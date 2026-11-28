"""Glue between the learning rules and the database. Support levels live per section."""

import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.config import load_config
from app.learning import bkt
from app.learning.fading import (
    LEVEL_NAMES, MAX_LEVEL, MIN_LEVEL, PROPOSAL_MESSAGES, SEARCH_FROM_LEVEL, Outcome, easy_text_proposal, propose,
)
from app.models import (
    Attempt, ConceptMastery, Course, Document, LevelChange, Milestone, Section, SectionSupport, Visit,
)
from app.schemas import (
    ChapterLevels, ConceptOut, CourseProgress, DayPoint, LevelStep, MilestoneOut, ProposalOut, SectionLevel, SupportOut, WeekPoint,
)

MILESTONES = {
    "first_original": "Πρώτη ενότητα που διάβασες από το πρωτότυπο κείμενο.",
    "first_no_help": "Πρώτη σωστή απάντηση χωρίς καμία βοήθεια.",
    "first_found_sentence": "Πρώτη φορά που βρήκες την πρόταση στο κείμενο χωρίς εξήγηση.",
    "first_level3": "Πρώτη ενότητα που μελετάς «Από το πρωτότυπο».",
    "first_level4": "Πρώτη ενότητα που μελετάς «Αυτόνομα».",
    "first_exam": "Πρώτη εξάσκηση σαν στις εξετάσεις.",
}


def section_label(s: Section) -> str:
    return f"{s.number} {s.title}" if s.number else s.title


# --- support level per section ------------------------------------------------

def support(session: Session, section_id: int) -> SectionSupport:
    """Every section starts at level 1: no placement, no test before first use."""
    sup = session.get(SectionSupport, section_id)
    if sup is None:
        sup = SectionSupport(section_id=section_id)
        session.add(sup)
        session.flush()
    return sup


def proposal_out(sup: SectionSupport) -> ProposalOut | None:
    if sup.proposal_to is None or sup.proposal_to == sup.level:
        return None
    return ProposalOut(
        reason=sup.proposal_reason or "",
        from_level=sup.level,
        to_level=sup.proposal_to,
        message=PROPOSAL_MESSAGES.get(sup.proposal_reason or "", "Θες να αλλάξεις τον τρόπο μελέτης;"),
    )


def support_out(sup: SectionSupport, milestones: list[MilestoneOut] | None = None) -> SupportOut:
    return SupportOut(
        section_id=sup.section_id, level=sup.level, level_name=LEVEL_NAMES[sup.level],
        proposal=proposal_out(sup), new_milestones=milestones or [],
    )


def _propose(sup: SectionSupport, to_level: int, reason: str) -> None:
    sup.proposal_to = max(MIN_LEVEL, min(MAX_LEVEL, to_level))
    sup.proposal_reason = reason


# --- knowledge tracing (BKT) per concept ----------------------------------------

def mastery(session: Session, course_id: int, concept: str, create: bool = True) -> ConceptMastery | None:
    row = session.exec(
        select(ConceptMastery).where(ConceptMastery.course_id == course_id, ConceptMastery.concept == concept)
    ).first()
    if row is None and create:
        row = ConceptMastery(course_id=course_id, concept=concept, p_known=load_config().bkt.p_init)
        session.add(row)
        session.flush()
    return row


def record_evidence(session: Session, attempt: Attempt) -> None:
    """Update the concept's P(known) after a finished attempt (standard BKT)."""
    if attempt.concept is None or attempt.mode == "keypoints" or attempt.correct is None:
        return
    cfg = load_config().bkt
    ev = bkt.evidence(bool(attempt.correct), attempt.wrong_tries, help_used(attempt), attempt.self_checked,
                      attempt.shown_options, cfg)
    if ev is None:  # self-check: the student judged it, not evidence of knowledge
        return
    row = mastery(session, attempt.course_id, attempt.concept)
    row.p_known = bkt.update(row.p_known, ev.correct, ev.guess, cfg)
    row.observations += 1
    row.updated_at = datetime.now()
    session.add(row)


