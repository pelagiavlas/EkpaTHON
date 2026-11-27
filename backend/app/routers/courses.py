import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, delete, select

from app.db import get_session
from app.models import Chunk, Course, WorkItem
from app.routers.profile import get_profile
from app.scheduler import estimate_minutes
from app.schemas import CourseIn, CourseOut, TaskIn, TaskOut, TaskUpdate

router = APIRouter(tags=["courses & tasks"])


@router.get("/courses", response_model=list[CourseOut])
def list_courses(session: Session = Depends(get_session)):
    return session.exec(select(Course).order_by(Course.name)).all()


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(body: CourseIn, session: Session = Depends(get_session)):
    course = Course(name=body.name.strip())
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, session: Session = Depends(get_session)):
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Δεν βρέθηκε το μάθημα")
    for item in session.exec(select(WorkItem).where(WorkItem.course_id == course_id)):
        _delete_item(session, item)
    session.delete(course)
    session.commit()


def task_out(item: WorkItem, course_name: str) -> TaskOut:
    return TaskOut(
        **item.model_dump(exclude={"steps", "pages", "difficulty", "created_at"}),
        course=course_name,
        steps=json.loads(item.steps),
    )


def _get_item(session: Session, task_id: int) -> WorkItem:
    item = session.get(WorkItem, task_id)
    if item is None:
        raise HTTPException(404, "Δεν βρέθηκε η εργασία")
    return item


def _delete_item(session: Session, item: WorkItem) -> None:
    session.exec(delete(Chunk).where(Chunk.work_item_id == item.id))
    session.delete(item)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(include_done: bool = False, session: Session = Depends(get_session)):
    query = select(WorkItem, Course).join(Course).order_by(WorkItem.deadline)
    if not include_done:
        query = query.where(WorkItem.done == False)  # noqa: E712
    return [task_out(item, course.name) for item, course in session.exec(query)]


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, session: Session = Depends(get_session)):
    course = session.get(Course, body.course_id)
    if course is None:
        raise HTTPException(404, "Δεν βρέθηκε το μάθημα")
    profile = get_profile(session)
    try:
        base = estimate_minutes(
            body.kind, body.pages, body.difficulty, profile.minutes_per_page, body.estimated_minutes
        )
    except ValueError:
        raise HTTPException(422, "Γράψε πόσα λεπτά νομίζεις ότι θα πάρει ή πόσες σελίδες είναι")
    item = WorkItem(
        course_id=course.id,
        title=body.title.strip(),
        kind=body.kind,
        base_minutes=base,
        deadline=body.deadline,
        pages=body.pages,
        difficulty=body.difficulty,
        steps=json.dumps(body.steps, ensure_ascii=False),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return task_out(item, course.name)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate, session: Session = Depends(get_session)):
    item = _get_item(session, task_id)
    changes = body.model_dump(exclude_none=True)
    if "estimated_minutes" in changes:
        item.base_minutes = changes.pop("estimated_minutes")
    if "steps" in changes:
        item.steps = json.dumps(changes.pop("steps"), ensure_ascii=False)
    for key, value in changes.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return task_out(item, session.get(Course, item.course_id).name)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, session: Session = Depends(get_session)):
    _delete_item(session, _get_item(session, task_id))
    session.commit()
