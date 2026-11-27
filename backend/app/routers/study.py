"""Study a section, answer questions, climb the hint ladder."""

import json
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.content import get_provider
from app.content.mock import as_section_input
from app.content.schema import Block, EasyRead, QuestionContent
from app.db import get_session
from app.learning import answers, service
from app.models import Attempt, ContentCache, Course, Document, Question, Section, StrategyNote, StudyView
from app.routers.courses import get_or_404
from app.schemas import (
    AnswerIn, AnswerOut, AttemptOut, EasyOut, FlagsIn, HintOut, LastStrategy, OptionOut, QuestionOut,
    QuestionsOut, SelfCheckIn, StudyOut, ViewIn,
)

router = APIRouter(tags=["study & questions"])

STRATEGY_LABELS = {"listen": "Να ακούσεις το κείμενο", "image": "Να δεις την εικόνα", "example": "Το παράδειγμα"}
LEVEL1_STEP3 = "Κοίτα ξανά τις δύο επιλογές. Διάβασέ τες ή άκουσέ τες μία-μία."


def _provider_call(fn, *args):
    try:
        return fn(*args)
    except NotImplementedError as err:
        raise HTTPException(503, str(err))


def _context(session: Session, section: Section) -> tuple[Document, Course]:
    doc = session.get(Document, section.document_id)
    return doc, session.get(Course, doc.course_id)


def easy_read(session: Session, section: Section) -> EasyRead:
    cached = session.get(ContentCache, section.id)
    if cached:
        return EasyRead.model_validate_json(cached.easy_json)
    easy = _provider_call(get_provider().simplify, as_section_input(section.number, section.title, section.paragraphs_json))
    session.add(ContentCache(section_id=section.id, easy_json=easy.model_dump_json()))
    session.commit()
    return easy


@router.get("/sections/{section_id}/study", response_model=StudyOut)
def study(section_id: int, session: Session = Depends(get_session)):
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    doc, course = _context(session, section)
    siblings = list(session.exec(select(Section.id).where(Section.document_id == doc.id).order_by(Section.position)))
    index = siblings.index(section.id)
    easy = easy_read(session, section)
    return StudyOut(
        id=section.id, number=section.number, title=section.title,
        document_id=doc.id, document_title=doc.title, course_id=course.id, course_name=course.name,
        level=course.level, position=index + 1, total=len(siblings),
        prev_id=siblings[index - 1] if index > 0 else None,
        next_id=siblings[index + 1] if index + 1 < len(siblings) else None,
        original=json.loads(section.paragraphs_json),
        easy=EasyOut(blocks=easy.blocks, glossary=easy.glossary, source=easy.source),
    )