def section_concepts(section: Section) -> list[str]:
    return json.loads(section.concepts_json or "[]")


def _bkt_direction(session: Session, sup: SectionSupport, section: Section, course_id: int,
                   concept: str | None) -> str | None:
    """All concepts of the section above the threshold -> up. The concept being worked on
    below the low threshold (after enough answers) -> down."""
    cfg = load_config().bkt
    concepts = section_concepts(section)
    if not concepts:
        return None
    rows = {c: mastery(session, course_id, c, create=False) for c in concepts}
    if sup.level < MAX_LEVEL and all(r is not None and r.p_known > cfg.up_threshold for r in rows.values()):
        return "up"
    current = rows.get(concept) if concept else None
    if concept and current is None:
        current = mastery(session, course_id, concept, create=False)
    low = current is not None and current.observations >= cfg.min_observations and current.p_known < cfg.down_threshold
    if sup.level > MIN_LEVEL and low:
        return "down"
    return None


def update_proposal(session: Session, section_id: int, concept: str | None = None) -> SectionSupport:
    """After a finished answer: propose (never apply) a change for THIS section.
    engine = "bkt": knowledge per concept. engine = "rules": the simple rules of [fading]."""
    config = load_config()
    sup = support(session, section_id)
    attempts = session.exec(
        select(Attempt).where(
            Attempt.section_id == section_id, Attempt.correct != None, Attempt.mode == "question",  # noqa: E711
            Attempt.finished_at >= sup.window_start,
        ).order_by(Attempt.finished_at)
    ).all()
    if config.engine == "bkt":
        section = session.get(Section, section_id)
        course_id = session.get(Document, section.document_id).course_id
        # After a decision ("yes" or "not now"), wait for a few new answers before proposing again.
        enough = len(attempts) >= config.bkt.min_observations
        direction = _bkt_direction(session, sup, section, course_id, concept) if enough else None
        reasons = {"up": "known_up", "down": "concept_down"}
    else:
        outcomes = [
            Outcome(a.hints_used, bool(a.correct), a.wrong_tries, search=a.level >= SEARCH_FROM_LEVEL, fell_back=a.fell_back)
            for a in attempts
        ]
        direction = propose(sup.level, outcomes, config.fading)
        reasons = {"up": "fading_up", "down": "fading_down"}
    if direction:
        _propose(sup, sup.level + (1 if direction == "up" else -1), reasons[direction])
    elif sup.proposal_reason in ("fading_up", "fading_down", "known_up", "concept_down"):
        sup.proposal_to = sup.proposal_reason = None
    session.add(sup)
    return sup


def check_easy_use(session: Session, section_id: int) -> SectionSupport:
    """Levels 3-4: the Easy-to-Read text is used often -> offer one level back."""
    fading = load_config().fading
    sup = support(session, section_id)
    visits = session.exec(
        select(Visit).where(Visit.section_id == section_id, Visit.level == sup.level, Visit.created_at >= sup.window_start)
        .order_by(Visit.created_at)
    ).all()
    if sup.proposal_to is None and easy_text_proposal(sup.level, [v.used_easy for v in visits], fading):
        _propose(sup, sup.level - 1, "easy_use")
        session.add(sup)
    return sup


def propose_known_concepts(session: Session, section: Section, course_id: int) -> None:
    """New section whose concepts the student already knows (from earlier chapters):
    OFFER less support, never apply it. Offered level = the lowest of the highest levels
    at which each concept was practised (at least one step up)."""
    cfg = load_config().bkt
    concepts = section_concepts(section)
    if not concepts:
        return
    rows = [mastery(session, course_id, c, create=False) for c in concepts]
    if not all(r is not None and r.p_known > cfg.up_threshold for r in rows):
        return
    reached = []
    for c in concepts:
        levels = session.exec(select(Attempt.level).where(Attempt.course_id == course_id, Attempt.concept == c)).all()
        reached.append(max(levels, default=1))
    sup = support(session, section.id)
    _propose(sup, max(2, min(reached)), "known_start")
    session.add(sup)


