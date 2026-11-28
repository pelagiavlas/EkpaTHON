"""Study a section, answer questions, climb the hint ladder. Everything per section level."""

import json
import os
import random
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import load_config
from app.content import get_provider
from app.content.mock import as_section_input
from app.content.schema import Block, EasyRead, QuestionContent
from app.db import get_session
from app.learning import answers, service
from app.learning.fading import SEARCH_FROM_LEVEL
from app.learning.locate import Location, locate
from app.models import (
    Attempt, ContentCache, Course, Document, Question, Section, SectionNote, StrategyNote, Visit,
)
from app.routers.courses import get_or_404
from app.schemas import (
    AnswerIn, AnswerOut, AttemptOut, ConceptOut, EasyOut, FlagsIn, HintOut, KeyPointsOut, LastStrategy, LevelIn, MilestoneOut,
    NoteIn, NoteOut, OptionOut, PickIn, PickOut, QuestionOut, QuestionsOut, SelfCheckIn, StudyOut, SupportOut, VisitOut,
)

router = APIRouter(tags=["study & questions"])


def demo_mode() -> bool:
    """DEMO_MODE=true in backend/.env turns on the level preview for presentations."""
    return os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes")

STRATEGY_LABELS = {"listen": "Να ακούσεις το κείμενο", "image": "Να δεις την εικόνα", "example": "Το παράδειγμα"}
LEVEL1_STEP3 = "Κοίτα ξανά τις δύο επιλογές. Διάβασέ τες ή άκουσέ τες μία-μία."
FALL_BACK = "Τώρα με εξήγηση."
NO_HELP_IN_EXAM = "Στην εξάσκηση δεν υπάρχει βοήθεια. Γράψε ό,τι θυμάσαι. Μετά βλέπεις το βασικό σημείο."
TERM = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


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


# --- reading ----------------------------------------------------------------------

@router.get("/sections/{section_id}/study", response_model=StudyOut)
def study(section_id: int, session: Session = Depends(get_session)):
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    doc, course = _context(session, section)
    siblings = list(session.exec(select(Section.id).where(Section.document_id == doc.id).order_by(Section.position)))
    index = siblings.index(section.id)
    easy = easy_read(session, section)
    sup = service.support(session, section.id)
    session.commit()
    return StudyOut(
        id=section.id, number=section.number, title=section.title,
        document_id=doc.id, document_title=doc.title, course_id=course.id, course_name=course.name,
        support=service.support_out(sup), position=index + 1, total=len(siblings),
        prev_id=siblings[index - 1] if index > 0 else None,
        next_id=siblings[index + 1] if index + 1 < len(siblings) else None,
        original=json.loads(section.paragraphs_json),
        easy=EasyOut(blocks=easy.blocks, glossary=easy.glossary, source=easy.source),
        demo=demo_mode(),
    )


