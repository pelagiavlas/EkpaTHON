"""eClass sync, the "Σήμερα" screen and the teaching plan of each course."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.ekpa import get_ekpa_provider, is_simulated
from app.ekpa import service as ekpa
from app.ekpa.clock import current_time, demo_enabled
from app.models import ClassConfirmation, Course, SyllabusUnit
from app.routers.courses import get_or_404
from app.routers.study import load_questions
from app.schemas import ConfirmIn, ConfirmOut, PlanOut, TeachingIn, TodayOut

router = APIRouter(tags=["eClass & today"])


def app_now(session: Session, demo: bool, moment: str | None) -> tuple[datetime, bool]:
    """The app clock: real time, or the demo clock (always a class at 11:00)."""
    on = demo_enabled(demo)
    return current_time(on, ekpa.load_slots(session), moment), on


def try_sync(session: Session, today: date) -> None:
    try:
        ekpa.sync(session, get_ekpa_provider(today))
    except NotImplementedError:
        pass  # eClass not connected yet: work with what is stored


def semester_start(today: date) -> date:
    try:
        return get_ekpa_provider(today).semester_start()
    except NotImplementedError:
        return today


@router.post("/ekpa/sync")
def sync_now(demo: bool = False, moment: str | None = None, session: Session = Depends(get_session)):
    now, _ = app_now(session, demo, moment)
    try:
        docs = ekpa.sync(session, get_ekpa_provider(now.date()))
    except NotImplementedError as err:
        raise HTTPException(503, str(err))
    return {"new_documents": len(docs)}


@router.get("/today", response_model=TodayOut)
def today(demo: bool = False, moment: str | None = None, session: Session = Depends(get_session)):
    try_sync(session, date.today())  # timetable first, so the demo clock can find the 11:00 class
    now, on = app_now(session, demo, moment)
    if on:
        try_sync(session, now.date())  # demo dates are relative to the demo "today"
    view = ekpa.today_view(session, now, semester_start(now.date()))
    session.commit()
    return TodayOut(**view, demo=on, simulated_eclass=is_simulated())


@router.post("/classes/confirm", response_model=ConfirmOut)
def confirm(body: ConfirmIn, demo: bool = False, moment: str | None = None, session: Session = Depends(get_session)):
    """"Σήμερα κάνατε την ενότητα Χ;" - Ναι / Όχι, κάναμε... / Δεν ξέρω. Can be corrected later."""
    get_or_404(session, Course, body.course_id, "Δεν βρέθηκε το μάθημα")
    if body.status == "done":
        unit = session.get(SyllabusUnit, body.unit_id) if body.unit_id else None
        if unit is None or unit.course_id != body.course_id:
            raise HTTPException(422, "Διάλεξε μία ενότητα από τη λίστα.")
    now, _ = app_now(session, demo, moment)
    row = ekpa.confirm_class(session, body.course_id, body.class_date, body.unit_id, body.status, now.date())
    section = ekpa.section_for_unit(session, body.course_id, row.unit_id)
    has_questions = bool(section and load_questions(session, section, 1))
    unit = session.get(SyllabusUnit, row.unit_id) if row.unit_id else None
    return ConfirmOut(status=row.status, unit_title=ekpa.unit_label(unit) if unit else None,
                      section_id=section.id if section else None, has_questions=has_questions)


@router.get("/courses/{course_id}/plan", response_model=PlanOut)
def plan(course_id: int, demo: bool = False, moment: str | None = None, session: Session = Depends(get_session)):
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    now, _ = app_now(session, demo, moment)
    return PlanOut(**ekpa.course_plan(session, course, now.date(), semester_start(now.date())), simulated_eclass=is_simulated())


@router.post("/courses/{course_id}/teaching", response_model=PlanOut)
def correct_teaching(course_id: int, body: TeachingIn, demo: bool = False, moment: str | None = None,
                     session: Session = Depends(get_session)):
    """The student corrects where teaching is: the latest answer changes, or a new one is added for today."""
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    unit = session.get(SyllabusUnit, body.unit_id)
    if unit is None or unit.course_id != course_id:
        raise HTTPException(422, "Διάλεξε μία ενότητα από τη λίστα.")
    now, _ = app_now(session, demo, moment)
    latest = session.exec(
        select(ClassConfirmation).where(ClassConfirmation.course_id == course_id, ClassConfirmation.status == "done")
        .order_by(ClassConfirmation.class_date.desc())
    ).first()
    later = session.exec(
        select(ClassConfirmation).join(SyllabusUnit, SyllabusUnit.id == ClassConfirmation.unit_id)
        .where(ClassConfirmation.course_id == course_id, SyllabusUnit.position > unit.position)
    ).all()
    for row in later:  # "teaching is at X" also means nothing after X has been taught yet
        session.delete(row)
    session.flush()
    ekpa.confirm_class(session, course_id, latest.class_date if latest and latest not in later else now.date(),
                       unit.id, "done", now.date())
    return PlanOut(**ekpa.course_plan(session, course, now.date(), semester_start(now.date())), simulated_eclass=is_simulated())