def concept_summary(session: Session, course_id: int, concepts: list[str]) -> tuple[int, int]:
    """(known, total) for "Ξέρεις ήδη 3 από τις 5 έννοιες"."""
    cfg = load_config().bkt
    unique = list(dict.fromkeys(concepts))
    known = 0
    for c in unique:
        row = mastery(session, course_id, c, create=False)
        known += row is not None and row.p_known >= cfg.label_known
    return known, len(unique)


def concept_out(row: ConceptMastery) -> ConceptOut:
    key = bkt.label_key(row.p_known, load_config().bkt)
    return ConceptOut(concept=row.concept, label_key=key, label=bkt.LABELS[key])


def set_level(session: Session, section_id: int, level: int, reason: str) -> list[MilestoneOut]:
    sup = support(session, section_id)
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    if reason == "proposal" and sup.proposal_reason:
        reason = sup.proposal_reason
    if level != sup.level:
        session.add(LevelChange(section_id=section_id, from_level=sup.level, to_level=level, reason=reason))
    sup.level = level
    sup.proposal_to = sup.proposal_reason = None
    sup.window_start = datetime.now()
    session.add(sup)
    new = []
    if level >= 3:
        new += award(session, "first_level3", section_id)
    if level == 4:
        new += award(session, "first_level4", section_id)
    return new


def decline_proposal(session: Session, section_id: int) -> SectionSupport:
    sup = support(session, section_id)
    if sup.proposal_to is not None:
        session.add(LevelChange(
            section_id=section_id, from_level=sup.level, to_level=sup.proposal_to,
            reason=sup.proposal_reason or "", accepted=False,
        ))
    sup.proposal_to = sup.proposal_reason = None
    sup.window_start = datetime.now()
    session.add(sup)
    return sup


# --- milestones ---------------------------------------------------------------

def milestone_out(m: Milestone) -> MilestoneOut:
    return MilestoneOut(key=m.key, text=MILESTONES[m.key], created_at=m.created_at)


def award(session: Session, key: str, section_id: int | None = None) -> list[MilestoneOut]:
    """A milestone is given once. Returns it only the first time."""
    if session.get(Milestone, key) is not None:
        return []
    m = Milestone(key=key, section_id=section_id)
    session.add(m)
    session.flush()
    return [milestone_out(m)]


# --- progress -------------------------------------------------------------------

def finished_attempts(session: Session, course_id: int | None = None) -> list[Attempt]:
    query = select(Attempt).where(Attempt.correct != None, Attempt.mode != "exam")  # noqa: E711
    if course_id is not None:
        query = query.where(Attempt.course_id == course_id)
    return list(session.exec(query.order_by(Attempt.finished_at)))


def help_used(a: Attempt) -> int:
    return a.hints_used + a.search_steps


def _pct(x: float) -> int:
    return round(x * 100)


def progress_message(previous: float | None, current: float | None, current_count: int, impersonal: bool = False) -> str:
    needed = "χρειάστηκε" if impersonal else "χρειάστηκες"
    if current is None and previous is None:
        return "Όταν απαντηθούν μερικές ερωτήσεις, εδώ θα φαίνεται πώς αλλάζει η βοήθεια." if impersonal else \
            "Όταν απαντήσεις μερικές ερωτήσεις, εδώ θα βλέπεις πώς αλλάζει η βοήθεια που χρειάζεσαι."
    if current is None:
        return "Αυτή την εβδομάδα δεν υπάρχουν ακόμα απαντήσεις." if impersonal else \
            "Αυτή την εβδομάδα δεν έχεις απαντήσει ακόμα ερωτήσεις. Μπορείς να συνεχίσεις όποτε θέλεις."
    if previous is None or previous == 0:
        return f"Αυτή την εβδομάδα απαντήθηκαν {current_count} ερωτήσεις." if impersonal else \
            f"Αυτή την εβδομάδα απάντησες {current_count} ερωτήσεις. Την επόμενη εβδομάδα θα δεις τη σύγκριση."
    change = (previous - current) / previous
    if change >= 0.05:
        return f"Αυτή την εβδομάδα {needed} {_pct(change)}% λιγότερη βοήθεια από την προηγούμενη."
    if change > -0.05:
        return f"Αυτή την εβδομάδα {needed} περίπου την ίδια βοήθεια με την προηγούμενη."
    return "Αυτή την εβδομάδα η ύλη ήθελε λίγο περισσότερη βοήθεια. Αυτό είναι φυσικό με καινούργια ύλη."


