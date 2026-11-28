"""Glue between eClass data, the database and the "Σήμερα" screen.

Everything on "Σήμερα" is an offer ("Θες να...;"). Nothing shows that something was missed:
an unanswered class is simply asked about again, calmly, another day.
"""

import re
from datetime import date, datetime

from sqlmodel import Session, select

from app.content.mock import normalize_title
from app.ekpa.provider import EkpaProvider
from app.ekpa.schedule import (
    ClassTime, Slot, Unit, ended_classes, next_class, parse_time, predict_unit, teaching_position, week_of,
)
from app.models import (
    Attempt, ClassConfirmation, Course, Document, Section, SyllabusUnit, TimetableSlot, Visit,
)

WEEKDAYS = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
WEEKDAY_ON = ["Τη Δευτέρα", "Την Τρίτη", "Την Τετάρτη", "Την Πέμπτη", "Την Παρασκευή", "Το Σάββατο", "Την Κυριακή"]
EASY_WORDS_PER_MINUTE = 100


# --- sync -----------------------------------------------------------------------

def sync_structure(session: Session, provider: EkpaProvider) -> dict[str, Course]:
    """Courses, timetable and syllabus. Safe to run again: nothing is duplicated."""
    courses = {}
    for c in provider.courses():
        course = session.exec(select(Course).where(Course.ekpa_id == c.id)).first()
        if course is None:
            course = Course(name=c.name, icon=c.icon, ekpa_id=c.id)
            session.add(course)
            session.flush()
        courses[c.id] = course

    for course in courses.values():
        for slot in session.exec(select(TimetableSlot).where(TimetableSlot.course_id == course.id)):
            session.delete(slot)
    for s in provider.timetable():
        if s.course_id in courses:
            session.add(TimetableSlot(course_id=courses[s.course_id].id, weekday=s.weekday, start=s.start, end=s.end, room=s.room))

    for ekpa_id, course in courses.items():
        existing = {u.position: u for u in session.exec(select(SyllabusUnit).where(SyllabusUnit.course_id == course.id))}
        for position, u in enumerate(provider.syllabus(ekpa_id)):
            row = existing.get(position) or SyllabusUnit(course_id=course.id, position=position, title=u.title, week=u.week)
            row.number, row.title, row.week = u.number, u.title, u.week  # unit ids stay, confirmations keep pointing to them
            session.add(row)
    session.flush()
    return courses


def sync_documents(session: Session, provider: EkpaProvider) -> list[Document]:
    """New PDFs posted by the teacher go through the same PDF analysis as uploads."""
    from app.pdf import PdfError
    from app.routers.courses import import_pdf

    imported = []
    for course in session.exec(select(Course).where(Course.ekpa_id != None)).all():  # noqa: E711
        for d in provider.documents(course.ekpa_id):
            if session.exec(select(Document).where(Document.ekpa_id == d.id)).first() is not None:
                continue
            try:
                doc = import_pdf(session, course, d.content, d.filename, title=d.title, source="eclass",
                                 ekpa_id=d.id, added_at=datetime.combine(d.added_on, datetime.min.time()))
            except PdfError:
                continue  # e.g. a scanned PDF: it simply does not show up
            imported.append(doc)
    session.flush()
    return imported


def sync(session: Session, provider: EkpaProvider) -> list[Document]:
    sync_structure(session, provider)
    docs = sync_documents(session, provider)
    session.commit()
    return docs


# --- reading the stored plan -------------------------------------------------------

def load_slots(session: Session) -> list[Slot]:
    return [
        Slot(s.course_id, s.weekday, parse_time(s.start), parse_time(s.end), s.room)
        for s in session.exec(select(TimetableSlot))
    ]


def load_units(session: Session, course_id: int) -> list[Unit]:
    return [
        Unit(u.id, u.position, unit_label(u), u.week)
        for u in session.exec(select(SyllabusUnit).where(SyllabusUnit.course_id == course_id).order_by(SyllabusUnit.position))
    ]


def unit_label(u: SyllabusUnit) -> str:
    return f"{u.number} {u.title}" if u.number else u.title


def confirmed_positions(session: Session, course_id: int) -> list[int]:
    rows = session.exec(
        select(SyllabusUnit.position).join(ClassConfirmation, ClassConfirmation.unit_id == SyllabusUnit.id)
        .where(ClassConfirmation.course_id == course_id, ClassConfirmation.status == "done")
    ).all()
    return list(rows)


def section_for_unit(session: Session, course_id: int, unit_id: int | None) -> Section | None:
    """The section of the uploaded material that matches a syllabus unit (same number and title)."""
    if unit_id is None:
        return None
    unit = session.get(SyllabusUnit, unit_id)
    title = normalize_title(unit.title)
    rows = session.exec(
        select(Section).join(Document, Document.id == Section.document_id)
        .where(Document.course_id == course_id, Document.simulated == False)  # noqa: E712
        .order_by(Document.uploaded_at.desc())
    ).all()
    for s in rows:
        if normalize_title(s.title) == title and (unit.number is None or s.number == unit.number):
            return s
    return None


def studied(session: Session, section_id: int) -> bool:
    return (
        session.exec(select(Visit.id).where(Visit.section_id == section_id)).first() is not None
        or session.exec(select(Attempt.id).where(Attempt.section_id == section_id, Attempt.correct != None)).first() is not None  # noqa: E711
    )


