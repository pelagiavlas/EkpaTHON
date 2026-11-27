"""Glue between the learning rules and the database."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.config import load_config
from app.learning.fading import LEVEL_NAMES, MAX_LEVEL, MIN_LEVEL, Outcome, propose, proposal_message
from app.learning.predict import ChapterHistory, Suggestion, suggest_start_level
from app.models import Attempt, Course, Document, LevelChange
from app.schemas import CourseProgress, DayPoint, LevelStep, ProposalOut, WeekPoint


def finished_attempts(session: Session, course_id: int, since: datetime | None = None) -> list[Attempt]:
    query = select(Attempt).where(Attempt.course_id == course_id, Attempt.correct != None)  # noqa: E711
    if since is not None:
        query = query.where(Attempt.finished_at >= since)
    return list(session.exec(query.order_by(Attempt.finished_at)))


def proposal_out(course: Course) -> ProposalOut | None:
    if course.proposal not in ("up", "down"):
        return None
    to_level = course.level + (1 if course.proposal == "up" else -1)
    return ProposalOut(
        direction=course.proposal,
        from_level=course.level,
        to_level=to_level,
        message=proposal_message(course.proposal, course.name),
    )


def update_proposal(session: Session, course: Course) -> None:
    fading, _ = load_config()
    attempts = finished_attempts(session, course.id, since=course.window_start)
    outcomes = [Outcome(a.hints_used, bool(a.correct), a.wrong_tries) for a in attempts]
    course.proposal = propose(course.level, outcomes, fading)
    session.add(course)


def set_level(session: Session, course: Course, level: int, reason: str, now: datetime | None = None) -> None:
    now = now or datetime.now()
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    if level != course.level:
        session.add(LevelChange(course_id=course.id, from_level=course.level, to_level=level, reason=reason, created_at=now))
    course.level = level
    course.proposal = None
    course.window_start = now
    session.add(course)


def decline_proposal(session: Session, course: Course) -> None:
    if course.proposal:
        to_level = course.level + (1 if course.proposal == "up" else -1)
        session.add(LevelChange(course_id=course.id, from_level=course.level, to_level=to_level, reason="proposal", accepted=False))
    course.proposal = None
    course.window_start = datetime.now()
    session.add(course)


def chapter_history(session: Session, course_id: int, exclude_document_id: int | None = None) -> list[ChapterHistory]:
    docs = session.exec(
        select(Document).where(Document.course_id == course_id).order_by(Document.uploaded_at)
    ).all()
    history = []
    for doc in docs:
        if doc.id == exclude_document_id:
            continue
        attempts = session.exec(
            select(Attempt).where(Attempt.document_id == doc.id, Attempt.correct != None)  # noqa: E711
        ).all()
        if not attempts:
            continue
        n = len(attempts)
        history.append(ChapterHistory(
            questions=n,
            hints_per_question=sum(a.hints_used for a in attempts) / n,
            wrong_rate=sum(1 for a in attempts if not a.correct or a.wrong_tries) / n,
        ))
    return history


def suggestion_for(session: Session, course: Course, document_id: int) -> Suggestion:
    _, prediction = load_config()
    return suggest_start_level(chapter_history(session, course.id, document_id), course.level, prediction)


# --- progress ---------------------------------------------------------------

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
    hpq = round(sum(a.hints_used for a in inside) / len(inside), 2) if inside else None
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
        DayPoint(day=d, questions=len(items), hints_per_question=round(sum(a.hints_used for a in items) / len(items), 2))
        for d, items in sorted(by_day.items())
        if first <= d <= today
    ]


def course_progress(session: Session, course: Course, today: date, impersonal: bool = False) -> CourseProgress:
    attempts = finished_attempts(session, course.id)
    weeks = weeks_for(attempts, today)
    changes = session.exec(
        select(LevelChange).where(LevelChange.course_id == course.id, LevelChange.accepted == True)  # noqa: E712
        .order_by(LevelChange.created_at)
    ).all()
    return CourseProgress(
        id=course.id,
        name=course.name,
        icon=course.icon,
        level=course.level,
        level_name=LEVEL_NAMES[course.level],
        days=days_for(attempts, today),
        weeks=weeks,
        level_history=[LevelStep(at=c.created_at, from_level=c.from_level, to_level=c.to_level) for c in changes],
        message=progress_message(weeks[0].hints_per_question, weeks[1].hints_per_question, weeks[1].questions, impersonal),
    )


def overall_message(session: Session, today: date, impersonal: bool = False) -> str:
    attempts = list(session.exec(select(Attempt).where(Attempt.correct != None)))  # noqa: E711
    weeks = weeks_for(attempts, today)
    return progress_message(weeks[0].hints_per_question, weeks[1].hints_per_question, weeks[1].questions, impersonal)


def has_simulated_data(session: Session) -> bool:
    return session.exec(select(Attempt).where(Attempt.simulated == True)).first() is not None  # noqa: E712
