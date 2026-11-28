"""«Δεν ξέρω αυτή τη λέξη» and «Οι λέξεις μου» (the student's own vocabulary)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.content import get_provider
from app.content.mock import as_section_input
from app.db import get_session
from app.models import ContentReport, Section, WordLookup
from app.routers.courses import get_or_404

router = APIRouter(tags=["words"])

NO_EXPLANATION = "Δεν έχουμε ακόμα εξήγηση για αυτή τη λέξη. Τη σημειώσαμε, για να τη δει κάποιος."


class WordIn(BaseModel):
    word: str = Field(min_length=1, max_length=60)


class WordOut(BaseModel):
    id: int
    word: str
    term: str | None
    gloss: str | None
    found: bool
    message: str | None
    created_at: datetime


def word_out(w: WordLookup) -> WordOut:
    return WordOut(id=w.id, word=w.word, term=w.term, gloss=w.gloss, found=w.found,
                   message=None if w.found else NO_EXPLANATION, created_at=w.created_at)


def clean(word: str) -> str:
    return word.strip().strip(".,;:!«»()\"'·…-–").strip()


@router.post("/sections/{section_id}/words", response_model=WordOut, status_code=201)
def look_up(section_id: int, body: WordIn, session: Session = Depends(get_session)):
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    word = clean(body.word)
    if not word:
        raise HTTPException(422, "Διάλεξε μια λέξη.")
    try:
        entry = get_provider().explain_word(word, as_section_input(section.number, section.title, section.paragraphs_json))
    except NotImplementedError:
        entry = None
    row = WordLookup(word=word, term=entry.term if entry else None, gloss=entry.gloss if entry else None,
                     section_id=section.id, found=entry is not None)
    session.add(row)
    if entry is None:  # the reviewer sees words that need an explanation (anonymous)
        session.add(ContentReport(section_id=section.id, kind="word", word=word))
    session.commit()
    session.refresh(row)
    return word_out(row)


@router.get("/words", response_model=list[WordOut])
def my_words(session: Session = Depends(get_session)):
    """One row per word (the latest lookup), newest first."""
    seen, out = set(), []
    for w in session.exec(select(WordLookup).order_by(WordLookup.created_at.desc(), WordLookup.id.desc())):
        key = (w.term or w.word).lower()
        if key not in seen:
            seen.add(key)
            out.append(word_out(w))
    return out


@router.delete("/words/{word_id}", status_code=204)
def remove_word(word_id: int, session: Session = Depends(get_session)):
    """Remove a word from «Οι λέξεις μου» (all lookups of the same word)."""
    w = get_or_404(session, WordLookup, word_id, "Δεν βρέθηκε η λέξη")
    key = (w.term or w.word).lower()
    for row in session.exec(select(WordLookup)):
        if (row.term or row.word).lower() == key:
            session.delete(row)
    session.commit()
