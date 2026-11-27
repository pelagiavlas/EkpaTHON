"""Glue between the prediction functions and the database."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.models import Chunk, KindStat, Profile, WorkItem
from app.prediction.fading import next_support
from app.prediction.multiplier import update_multiplier
from app.prediction.risk import Capacity
from app.scheduler import Availability

WORKED = ("done", "in_progress")
PREDICTED_KINDS = ("study", "assignment")


def get_stat(session: Session, kind: str) -> KindStat:
    stat = session.get(KindStat, kind)
    if stat is None:
        stat = KindStat(kind=kind)
        session.add(stat)
    return stat


def current_multipliers(session: Session) -> dict[str, float]:
    return {s.kind: s.multiplier for s in session.exec(select(KindStat))}


def worked_minutes(session: Session, item_id: int, field: str = "minutes") -> float:
    """Planned (`minutes`) or real (`actual_minutes`) time already spent on an item."""
    chunks = session.exec(
        select(Chunk).where(Chunk.work_item_id == item_id, Chunk.status.in_(WORKED), Chunk.kind != "revision")
    )
    return sum(getattr(c, field) or 0 for c in chunks)


def on_item_completed(session: Session, item: WorkItem) -> None:
    """Teach the model: actual time for the whole task vs its estimate."""
    if item.kind not in PREDICTED_KINDS:
        return
    actual = worked_minutes(session, item.id, "actual_minutes")
    if actual <= 0:
        return
    stat = get_stat(session, item.kind)
    stat.multiplier = update_multiplier(stat.multiplier, actual, item.base_minutes)
    stat.samples += 1
    session.add(stat)


def on_chunk_finished(session: Session, chunk: Chunk) -> None:
    stat = get_stat(session, chunk.kind)
    stat.support_level, stat.success_streak = next_support(
        stat.support_level, stat.success_streak, chunk.help_requests > 0
    )
    session.add(stat)


def mark_missed(session: Session, before: date) -> None:
    """Planned chunks in the past that were never started count as missed (for pace)."""
    for chunk in session.exec(select(Chunk).where(Chunk.status == "upcoming", Chunk.day < before)):
        chunk.status = "missed"
        session.add(chunk)


def weekly_pace(session: Session, today: date) -> float:
    """Share of last week's planned chunks that were actually done. 1.0 without history."""
    week = session.exec(select(Chunk).where(Chunk.day >= today - timedelta(days=7), Chunk.day < today)).all()
    if not week:
        return 1.0
    return sum(1 for c in week if c.status == "done") / len(week)


def capacity_until(availability: Availability, profile: Profile, now: datetime, deadline: date) -> Capacity:
    """Usable study minutes from now until the day before the deadline."""
    per_day_cap = profile.max_chunks_per_day * profile.chunk_minutes
    efficiency = profile.chunk_minutes / (profile.chunk_minutes + profile.short_break)
    minutes, days = 0.0, 0
    day = now.date()
    while day < deadline:
        not_before = now.hour * 60 + now.minute if day == now.date() else 0
        free = sum(e - s for s, e in availability.windows_on(day, not_before))
        if free > 0:
            minutes += min(per_day_cap, free * efficiency)
            days += 1
        day += timedelta(days=1)
    return Capacity(minutes, days)


def weekly_help(session: Session) -> list[dict]:
    """Help requests per finished chunk, per week (Monday start)."""
    weeks = defaultdict(lambda: [0, 0])
    for c in session.exec(select(Chunk).where(Chunk.status == "done")):
        monday = c.day - timedelta(days=c.day.weekday())
        weeks[monday][0] += 1
        weeks[monday][1] += c.help_requests
    return [
        {"week_start": w, "chunks_done": n, "help_requests": h, "help_per_chunk": round(h / n, 2)}
        for w, (n, h) in sorted(weeks.items())
    ]
