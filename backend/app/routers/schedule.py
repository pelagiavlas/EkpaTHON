from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select

from app import scheduler
from app.db import get_session
from app.models import AvailabilityWindow, BlockedDate, Chunk, Course, WorkItem
from app.routers.profile import get_profile
from app.scheduler import fmt_hhmm, parse_hhmm
from app.schemas import ChunkOut, FinishIn, GenerateIn, ScheduleOut, UnscheduledOut

router = APIRouter(tags=["schedule"])


def load_availability(session: Session) -> scheduler.Availability:
    windows = [
        scheduler.Window(w.weekday, parse_hhmm(w.start), parse_hhmm(w.end))
        for w in session.exec(select(AvailabilityWindow))
    ]
    blocked = {b.day for b in session.exec(select(BlockedDate))}
    return scheduler.Availability(windows, blocked)


def chunks_out(session: Session, chunks: list[Chunk]) -> list[ChunkOut]:
    items = {i.id: i for i in session.exec(select(WorkItem))}
    courses = {c.id: c.name for c in session.exec(select(Course))}
    result = []
    for ch in chunks:
        item = items[ch.work_item_id]
        result.append(
            ChunkOut(
                id=ch.id,
                work_item_id=ch.work_item_id,
                title=item.title,
                course=courses[item.course_id],
                kind=ch.kind,
                day=ch.day,
                start=fmt_hhmm(ch.start_min),
                end=fmt_hhmm(ch.start_min + ch.minutes),
                minutes=ch.minutes,
                seq=ch.seq,
                status=ch.status,
                help_requests=ch.help_requests,
                actual_minutes=ch.actual_minutes,
            )
        )
    return result


def current_multipliers(session: Session) -> dict[str, float]:
    """Personal time multipliers per task kind (filled in by the prediction model)."""
    return {}


@router.post("/schedule/generate", response_model=ScheduleOut)
def generate_schedule(body: GenerateIn | None = None, session: Session = Depends(get_session)):
    body = body or GenerateIn()
    profile = get_profile(session)
    now = datetime.now()
    start = body.start_date or now.date()
    start_minute = now.hour * 60 + now.minute if start == now.date() else 0

    # Future plans are rebuilt; started and finished chunks are history and stay.
    session.exec(delete(Chunk).where(Chunk.status == "upcoming"))
    done_minutes = defaultdict(float)
    for ch in session.exec(select(Chunk).where(Chunk.status != "upcoming", Chunk.kind != "revision")):
        done_minutes[ch.work_item_id] += ch.minutes

    courses = {c.id: c.name for c in session.exec(select(Course))}
    rows = session.exec(
        select(WorkItem).where(WorkItem.done == False, WorkItem.deadline > start)  # noqa: E712
    ).all()
    items = [
        scheduler.WorkItem(r.id, courses[r.course_id], r.kind, r.base_minutes, r.deadline, r.title)
        for r in rows
    ]
    settings = scheduler.Settings(
        chunk_minutes=profile.chunk_minutes,
        short_break=profile.short_break,
        long_break=profile.long_break,
        max_chunks_per_day=profile.max_chunks_per_day,
    )
    result = scheduler.generate(
        items,
        load_availability(session),
        start,
        settings,
        multipliers=current_multipliers(session),
        done_minutes=done_minutes,
        seed=body.seed,
        start_minute=start_minute,
    )

    seq = defaultdict(int)
    for item_id, count in session.exec(select(Chunk.work_item_id, Chunk.seq).where(Chunk.status != "upcoming")):
        seq[item_id] = max(seq[item_id], count)
    saved = []
    for p in result.placements:
        seq[p.chunk.item_id] += 1
        row = Chunk(
            work_item_id=p.chunk.item_id,
            kind=p.chunk.kind,
            day=p.day,
            start_min=p.start,
            minutes=p.chunk.minutes,
            seq=seq[p.chunk.item_id],
        )
        session.add(row)
        saved.append(row)
    session.commit()
    for row in saved:
        session.refresh(row)

    titles = {r.id: r.title for r in rows}
    missing = defaultdict(int)
    for ch in result.unscheduled:
        missing[ch.item_id] += ch.minutes
    return ScheduleOut(
        score=round(result.score, 2),
        chunks=chunks_out(session, saved),
        unscheduled=[UnscheduledOut(work_item_id=i, title=titles[i], minutes=m) for i, m in missing.items()],
    )


@router.get("/schedule", response_model=list[ChunkOut])
def list_schedule(start: date, end: date, session: Session = Depends(get_session)):
    chunks = session.exec(
        select(Chunk).where(Chunk.day >= start, Chunk.day <= end).order_by(Chunk.day, Chunk.start_min)
    ).all()
    return chunks_out(session, chunks)


@router.get("/schedule/today", response_model=list[ChunkOut])
def today(day: date | None = None, session: Session = Depends(get_session)):
    day = day or date.today()
    return list_schedule(day, day, session)


def _get_chunk(session: Session, chunk_id: int) -> Chunk:
    chunk = session.get(Chunk, chunk_id)
    if chunk is None:
        raise HTTPException(404, "Δεν βρέθηκε το κομμάτι")
    return chunk


def _save(session: Session, chunk: Chunk) -> ChunkOut:
    session.add(chunk)
    session.commit()
    session.refresh(chunk)
    return chunks_out(session, [chunk])[0]


@router.post("/chunks/{chunk_id}/start", response_model=ChunkOut)
def start_chunk(chunk_id: int, session: Session = Depends(get_session)):
    chunk = _get_chunk(session, chunk_id)
    if chunk.status == "done":
        raise HTTPException(409, "Αυτό το κομμάτι έχει ήδη τελειώσει")
    chunk.status = "in_progress"
    chunk.started_at = datetime.now()
    return _save(session, chunk)


@router.post("/chunks/{chunk_id}/finish", response_model=ChunkOut)
def finish_chunk(chunk_id: int, body: FinishIn | None = None, session: Session = Depends(get_session)):
    body = body or FinishIn()
    chunk = _get_chunk(session, chunk_id)
    chunk.finished_at = datetime.now()
    if body.actual_minutes is not None:
        chunk.actual_minutes = body.actual_minutes
    elif chunk.started_at is not None:
        elapsed = (chunk.finished_at - chunk.started_at).total_seconds() / 60
        chunk.actual_minutes = round(max(1.0, elapsed), 1)
    else:
        chunk.actual_minutes = float(chunk.minutes)  # no start pressed: assume as planned
    chunk.status = "done"
    if body.item_done:
        item = session.get(WorkItem, chunk.work_item_id)
        item.done = True
        session.add(item)
    return _save(session, chunk)


@router.post("/chunks/{chunk_id}/help", response_model=ChunkOut)
def ask_help(chunk_id: int, session: Session = Depends(get_session)):
    chunk = _get_chunk(session, chunk_id)
    chunk.help_requests += 1
    return _save(session, chunk)
