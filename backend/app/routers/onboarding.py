"""First use: «Θέλεις κάποιος να σε βοηθήσει να ξεκινήσεις;» and the start guide.

The guide is written to the student, who does it together with a person they chose
(e.g. a parent, a friend, a volunteer). Its practice question is checked here but
nothing about it is stored.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.ekpa.clock import demo_enabled
from app.learning import practice
from app.models import Profile
from app.routers.progress import get_profile
from app.schemas import (
    PracticeAnswerIn, PracticeAnswerOut, PracticeOut, PracticeQuestionOut, StartIn, StartOut, StartStepIn,
)

router = APIRouter(tags=["first use"])


def start_out(profile: Profile) -> StartOut:
    return StartOut(choice=profile.start_choice, step=profile.start_step, done=profile.start_done)


@router.get("/start", response_model=StartOut)
def read_start(session: Session = Depends(get_session)):
    return start_out(get_profile(session))


@router.post("/start", response_model=StartOut)
def answer_start(body: StartIn, session: Session = Depends(get_session)):
    """Ναι (open the guide) or «Όχι, θα ξεκινήσω χωρίς βοήθεια». The guide stays in Settings either way."""
    profile = get_profile(session)
    profile.start_choice = body.choice
    profile.start_done = body.choice == "alone"
    session.add(profile)
    session.commit()
    return start_out(profile)


@router.delete("/start", response_model=StartOut)
def ask_again(demo: bool = False, session: Session = Depends(get_session)):
    """Presentation only: show the first-use question again."""
    if not demo_enabled(demo):
        raise HTTPException(403, "Μόνο για την παρουσίαση.")
    profile = get_profile(session)
    profile.start_choice, profile.start_step, profile.start_done = None, 1, False
    session.add(profile)
    session.commit()
    return start_out(profile)


@router.put("/start/step", response_model=StartOut)
def save_step(body: StartStepIn, session: Session = Depends(get_session)):
    profile = get_profile(session)
    profile.start_choice = profile.start_choice or "with_help"
    profile.start_step = body.step
    profile.start_done = body.done
    session.add(profile)
    session.commit()
    return start_out(profile)


@router.get("/practice", response_model=PracticeOut)
def practice_text():
    return PracticeOut(
        title=practice.TITLE, blocks=practice.BLOCKS, glossary=practice.GLOSSARY,
        question=PracticeQuestionOut(prompt=practice.PROMPT, options=practice.OPTIONS, hints=practice.HINTS),
    )


@router.post("/practice/answer", response_model=PracticeAnswerOut)
def practice_answer(body: PracticeAnswerIn):
    """Only for practice: no session, nothing stored, no effect on the support level or progress."""
    correct, message = practice.check(body.option)
    return PracticeAnswerOut(correct=correct, message=message)
