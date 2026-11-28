"""Human review of AI-made content, student reports, and an anonymous summary for the teacher.

The review screen is on only with REVIEW_MODE=true (backend/.env) or in demo mode.
No student is named anywhere: reports have no author.

About the teacher summary: this app keeps data on the student's own device, so here it
counts the reports of THIS device only. A real summary over many students needs a central
service with consent (docs/future-features.md). There, a count is shown only from
`aggregate_min_count` reports up (config.toml, default 5), so that nobody can be identified.
"""

import json
import os
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import load_config
from app.db import get_session
from app.ekpa.clock import demo_enabled
from app.learning.service import section_label
from app.models import ContentCache, ContentReport, Course, Document, Section
from app.routers.courses import get_or_404
from app.routers.study import easy_read
from app.content.schema import Block, GlossaryEntry

router = APIRouter(tags=["review & reports"])

KIND_LABELS = {
    "unclear": "Δεν το καταλαβαίνω",
    "wrong": "Νομίζω ότι είναι λάθος",
    "missing": "Λείπει κάτι",
    "word": "Δεν ξέρω αυτή τη λέξη",
}


class ReportIn(BaseModel):
    kind: str = Field(pattern="^(unclear|wrong|missing)$")
    block_index: int | None = Field(None, ge=0)
    comment: str | None = Field(None, max_length=1000)


class ReviewItem(BaseModel):
    section_id: int
    label: str
    course: str
    document: str
    status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    original: list[str]
    blocks: list[Block]
    glossary: list[GlossaryEntry]
    reports: int


class ApproveIn(BaseModel):
    reviewed_by: str = Field(min_length=1, max_length=100)


class ReportOut(BaseModel):
    id: int
    section: str
    kind: str
    kind_label: str
    block_index: int | None
    word: str | None
    comment: str | None
    created_at: datetime


class SummaryRow(BaseModel):
    section: str
    unclear: int


class SummaryOut(BaseModel):
    min_count: int
    demo_threshold: bool  # True: a lower threshold, only for the presentation
    rows: list[SummaryRow]


def review_enabled(demo: bool) -> bool:
    return os.getenv("REVIEW_MODE", "false").strip().lower() in ("1", "true", "yes") or demo_enabled(demo)


def require_review(demo: bool) -> None:
    if not review_enabled(demo):
        raise HTTPException(403, "Ο έλεγχος περιεχομένου δεν είναι ενεργός. Βάλε REVIEW_MODE=true.")


@router.get("/features")
def features(demo: bool = False):
    f = load_config().features
    return {"help_now": f.help_now, "alerts": f.alerts, "forum": f.forum,
            "review": review_enabled(demo), "demo": demo_enabled(demo)}


@router.post("/sections/{section_id}/reports", status_code=201)
def report(section_id: int, body: ReportIn, session: Session = Depends(get_session)):
    """«Κάτι δεν μου φαίνεται σωστό». Anonymous: nothing about the student is stored."""
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    comment = (body.comment or "").strip() or None
    session.add(ContentReport(section_id=section_id, block_index=body.block_index, kind=body.kind, comment=comment))
    session.commit()
    return {"message": "Ευχαριστούμε. Θα το δει κάποιος."}


def _context(session: Session, section: Section) -> tuple[Document, Course]:
    doc = session.get(Document, section.document_id)
    return doc, session.get(Course, doc.course_id)


@router.get("/review/sections", response_model=list[ReviewItem])
def review_sections(status: str = "ai_draft", demo: bool = False, session: Session = Depends(get_session)):
    require_review(demo)
    counts = Counter(r.section_id for r in session.exec(select(ContentReport)))
    items = []
    sections = session.exec(
        select(Section).join(Document, Document.id == Section.document_id)
        .where(Document.simulated == False).order_by(Document.uploaded_at, Section.position)  # noqa: E712
    ).all()
    for s in sections:
        easy = easy_read(session, s)
        cache = session.get(ContentCache, s.id)
        if status != "all" and cache.review_status != status:
            continue
        doc, course = _context(session, s)
        items.append(ReviewItem(
            section_id=s.id, label=section_label(s), course=course.name, document=doc.title,
            status=cache.review_status, reviewed_by=cache.reviewed_by, reviewed_at=cache.reviewed_at,
            original=json.loads(s.paragraphs_json), blocks=easy.blocks, glossary=easy.glossary, reports=counts[s.id],
        ))
    return items


@router.post("/review/sections/{section_id}/approve", response_model=ReviewItem)
def approve(section_id: int, body: ApproveIn, demo: bool = False, session: Session = Depends(get_session)):
    require_review(demo)
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    easy_read(session, section)
    cache = session.get(ContentCache, section_id)
    cache.review_status, cache.reviewed_by, cache.reviewed_at = "reviewed", body.reviewed_by.strip(), datetime.now()
    session.add(cache)
    session.commit()
    return next(i for i in review_sections("all", demo, session) if i.section_id == section_id)


@router.post("/review/sections/{section_id}/reopen", response_model=ReviewItem)
def reopen(section_id: int, demo: bool = False, session: Session = Depends(get_session)):
    """Undo an approval: back to draft."""
    require_review(demo)
    cache = get_or_404(session, ContentCache, section_id, "Δεν βρέθηκε η ενότητα")
    cache.review_status, cache.reviewed_by, cache.reviewed_at = "ai_draft", None, None
    session.add(cache)
    session.commit()
    return next(i for i in review_sections("all", demo, session) if i.section_id == section_id)


@router.get("/review/reports", response_model=list[ReportOut])
def reports(demo: bool = False, session: Session = Depends(get_session)):
    require_review(demo)
    out = []
    for r in session.exec(select(ContentReport).order_by(ContentReport.created_at.desc())):
        s = session.get(Section, r.section_id)
        out.append(ReportOut(id=r.id, section=section_label(s), kind=r.kind, kind_label=KIND_LABELS[r.kind],
                             block_index=r.block_index, word=r.word, comment=r.comment, created_at=r.created_at))
    return out


@router.get("/review/summary", response_model=SummaryOut)
def summary(demo: bool = False, session: Session = Depends(get_session)):
    """For the teacher: which sections get the most «Δεν το καταλαβαίνω». Counts only, anonymous."""
    require_review(demo)
    cfg = load_config().review
    lowered = demo_enabled(demo)
    min_count = cfg.demo_min_count if lowered else cfg.aggregate_min_count
    counts = Counter(r.section_id for r in session.exec(select(ContentReport).where(ContentReport.kind == "unclear")))
    rows = [
        SummaryRow(section=section_label(session.get(Section, sid)), unclear=n)
        for sid, n in counts.most_common() if n >= min_count
    ]
    return SummaryOut(min_count=min_count, demo_threshold=lowered, rows=rows)