def _week(attempts: list[Attempt], start: date, end: date, label: str) -> WeekPoint:
    inside = [a for a in attempts if start <= a.finished_at.date() <= end]
    hpq = round(sum(help_used(a) for a in inside) / len(inside), 2) if inside else None
    return WeekPoint(label=label, start=start, end=end, questions=len(inside), hints_per_question=hpq)


def weeks_for(attempts: list[Attempt], today: date) -> list[WeekPoint]:
    """Two rolling weeks: the last 7 days and the 7 days before."""
    this_start = today - timedelta(days=6)
    prev_start = this_start - timedelta(days=7)
    return [
        _week(attempts, prev_start, this_start - timedelta(days=1), "Προηγούμενη εβδομάδα"),
        _week(attempts, this_start, today, "Αυτή την εβδομάδα"),
    ]


def days_for(attempts: list[Attempt], today: date, span: int = 14) -> list[DayPoint]:
    by_day = defaultdict(list)
    for a in attempts:
        by_day[a.finished_at.date()].append(a)
    first = today - timedelta(days=span - 1)
    return [
        DayPoint(day=d, questions=len(items), hints_per_question=round(sum(help_used(a) for a in items) / len(items), 2))
        for d, items in sorted(by_day.items())
        if first <= d <= today
    ]


def chapter_levels(session: Session, course_id: int) -> list[ChapterLevels]:
    docs = session.exec(select(Document).where(Document.course_id == course_id).order_by(Document.uploaded_at)).all()
    chapters = []
    for doc in docs:
        sections = session.exec(select(Section).where(Section.document_id == doc.id).order_by(Section.position)).all()
        levels = []
        for s in sections:
            sup = session.get(SectionSupport, s.id)
            level = sup.level if sup else 1
            levels.append(SectionLevel(id=s.id, label=section_label(s), level=level, level_name=LEVEL_NAMES[level]))
        chapters.append(ChapterLevels(title=doc.title, sections=levels))
    return chapters


def course_progress(session: Session, course: Course, today: date, impersonal: bool = False) -> CourseProgress:
    attempts = finished_attempts(session, course.id)
    weeks = weeks_for(attempts, today)
    changes = session.exec(
        select(LevelChange, Section).join(Section, Section.id == LevelChange.section_id)
        .join(Document, Document.id == Section.document_id)
        .where(Document.course_id == course.id, LevelChange.accepted == True)  # noqa: E712
        .order_by(LevelChange.created_at)
    ).all()
    return CourseProgress(
        id=course.id,
        name=course.name,
        icon=course.icon,
        chapters=chapter_levels(session, course.id),
        days=days_for(attempts, today),
        weeks=weeks,
        level_history=[
            LevelStep(at=c.created_at, section=section_label(s), from_level=c.from_level, to_level=c.to_level)
            for c, s in changes
        ],
        message=progress_message(weeks[0].hints_per_question, weeks[1].hints_per_question, weeks[1].questions, impersonal),
        concepts=[concept_out(r) for r in session.exec(
            select(ConceptMastery).where(ConceptMastery.course_id == course.id, ConceptMastery.observations > 0)
            .order_by(ConceptMastery.concept)
        )],
    )


def overall_message(session: Session, today: date, impersonal: bool = False) -> str:
    weeks = weeks_for(finished_attempts(session), today)
    return progress_message(weeks[0].hints_per_question, weeks[1].hints_per_question, weeks[1].questions, impersonal)


def has_simulated_data(session: Session) -> bool:
    return session.exec(select(Attempt).where(Attempt.simulated == True)).first() is not None  # noqa: E712