@router.post("/sections/{section_id}/visits", response_model=VisitOut, status_code=201)
def start_visit(section_id: int, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    visit = Visit(section_id=section_id, level=service.support(session, section_id).level)
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return VisitOut(visit_id=visit.id)


@router.post("/visits/{visit_id}/easy", response_model=SupportOut)
def used_easy_text(visit_id: int, session: Session = Depends(get_session)):
    """The student opened the Easy-to-Read text. At levels 3-4, often -> a proposal (never a change)."""
    visit = get_or_404(session, Visit, visit_id, "Δεν βρέθηκε η επίσκεψη")
    visit.used_easy = True
    session.add(visit)
    session.flush()
    sup = service.check_easy_use(session, visit.section_id)
    session.commit()
    return service.support_out(sup)


# --- support level of a section (changes ONLY with the student's yes) --------------

@router.get("/sections/{section_id}/support", response_model=SupportOut)
def read_support(section_id: int, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    sup = service.support(session, section_id)
    session.commit()
    return service.support_out(sup)


@router.post("/sections/{section_id}/level", response_model=SupportOut)
def change_level(section_id: int, body: LevelIn, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    milestones = service.set_level(session, section_id, body.level, body.reason)
    session.commit()
    return service.support_out(service.support(session, section_id), milestones)


@router.post("/sections/{section_id}/proposal/decline", response_model=SupportOut)
def decline_proposal(section_id: int, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    sup = service.decline_proposal(session, section_id)
    session.commit()
    return service.support_out(sup)


# --- questions ----------------------------------------------------------------------

def mode_for(level: int, exam: bool = False) -> str:
    return "choice" if level <= 2 and not exam else "open"


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
def questions(section_id: int, exam: bool = False, session: Session = Depends(get_session)):
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    _, course = _context(session, section)
    level = service.support(session, section.id).level
    if exam and level < 4:
        raise HTTPException(409, "Η εξάσκηση σαν στις εξετάσεις υπάρχει όταν μελετάς την ενότητα «Αυτόνομα».")
    mode = mode_for(level, exam)
    out = []
    for q in load_questions(session, section, level):
        c = content_of(q)
        out.append(QuestionOut(
            id=q.id, prompt=c.prompt, image=c.image if level <= 2 else None, image_alt=c.image_alt, mode=mode,
            options=options_out(c, shown_option_ids(q.id, c, level)) if mode == "choice" else [],
        ))
    last = session.exec(
        select(StrategyNote).where(StrategyNote.course_id == course.id).order_by(StrategyNote.created_at.desc())
    ).first()
    ask = level == 3 and not exam
    return QuestionsOut(
        section_id=section.id, course_id=course.id, level=level, exam=exam, questions=out, ask_strategy=ask,
        last_strategy=LastStrategy(choice=last.choice, label=STRATEGY_LABELS[last.choice]) if last and ask else None,
    )


@router.post("/questions/{question_id}/attempts", response_model=AttemptOut, status_code=201)
def start_attempt(question_id: int, exam: bool = False, session: Session = Depends(get_session)):
    question = get_or_404(session, Question, question_id, "Δεν βρέθηκε η ερώτηση")
    section = session.get(Section, question.section_id)
    doc, course = _context(session, section)
    level = service.support(session, section.id).level
    content = content_of(question)
    open_question = exam or mode_for(level) == "open"
    attempt = Attempt(
        question_id=question.id, section_id=section.id, course_id=course.id, document_id=doc.id,
        level=level, mode="exam" if exam else "question", concept=content.concept,
        shown_options=0 if open_question else len(shown_option_ids(question.id, content, level)),
    )
    session.add(attempt)
    milestones: list[MilestoneOut] = []
    if level >= SEARCH_FROM_LEVEL:
        last_visit = session.exec(
            select(Visit).where(Visit.section_id == section.id).order_by(Visit.created_at.desc())
        ).first()
        if last_visit and not last_visit.used_easy:
            milestones = service.award(session, "first_original", section.id)
    session.commit()
    session.refresh(attempt)
    return AttemptOut(attempt_id=attempt.id, new_milestones=milestones)


def _open_attempt(session: Session, attempt_id: int) -> tuple[Attempt, Question | None, QuestionContent | None]:
    attempt = get_or_404(session, Attempt, attempt_id, "Δεν βρέθηκε η προσπάθεια")
    if attempt.correct is not None:
        raise HTTPException(409, "Αυτή η ερώτηση έχει τελειώσει. Συνέχισε στην επόμενη.")
    if attempt.question_id is None:
        return attempt, None, None
    question = session.get(Question, attempt.question_id)
    return attempt, question, content_of(question)


def _location(session: Session, attempt: Attempt, content: QuestionContent) -> Location | None:
    section = session.get(Section, attempt.section_id)
    return locate(json.loads(section.paragraphs_json), content)


def _example_block(session: Session, section_id: int) -> Block | None:
    section = session.get(Section, section_id)
    return next((b for b in easy_read(session, section).blocks if b.type == "example"), None)


def _explain_hint(session: Session, attempt: Attempt, question: Question, content: QuestionContent, fell_back: bool = False) -> HintOut:
    """Hints that explain: levels 1-2, and at levels 3-4 only after searching did not work."""
    if attempt.hints_used >= len(content.hints):
        raise HTTPException(409, "Είδες όλες τις υποδείξεις. Δοκίμασε τώρα να απαντήσεις.")
    hint = content.hints[attempt.hints_used]
    attempt.hints_used += 1
    session.add(attempt)
    text, choices = hint.text, []
    if hint.step == 3:
        ids = [0, 1]
        random.Random(question.id).shuffle(ids)
        choices = options_out(content, ids)
        if attempt.level == 1:
            text = LEVEL1_STEP3
    example = _example_block(session, question.section_id) if hint.action == "replay_example" else None
    action = hint.action if example or hint.action != "replay_example" else "open_section"
    return HintOut(
        kind="explain", step=hint.step, text=f"{FALL_BACK} {text}" if fell_back else text, action=action,
        section_id=question.section_id if action else None, choices=choices, example=example, fell_back=fell_back,
    )


def _fall_back(session: Session, attempt: Attempt, question: Question, content: QuestionContent) -> HintOut:
    attempt.fell_back = True  # counted as "needed more help" by the fading rules
    return _explain_hint(session, attempt, question, content, fell_back=True)


def _search_hint(attempt: Attempt, content: QuestionContent, loc: Location | None) -> HintOut:
    """Levels 3-4: nothing is explained, only WHERE to look in the original text."""
    step = attempt.search_steps
    if step == 1:
        where = f"στην ενότητα {content.section_number}" if content.section_number else "σε αυτή την ενότητα"
        return HintOut(kind="search", step=1, text=f"Η απάντηση είναι {where}. Διάβασέ την ξανά.",
                       action="open_original", section_id=attempt.section_id)
    if step == 2:
        return HintOut(kind="search", step=2, text=f"Είναι στην {loc.paragraph + 1}η παράγραφο.",
                       action="highlight_paragraph", section_id=attempt.section_id, paragraph=loc.paragraph)
    what = f"λέει {content.source_hint}" if content.source_hint else "απαντά στην ερώτηση"
    return HintOut(kind="search", step=3, text=f"Βρες την πρόταση που {what}. Πάτησέ την.",
                   action="pick_sentence", section_id=attempt.section_id, paragraph=loc.paragraph, sentences=loc.sentences)


@router.post("/attempts/{attempt_id}/hint", response_model=HintOut)
def next_hint(attempt_id: int, session: Session = Depends(get_session)):
    attempt, question, content = _open_attempt(session, attempt_id)
    if attempt.mode == "exam":
        raise HTTPException(409, NO_HELP_IN_EXAM)
    if content is None:
        raise HTTPException(409, "Εδώ δεν υπάρχουν υποδείξεις.")
    if attempt.level >= SEARCH_FROM_LEVEL and not attempt.fell_back:
        loc = _location(session, attempt, content)
        search_steps = 3 if loc else 1  # without a target sentence only "read the section again"
        if attempt.search_steps < search_steps and not attempt.found_sentence:
            attempt.search_steps += 1
            session.add(attempt)
            session.commit()
            return _search_hint(attempt, content, loc)
        # Searching is over (or the sentence was found and more help is still wanted): step δ.
        hint = _fall_back(session, attempt, question, content)
        session.commit()
        return hint
    hint = _explain_hint(session, attempt, question, content)
    session.commit()
    return hint


@router.post("/attempts/{attempt_id}/pick", response_model=PickOut)
def pick_sentence(attempt_id: int, body: PickIn, session: Session = Depends(get_session)):
    """Level 3-4 step γ: the student taps the sentence they think answers the question.
    The right sentence is checked here, it is never sent to the browser."""
    attempt, question, content = _open_attempt(session, attempt_id)
    if content is None or attempt.search_steps < 3 or attempt.fell_back or attempt.found_sentence:
        raise HTTPException(409, "Πάτησε πρώτα «Βοήθεια» για να ψάξεις την πρόταση.")
    loc = _location(session, attempt, content)
    if loc is None or body.sentence >= len(loc.sentences):
        raise HTTPException(422, "Διάλεξε μία από τις προτάσεις της παραγράφου.")
    if body.sentence == loc.sentence:
        attempt.found_sentence = True
        session.add(attempt)
        milestones = service.award(session, "first_found_sentence", attempt.section_id)
        session.commit()
        return PickOut(correct=True, message="Τη βρήκες. Τώρα απάντησε την ερώτηση.", new_milestones=milestones)

    search = load_config().search
    attempt.wrong_picks += 1
    session.add(attempt)
    if attempt.wrong_picks >= search.max_wrong_picks:
        hint = _fall_back(session, attempt, question, content)
        session.commit()
        return PickOut(correct=False, message=f"Δεν είναι αυτή. {FALL_BACK}", fallback_hint=hint)
    session.commit()
    if attempt.wrong_picks == search.max_wrong_picks - 1:
        return PickOut(correct=False, message="Δεν είναι αυτή. Θες βοήθεια; Πάτησε «Βοήθεια».")
    return PickOut(correct=False, message="Δεν είναι αυτή. Ψάξε στην ίδια παράγραφο.")


def _finish(session: Session, attempt: Attempt, correct: bool) -> tuple:
    attempt.correct = correct
    attempt.awaiting_self_check = False
    attempt.finished_at = datetime.now()
    session.add(attempt)
    session.flush()
    milestones: list[MilestoneOut] = []
    proposal = None
    service.record_evidence(session, attempt)  # knowledge tracing (not for self-check or key points)
    session.flush()
    if attempt.mode == "exam":  # practice updates what is known, but never proposes a change by itself
        milestones += service.award(session, "first_exam", attempt.section_id)
    else:
        if correct and attempt.mode == "question" and not (attempt.hints_used or attempt.search_steps or attempt.wrong_tries):
            milestones += service.award(session, "first_no_help", attempt.section_id)
        proposal = service.proposal_out(service.update_proposal(session, attempt.section_id, attempt.concept))
    session.commit()
    return proposal, milestones


@router.post("/attempts/{attempt_id}/answer", response_model=AnswerOut)
def answer(attempt_id: int, body: AnswerIn, session: Session = Depends(get_session)):
    attempt, question, content = _open_attempt(session, attempt_id)
    if content is None:
        raise HTTPException(409, "Εδώ δεν υπάρχει ερώτηση για απάντηση.")

    if body.option_id is not None:
        two_choices = {0, 1} if attempt.hints_used >= 3 else set()  # explaining hint 3 shows two choices
        if mode_for(attempt.level, attempt.mode == "exam") == "open":
            allowed = two_choices
        else:
            allowed = set(shown_option_ids(question.id, content, attempt.level)) | two_choices
        if body.option_id not in allowed:
            raise HTTPException(422, "Διάλεξε μία από τις επιλογές που βλέπεις.")
        if body.option_id == 0:
            proposal, ms = _finish(session, attempt, True)
            return AnswerOut(outcome="correct", message=answers.CORRECT, key_point=content.key_point, done=True,
                             proposal=proposal, new_milestones=ms)
        attempt.wrong_tries += 1
        session.add(attempt)
        session.commit()
        return AnswerOut(outcome="try_again", message=answers.TRY_AGAIN, key_point=None, done=False)

    text = (body.text or "").strip()
    if not text:
        raise HTTPException(422, "Γράψε την απάντησή σου ή πάτησε «Βοήθεια».")
    if answers.matches_open_answer(content, text):
        proposal, ms = _finish(session, attempt, True)
        return AnswerOut(outcome="correct", message=answers.CORRECT, key_point=content.key_point, done=True,
                         proposal=proposal, new_milestones=ms)
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
    proposal, ms = _finish(session, attempt, body.close)
    if attempt.mode == "keypoints":
        message = answers.KEYPOINTS_YES if body.close else answers.KEYPOINTS_NO
    else:
        message = answers.SELF_CHECK_YES if body.close else answers.SELF_CHECK_NO
    return AnswerOut(outcome="correct" if body.close else "not_yet", message=message,
                     key_point=content.key_point if content else None, done=True, proposal=proposal, new_milestones=ms)


@router.post("/attempts/{attempt_id}/explain", response_model=AnswerOut)
def explain(attempt_id: int, session: Session = Depends(get_session)):
    """The explanation is shown only after the student has tried at least once."""
    attempt, _, content = _open_attempt(session, attempt_id)
    if content is None or (attempt.wrong_tries == 0 and not attempt.awaiting_self_check):
        raise HTTPException(409, "Πρώτα δοκίμασε μία απάντηση. Μετά θα δεις την εξήγηση.")
    proposal, ms = _finish(session, attempt, False)
    return AnswerOut(outcome="explained", message=answers.EXPLAINED, key_point=content.key_point, done=True,
                     proposal=proposal, new_milestones=ms)


@router.post("/attempts/{attempt_id}/flags", status_code=204)
def flags(attempt_id: int, body: FlagsIn, session: Session = Depends(get_session)):
    attempt = get_or_404(session, Attempt, attempt_id, "Δεν βρέθηκε η προσπάθεια")
    if body.listened:
        attempt.listened = True
    if body.opened_section:
        attempt.opened_section = True
    session.add(attempt)
    session.commit()


@router.get("/sections/{section_id}/concepts", response_model=list[ConceptOut])
def section_concepts(section_id: int, session: Session = Depends(get_session)):
    """Concepts of this section the student has already met, in words only."""
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    _, course = _context(session, section)
    rows = [service.mastery(session, course.id, c, create=False) for c in service.section_concepts(section)]
    return [service.concept_out(r) for r in rows if r is not None and r.observations > 0]


# --- level 4: key points and own questions -------------------------------------------

def key_points(session: Session, section: Section, level: int) -> list[str]:
    easy = easy_read(session, section)
    points = [TERM.sub(r"\1", b.text) for b in easy.blocks if b.type == "key"]
    points += [content_of(q).key_point for q in load_questions(session, section, level)]
    return list(dict.fromkeys(points))


@router.post("/sections/{section_id}/keypoints", response_model=KeyPointsOut, status_code=201)
def write_key_points(section_id: int, body: NoteIn, session: Session = Depends(get_session)):
    """The student writes what they kept. Only then the section's key points are shown,
    and the student compares by themselves."""
    section = get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    doc, course = _context(session, section)
    level = service.support(session, section.id).level
    session.add(SectionNote(section_id=section.id, kind="keypoints", text=body.text.strip()))
    attempt = Attempt(section_id=section.id, course_id=course.id, document_id=doc.id, level=level,
                      mode="keypoints", awaiting_self_check=True)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return KeyPointsOut(attempt_id=attempt.id, key_points=key_points(session, section, level))


@router.post("/sections/{section_id}/my-questions", response_model=NoteOut, status_code=201)
def add_own_question(section_id: int, body: NoteIn, session: Session = Depends(get_session)):
    get_or_404(session, Section, section_id, "Δεν βρέθηκε η ενότητα")
    note = SectionNote(section_id=section_id, kind="question", text=body.text.strip())
    session.add(note)
    session.commit()
    session.refresh(note)
    return NoteOut(id=note.id, kind=note.kind, text=note.text, created_at=note.created_at)


@router.get("/sections/{section_id}/my-questions", response_model=list[NoteOut])
def list_own_questions(section_id: int, session: Session = Depends(get_session)):
    notes = session.exec(
        select(SectionNote).where(SectionNote.section_id == section_id, SectionNote.kind == "question")
        .order_by(SectionNote.created_at)
    )
    return [NoteOut(id=n.id, kind=n.kind, text=n.text, created_at=n.created_at) for n in notes]
