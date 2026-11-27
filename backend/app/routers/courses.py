import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, delete, select

from app.db import STORAGE_DIR, get_session
from app.learning import service
from app.learning.fading import LEVEL_NAMES
from app.models import (
    Attempt, ContentCache, Course, Document, LevelChange, Question, Section, StrategyNote, StudyView,
)
from app.pdf import PdfError, pdf_to_sections
from app.schemas import (
    CourseIn, CourseOut, DocumentOut, LevelIn, SectionSummary, StrategyIn, SuggestionOut, UploadOut,
)

router = APIRouter(tags=["courses & chapters"])

MAX_PDF_BYTES = 20 * 1024 * 1024


def get_or_404(session: Session, model, id: int, message: str):
    row = session.get(model, id)
    if row is None:
        raise HTTPException(404, message)
    return row


def course_out(session: Session, course: Course) -> CourseOut:
    chapters = len(session.exec(
        select(Document.id).where(Document.course_id == course.id, Document.simulated == False)  # noqa: E712
    ).all())
    return CourseOut(
        id=course.id, name=course.name, icon=course.icon, level=course.level,
        level_name=LEVEL_NAMES[course.level], chapters=chapters, proposal=service.proposal_out(course),
    )


def document_out(session: Session, doc: Document) -> DocumentOut:
    sections = session.exec(select(Section).where(Section.document_id == doc.id).order_by(Section.position))
    return DocumentOut(
        **doc.model_dump(include={"id", "course_id", "title", "filename", "uploaded_at", "start_level", "suggested_level"}),
        sections=[SectionSummary(id=s.id, number=s.number, title=s.title) for s in sections],
    )


@router.get("/courses", response_model=list[CourseOut])
def list_courses(session: Session = Depends(get_session)):
    return [course_out(session, c) for c in session.exec(select(Course).order_by(Course.created_at))]


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(body: CourseIn, session: Session = Depends(get_session)):
    course = Course(name=body.name.strip(), icon=body.icon)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course_out(session, course)


@router.get("/courses/{course_id}", response_model=CourseOut)
def read_course(course_id: int, session: Session = Depends(get_session)):
    return course_out(session, get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα"))


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, session: Session = Depends(get_session)):
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    for doc in session.exec(select(Document).where(Document.course_id == course_id)):
        _delete_document(session, doc)
    for model in (Attempt, LevelChange, StrategyNote):
        session.exec(delete(model).where(model.course_id == course_id))
    session.delete(course)
    session.commit()


@router.post("/courses/{course_id}/level", response_model=CourseOut)
def change_level(course_id: int, body: LevelIn, session: Session = Depends(get_session)):
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    service.set_level(session, course, body.level, body.reason)
    session.commit()
    session.refresh(course)
    return course_out(session, course)


@router.post("/courses/{course_id}/proposal/decline", response_model=CourseOut)
def decline_proposal(course_id: int, session: Session = Depends(get_session)):
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    service.decline_proposal(session, course)
    session.commit()
    session.refresh(course)
    return course_out(session, course)


@router.post("/courses/{course_id}/strategy", status_code=204)
def save_strategy(course_id: int, body: StrategyIn, session: Session = Depends(get_session)):
    get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    session.add(StrategyNote(course_id=course_id, choice=body.choice))
    session.commit()


@router.get("/courses/{course_id}/documents", response_model=list[DocumentOut])
def list_documents(course_id: int, session: Session = Depends(get_session)):
    get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    docs = session.exec(
        select(Document).where(Document.course_id == course_id, Document.simulated == False)  # noqa: E712
        .order_by(Document.uploaded_at)
    )
    return [document_out(session, d) for d in docs]


def chapter_title(sections, filename: str) -> str:
    first = sections[0]
    if first.number is None and first.title != "Εισαγωγή":
        return first.title
    return Path(filename).stem.replace("_", " ").replace("-", " ")


@router.post("/courses/{course_id}/documents", response_model=UploadOut, status_code=201)
async def upload_document(course_id: int, file: UploadFile, session: Session = Depends(get_session)):
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "Το αρχείο είναι πολύ μεγάλο. Δοκίμασε ένα PDF μικρότερο από 20 MB.")
    try:
        sections = pdf_to_sections(data)
    except PdfError as err:
        raise HTTPException(422, str(err))
    if not sections:
        raise HTTPException(422, "Δεν βρήκα κείμενο σε αυτό το PDF. Δοκίμασε άλλο.")

    sha = hashlib.sha256(data).hexdigest()
    doc = session.exec(select(Document).where(Document.course_id == course_id, Document.sha256 == sha)).first()
    if doc is None:
        path = STORAGE_DIR / f"{sha}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        filename = Path(file.filename or "kefalaio.pdf").name
        doc = Document(course_id=course_id, filename=filename, title=chapter_title(sections, filename), sha256=sha, path=str(path))
        session.add(doc)
        session.flush()
        for position, s in enumerate(sections):
            session.add(Section(
                document_id=doc.id, position=position, number=s.number, title=s.title,
                paragraphs_json=json.dumps(s.paragraphs, ensure_ascii=False),
            ))
    suggestion = service.suggestion_for(session, course, doc.id)
    doc.suggested_level = suggestion.level
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return UploadOut(
        document=document_out(session, doc),
        suggestion=SuggestionOut(level=suggestion.level, level_name=LEVEL_NAMES[suggestion.level], reason=suggestion.reason),
        current_level=course.level,
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
def read_document(document_id: int, session: Session = Depends(get_session)):
    return document_out(session, get_or_404(session, Document, document_id, "Δεν βρέθηκε το κεφάλαιο"))


@router.post("/documents/{document_id}/start-level", response_model=CourseOut)
def choose_start_level(document_id: int, body: LevelIn, session: Session = Depends(get_session)):
    doc = get_or_404(session, Document, document_id, "Δεν βρέθηκε το κεφάλαιο")
    course = session.get(Course, doc.course_id)
    doc.start_level = body.level
    session.add(doc)
    if body.level != course.level:
        service.set_level(session, course, body.level, "new_chapter")
    session.commit()
    session.refresh(course)
    return course_out(session, course)


def _delete_document(session: Session, doc: Document) -> None:
    section_ids = list(session.exec(select(Section.id).where(Section.document_id == doc.id)))
    if section_ids:
        question_ids = list(session.exec(select(Question.id).where(Question.section_id.in_(section_ids))))
        if question_ids:
            session.exec(delete(Attempt).where(Attempt.question_id.in_(question_ids)))
        for model in (Question, ContentCache, StudyView):
            session.exec(delete(model).where(model.section_id.in_(section_ids)))
    session.exec(delete(Attempt).where(Attempt.document_id == doc.id))
    session.exec(delete(Section).where(Section.document_id == doc.id))
    if doc.path:
        others = session.exec(select(Document).where(Document.sha256 == doc.sha256, Document.id != doc.id)).first()
        if others is None:
            Path(doc.path).unlink(missing_ok=True)
    session.delete(doc)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, session: Session = Depends(get_session)):
    _delete_document(session, get_or_404(session, Document, document_id, "Δεν βρέθηκε το κεφάλαιο"))
    session.commit()