@router.post("/sections/{section_id}/views", status_code=204)
def record_view(section_id: int, body: ViewIn, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    session.add(StudyView(section_id=section_id, mode=body.mode))
    session.commit()


# --- questions ----------------------------------------------------------------

def mode_for(level: int) -> str:
    return "choice" if level <= 2 else "open"


def shown_option_ids(question_id: int, content: QuestionContent, level: int) -> list[int]:
    """Level 1: two options, level 2: three. Order is mixed but stable per question."""
    count = 2 if level == 1 else len(content.options)
    ids = list(range(min(count, len(content.options))))
    random.Random(question_id).shuffle(ids)
    return ids


def options_out(content: QuestionContent, ids: list[int]) -> list[OptionOut]:
    return [OptionOut(id=i, text=content.options[i].text, image=content.options[i].image) for i in ids]


def load_questions(session: Session, section: Section, level: int) -> list[Question]:
    rows = list(session.exec(
        select(Question).where(Question.section_id == section.id, Question.level == level).order_by(Question.position)
    ))
    if rows:
        return rows
    provider = get_provider()
    contents = _provider_call(provider.make_questions, as_section_input(section.number, section.title, section.paragraphs_json), level)
    for position, content in enumerate(contents):
        content.hints = _provider_call(provider.make_hints, content)
        row = Question(section_id=section.id, level=level, position=position, content_json=content.model_dump_json())
        session.add(row)
        rows.append(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def content_of(question: Question) -> QuestionContent:
    return QuestionContent.model_validate_json(question.content_json)


@router.get("/sections/{section_id}/questions", response_model=QuestionsOut)
def questions(section_id: int, session: Session = Depends(get_session)):
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    _, course = _context(session, section)
    level = course.level
    out = []
    for q in load_questions(session, section, level):
        c = content_of(q)
        mode = mode_for(level)
        out.append(QuestionOut(
            id=q.id, prompt=c.prompt, image=c.image if level <= 2 else None, image_alt=c.image_alt, mode=mode,
            options=options_out(c, shown_option_ids(q.id, c, level)) if mode == "choice" else [],
        ))
    last = session.exec(
        select(StrategyNote).where(StrategyNote.course_id == course.id).order_by(StrategyNote.created_at.desc())
    ).first()
    return QuestionsOut(
        section_id=section.id, course_id=course.id, level=level, questions=out,
        ask_strategy=level == 3,
        last_strategy=LastStrategy(choice=last.choice, label=STRATEGY_LABELS[last.choice]) if last and level == 3 else None,
    )


@router.post("/questions/{question_id}/attempts", response_model=AttemptOut, status_code=201)
def start_attempt(question_id: int, session: Session = Depends(get_session)):
    question = get_or_404(session, Question, question_id, "Δεν βρέθηκε η ερώτηση")
    section = session.get(Section, question.section_id)
    doc, course = _context(session, section)
    attempt = Attempt(question_id=question.id, course_id=course.id, document_id=doc.id, level=course.level)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return AttemptOut(attempt_id=attempt.id, hints_used=0)


def _open_attempt(session: Session, attempt_id: int) -> tuple[Attempt, Question, QuestionContent]:
    attempt = get_or_404(session, Attempt, attempt_id, "Δεν βρέθηκε η προσπάθεια")
    if attempt.correct is not None:
        raise HTTPException(409, "Αυτή η ερώτηση έχει τελειώσει. Πάμε στην επόμενη.")
    question = session.get(Question, attempt.question_id)
    return attempt, question, content_of(question)


def _example_block(session: Session, section_id: int) -> Block | None:
    section = session.get(Section, section_id)
    return next((b for b in easy_read(session, section).blocks if b.type == "example"), None)


@router.post("/attempts/{attempt_id}/hint", response_model=HintOut)
def next_hint(attempt_id: int, session: Session = Depends(get_session)):
    attempt, question, content = _open_attempt(session, attempt_id)
    if attempt.hints_used >= len(content.hints):
        raise HTTPException(409, "Είδες όλες τις υποδείξεις. Δοκίμασε τώρα να απαντήσεις.")
    hint = content.hints[attempt.hints_used]
    attempt.hints_used += 1
    session.add(attempt)
    session.commit()

    text, choices = hint.text, []
    if hint.step == 3:
        ids = [0, 1]
        random.Random(question.id).shuffle(ids)
        choices = options_out(content, ids)
        if attempt.level == 1:
            text = LEVEL1_STEP3
    example = _example_block(session, question.section_id) if hint.action == "replay_example" else None
    if hint.action == "replay_example" and example is None:
        hint = hint.model_copy(update={"action": "open_section"})
    return HintOut(
        step=hint.step, text=text, action=hint.action,
        section_id=question.section_id if hint.action else None, choices=choices, example=example,
    )


def _finish(session: Session, attempt: Attempt, correct: bool) -> AnswerOut | None:
    attempt.correct = correct
    attempt.awaiting_self_check = False
    attempt.finished_at = datetime.now()
    session.add(attempt)
    session.flush()
    course = session.get(Course, attempt.course_id)
    service.update_proposal(session, course)
    session.commit()
    session.refresh(course)
    return service.proposal_out(course)


@router.post("/attempts/{attempt_id}/answer", response_model=AnswerOut)
def answer(attempt_id: int, body: AnswerIn, session: Session = Depends(get_session)):
    attempt, question, content = _open_attempt(session, attempt_id)

    if body.option_id is not None:
        two_choices = {0, 1} if attempt.hints_used >= 3 else set()  # hint step 3 shows two choices
        if mode_for(attempt.level) == "open":
            allowed = two_choices
        else:
            allowed = set(shown_option_ids(question.id, content, attempt.level)) | two_choices
        if body.option_id not in allowed:
            raise HTTPException(422, "Διάλεξε μία από τις επιλογές που βλέπεις.")
        if body.option_id == 0:
            proposal = _finish(session, attempt, True)
            return AnswerOut(outcome="correct", message=answers.CORRECT, key_point=content.key_point, done=True, proposal=proposal)
        attempt.wrong_tries += 1
        session.add(attempt)
        session.commit()
        return AnswerOut(outcome="try_again", message=answers.TRY_AGAIN, key_point=None, done=False)

    text = (body.text or "").strip()
    if not text:
        raise HTTPException(422, "Γράψε την απάντησή σου ή πάτησε «Βοήθεια».")
    if answers.matches_open_answer(content, text):
        proposal = _finish(session, attempt, True)
        return AnswerOut(outcome="correct", message=answers.CORRECT, key_point=content.key_point, done=True, proposal=proposal)
    attempt.awaiting_self_check = True
    session.add(attempt)
    session.commit()
    return AnswerOut(outcome="self_check", message=answers.SELF_CHECK, key_point=content.key_point, done=False)


@router.post("/attempts/{attempt_id}/self-check", response_model=AnswerOut)
def self_check(attempt_id: int, body: SelfCheckIn, session: Session = Depends(get_session)):
    attempt, _, content = _open_attempt(session, attempt_id)
    if not attempt.awaiting_self_check:
        raise HTTPException(409, "Πρώτα γράψε την απάντησή σου.")
    attempt.self_checked = True
    proposal = _finish(session, attempt, body.close)
    message = answers.SELF_CHECK_YES if body.close else answers.SELF_CHECK_NO
    return AnswerOut(outcome="correct" if body.close else "not_yet", message=message, key_point=content.key_point, done=True, proposal=proposal)


@router.post("/attempts/{attempt_id}/explain", response_model=AnswerOut)
def explain(attempt_id: int, session: Session = Depends(get_session)):
    """The explanation is shown only after the student has tried at least once."""
    attempt, _, content = _open_attempt(session, attempt_id)
    if attempt.wrong_tries == 0 and not attempt.awaiting_self_check:
        raise HTTPException(409, "Πρώτα δοκίμασε μία απάντηση. Μετά σου δείχνω την εξήγηση.")
    proposal = _finish(session, attempt, False)
    return AnswerOut(outcome="explained", message=answers.EXPLAINED, key_point=content.key_point, done=True, proposal=proposal)


@router.post("/attempts/{attempt_id}/flags", status_code=204)
def flags(attempt_id: int, body: FlagsIn, session: Session = Depends(get_session)):
    attempt = get_or_404(session, Attempt, attempt_id, "Δεν βρέθηκε η προσπάθεια")
    if body.listened:
        attempt.listened = True
    if body.opened_section:
        attempt.opened_section = True
    session.add(attempt)
    session.commit()