def reading_minutes(session: Session, section: Section) -> int:
    from app.routers.study import easy_read

    easy = easy_read(session, section)
    words = sum(len(re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", b.text).split()) for b in easy.blocks)
    return max(1, round(words / EASY_WORDS_PER_MINUTE))


# --- "Σήμερα" ---------------------------------------------------------------------------

def _class_out(session: Session, c: ClassTime, phase: str, now: datetime) -> dict:
    course = session.get(Course, c.course_id)
    return {
        "course_id": course.id, "course_name": course.name, "day": c.day, "weekday": WEEKDAYS[c.day.weekday()],
        "is_today": c.day == now.date(), "start": c.start.strftime("%H:%M"), "end": c.end.strftime("%H:%M"),
        "room": c.room, "phase": phase,
    }


def _pending_class(session: Session, slots: list[Slot], now: datetime) -> ClassTime | None:
    """The most recent class that ended and that the student has not told us about yet.
    "Δεν ξέρω" is respected for the rest of that day, then the question comes back calmly."""
    for c in ended_classes(slots, now):
        if not session.exec(select(SyllabusUnit.id).where(SyllabusUnit.course_id == c.course_id)).first():
            continue
        answers = session.exec(
            select(ClassConfirmation).where(ClassConfirmation.course_id == c.course_id, ClassConfirmation.class_date == c.day)
        ).all()
        if any(a.status == "done" for a in answers):
            continue
        if any(a.status == "unknown" and a.asked_on == now.date() for a in answers):
            continue
        return c
    return None


def today_view(session: Session, now: datetime, semester_start: date) -> dict:
    slots = load_slots(session)
    view: dict = {"now": now, "next_class": None, "before": None, "after": None, "new_material": []}

    upcoming = next_class(slots, now)
    if upcoming:
        c, phase = upcoming
        view["next_class"] = _class_out(session, c, phase, now)
        if phase == "before":
            unit = predict_unit(load_units(session, c.course_id), confirmed_positions(session, c.course_id), c.day, semester_start)
            if unit:
                section = section_for_unit(session, c.course_id, unit.id)
                view["before"] = {
                    "course_id": c.course_id, "course_name": session.get(Course, c.course_id).name,
                    "unit_id": unit.id, "unit_title": unit.title,
                    "section_id": section.id if section else None,
                    "minutes": reading_minutes(session, section) if section else None,
                }

    pending = _pending_class(session, slots, now)
    if pending:
        units = load_units(session, pending.course_id)
        unit = predict_unit(units, confirmed_positions(session, pending.course_id), pending.day, semester_start)
        view["after"] = {
            "course_id": pending.course_id, "course_name": session.get(Course, pending.course_id).name,
            "class_date": pending.day,
            "when": "Σήμερα" if pending.day == now.date() else WEEKDAY_ON[pending.day.weekday()],
            "predicted": {"unit_id": unit.id, "title": unit.title} if unit else None,
            "units": [{"unit_id": u.id, "title": u.title} for u in units],
        }

    docs = session.exec(
        select(Document, Course).join(Course, Course.id == Document.course_id)
        .where(Document.source == "eclass", Document.seen_at == None)  # noqa: E711
        .order_by(Document.uploaded_at.desc())
    ).all()
    view["new_material"] = [
        {"document_id": d.id, "course_name": c.name, "title": d.title, "added_on": d.uploaded_at.date()} for d, c in docs
    ]
    return view


def confirm_class(session: Session, course_id: int, class_date: date, unit_id: int | None, status: str, today: date) -> ClassConfirmation:
    """Save (or correct) what was taught in a class. One answer per course and day."""
    row = session.exec(
        select(ClassConfirmation).where(ClassConfirmation.course_id == course_id, ClassConfirmation.class_date == class_date)
    ).first() or ClassConfirmation(course_id=course_id, class_date=class_date)
    row.status = status
    row.unit_id = unit_id if status == "done" else None
    row.asked_on = today
    row.created_at = datetime.now()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def course_plan(session: Session, course: Course, today: date, semester_start: date) -> dict:
    """Where teaching is, what the student has studied, and a suggested next step."""
    units = load_units(session, course.id)
    confirmed = confirmed_positions(session, course.id)
    teaching = teaching_position(units, confirmed, today, semester_start)
    rows = []
    for u in units:
        section = section_for_unit(session, course.id, u.id)
        rows.append({
            "unit_id": u.id, "title": u.title, "week": u.week,
            "taught": teaching is not None and u.position <= teaching.position,
            "section_id": section.id if section else None,
            "studied": bool(section and studied(session, section.id)),
        })
    with_material = [r for r in rows if r["section_id"]]
    nxt = next((r for r in with_material if r["taught"] and not r["studied"]), None)
    if nxt is None and teaching is not None:
        upcoming = predict_unit(units, confirmed, today, semester_start)
        nxt = next((r for r in with_material if upcoming and r["unit_id"] == upcoming.id and not r["studied"]), None)
    return {
        "teaching": {"unit_id": teaching.id, "title": teaching.title, "week": teaching.week} if teaching else None,
        "teaching_from": "confirmed" if confirmed else "plan",
        "week": week_of(today, semester_start),
        "units": rows,
        "studied": sum(r["studied"] for r in with_material),
        "with_material": len(with_material),
        "next": {"section_id": nxt["section_id"], "text": f"Θες να δεις την ενότητα {nxt['title']};"} if nxt else None,
    }
