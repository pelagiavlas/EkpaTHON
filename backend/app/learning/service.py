"""Glue between the learning rules and the database. Support levels live per section."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.config import load_config
from app.content.mock import normalize_title
from app.learning.fading import (
    LEVEL_NAMES, MAX_LEVEL, MIN_LEVEL, PROPOSAL_MESSAGES, SEARCH_FROM_LEVEL, Outcome, easy_text_proposal, propose,
)
from app.models import Attempt, Course, Document, LevelChange, Milestone, Section, SectionSupport, Visit
from app.schemas import (
    ChapterLevels, CourseProgress, DayPoint, LevelStep, MilestoneOut, ProposalOut, SectionLevel, SupportOut, WeekPoint,
)

MILESTONES = {
    "first_original": "Πρώτη ενότητα που διάβασες από το πρωτότυπο κείμενο.",
    "first_no_help": "Πρώτη σωστή απάντηση χωρίς καμία βοήθεια.",
    "first_found_sentence": "Πρώτη φορά που βρήκες την πρόταση στο κείμενο χωρίς εξήγηση.",
    "first_level3": "Πρώτη ενότητα στο επίπεδο 3: ψάχνεις στο κείμενο.",
    "first_level4": "Πρώτη ενότητα στο επίπεδο 4: αυτονομία.",
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
        message=PROPOSAL_MESSAGES.get(sup.proposal_reason or "", "Θες να αλλάξεις το επίπεδο βοήθειας;"),
    )


def support_out(sup: SectionSupport, milestones: list[MilestoneOut] | None = None) -> SupportOut:
    return SupportOut(
        section_id=sup.section_id, level=sup.level, level_name=LEVEL_NAMES[sup.level],
        proposal=proposal_out(sup), new_milestones=milestones or [],
    )


def _propose(sup: SectionSupport, to_level: int, reason: str) -> None:
    sup.proposal_to = max(MIN_LEVEL, min(MAX_LEVEL, to_level))
    sup.proposal_reason = reason


def update_proposal(session: Session, section_id: int) -> SectionSupport:
    """After a finished answer: apply the fading rules to THIS section's answers."""
    fading, _ = load_config()
    sup = support(session, section_id)
    attempts = session.exec(
        select(Attempt).where(
            Attempt.section_id == section_id, Attempt.correct != None, Attempt.mode != "exam",  # noqa: E711
            Attempt.finished_at >= sup.window_start,
        ).order_by(Attempt.finished_at)
    ).all()
    outcomes = [
        Outcome(a.hints_used, bool(a.correct), a.wrong_tries, search=a.level >= SEARCH_FROM_LEVEL, fell_back=a.fell_back)
        for a in attempts
    ]
    direction = propose(sup.level, outcomes, fading)
    if direction:
        _propose(sup, sup.level + (1 if direction == "up" else -1), f"fading_{direction}")
    elif sup.proposal_reason in ("fading_up", "fading_down"):
        sup.proposal_to = sup.proposal_reason = None
    session.add(sup)
    return sup


def check_easy_use(session: Session, section_id: int) -> SectionSupport:
    """Levels 3-4: the Easy-to-Read text is used often -> offer one level back."""
    fading, _ = load_config()
    sup = support(session, section_id)
    visits = session.exec(
        select(Visit).where(Visit.section_id == section_id, Visit.level == sup.level, Visit.created_at >= sup.window_start)
        .order_by(Visit.created_at)
    ).all()
    if sup.proposal_to is None and easy_text_proposal(sup.level, [v.used_easy for v in visits], fading):
        _propose(sup, sup.level - 1, "easy_use")
        session.add(sup)
    return sup


def propose_same_topic(session: Session, section: Section, course_id: int) -> None:
    """A section on a topic the student already studied (same title, same course):
    OFFER the level reached there. Never applied without a yes."""
    title = normalize_title(section.title)
    best = 1
    others = session.exec(
        select(Section, SectionSupport).join(Document, Document.id == Section.document_id)
        .join(SectionSupport, SectionSupport.section_id == Section.id)
        .where(Document.course_id == course_id, Section.id != section.id)
    ).all()
    for other, sup in others:
        if normalize_title(other.title) == title:
            best = max(best, sup.level)
    if best > 1:
        sup = support(session, section.id)
        _propose(sup, best, "same_topic")
        session.add(sup)


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
            "Αυτή την εβδομάδα δεν έχεις απαντήσει ακόμα ερωτήσεις. Όποτε θέλεις, συνεχίζουμε."
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
    )


def overall_message(session: Session, today: date, impersonal: bool = False) -> str:
    weeks = weeks_for(finished_attempts(session), today)
    return progress_message(weeks[0].hints_per_question, weeks[1].hints_per_question, weeks[1].questions, impersonal)


def has_simulated_data(session: Session) -> bool:
    return session.exec(select(Attempt).where(Attempt.simulated == True)).first() is not None  # noqa: E712
