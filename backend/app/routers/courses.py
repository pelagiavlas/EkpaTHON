import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlmodel import Session, delete, select

from app.db import STORAGE_DIR, get_session
from app.learning import service
from app.learning.fading import LEVEL_NAMES
from app.models import (
    Attempt, ContentCache, Course, Document, LevelChange, Milestone, Question, Section, SectionNote, SectionSupport,
    StrategyNote, Visit,
)
from app.pdf import PdfError, pdf_to_sections
from app.schemas import CourseIn, CourseOut, DocumentOut, SectionSummary, StrategyIn

router = APIRouter(tags=["courses & chapters"])

MAX_PDF_BYTES = 20 * 1024 * 1024


def get_or_404(session: Session, model, id: int, message: str):
    row = session.get(model, id)
    if row is None:
        raise HTTPException(404, message)
    return row


def course_out(session: Session, course: Course) -> CourseOut:
    docs = session.exec(
        select(Document.id).where(Document.course_id == course.id, Document.simulated == False)  # noqa: E712
    ).all()
    waiting = session.exec(
        select(SectionSupport).join(Section, Section.id == SectionSupport.section_id)
        .join(Document, Document.id == Section.document_id)
        .where(Document.course_id == course.id, SectionSupport.proposal_to != None)  # noqa: E711
    ).all()
    return CourseOut(id=course.id, name=course.name, icon=course.icon, chapters=len(docs), proposals=len(waiting))


def document_out(session: Session, doc: Document) -> DocumentOut:
    sections = session.exec(select(Section).where(Section.document_id == doc.id).order_by(Section.position))
    summaries = []
    for s in sections:
        sup = service.support(session, s.id)
        summaries.append(SectionSummary(
            id=s.id, number=s.number, title=s.title, level=sup.level, level_name=LEVEL_NAMES[sup.level],
            has_proposal=service.proposal_out(sup) is not None,
        ))
    return DocumentOut(
        **doc.model_dump(include={"id", "course_id", "title", "filename", "uploaded_at"}), sections=summaries,
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
    for model in (Attempt, StrategyNote):
        session.exec(delete(model).where(model.course_id == course_id))
    session.delete(course)
    session.commit()


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
    ).all()
    out = [document_out(session, d) for d in docs]
    session.commit()
    return out


def chapter_title(sections, filename: str) -> str:
    first = sections[0]
    if first.number is None and first.title != "Εισαγωγή":
        return first.title
    return Path(filename).stem.replace("_", " ").replace("-", " ")


@router.post("/courses/{course_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(course_id: int, file: UploadFile, session: Session = Depends(get_session)):
    """Straight to the sections: every new section starts at level 1, no placement question.
    A section on a topic already studied in this course gets a PROPOSAL, never a silent change."""
    course = get_or_404(session, Course, course_id, "Δεν βρέθηκε το μάθημα")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "Το αρχείο είναι πολύ μεγάλο. Δοκίμασε ένα PDF μικρότερο από 20 MB.")
    try:
        sections = pdf_to_sections(data)
    except PdfError as err:
        raise HTTPException(422, str(err))
    if not sections:
        raise HTTPException(422, "Δεν βρέθηκε κείμενο σε αυτό το PDF. Δοκίμασε άλλο.")

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
            row = Section(
                document_id=doc.id, position=position, number=s.number, title=s.title,
                paragraphs_json=json.dumps(s.paragraphs, ensure_ascii=False),
            )
            session.add(row)
            session.flush()
            session.add(SectionSupport(section_id=row.id))
            session.flush()
            service.propose_same_topic(session, row, course.id)
    session.commit()
    session.refresh(doc)
    return document_out(session, doc)


@router.get("/documents/{document_id}", response_model=DocumentOut)
def read_document(document_id: int, session: Session = Depends(get_session)):
    out = document_out(session, get_or_404(session, Document, document_id, "Δεν βρέθηκε το κεφάλαιο"))
    session.commit()
    return out


def _delete_document(session: Session, doc: Document) -> None:
    section_ids = list(session.exec(select(Section.id).where(Section.document_id == doc.id)))
    if section_ids:
        session.exec(delete(Attempt).where(Attempt.section_id.in_(section_ids)))
        for model in (Question, ContentCache, Visit, LevelChange, SectionNote, SectionSupport):
            session.exec(delete(model).where(model.section_id.in_(section_ids)))
        session.exec(delete(Milestone).where(Milestone.section_id.in_(section_ids)))
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
