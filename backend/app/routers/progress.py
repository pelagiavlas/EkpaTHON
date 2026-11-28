"""Progress, settings and the optional supporter."""

import json
import secrets
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.learning import service
from app.models import Course, Milestone, Profile, SupporterAccess
from app.routers.courses import get_or_404
from app.schemas import ProgressOut, Settings, SupporterIn, SupporterOut

router = APIRouter(tags=["progress, settings & supporter"])


def build_progress(session: Session, today: date, impersonal: bool = False) -> ProgressOut:
    courses = session.exec(select(Course).order_by(Course.created_at)).all()
    milestones = [] if impersonal else session.exec(select(Milestone).order_by(Milestone.created_at)).all()
    return ProgressOut(
        simulated=service.has_simulated_data(session),
        message=service.overall_message(session, today, impersonal),
        courses=[service.course_progress(session, c, today, impersonal) for c in courses],
        milestones=[service.milestone_out(m) for m in milestones],
    )


@router.get("/progress", response_model=ProgressOut)
def progress(session: Session = Depends(get_session)):
    return build_progress(session, date.today())


@router.post("/milestones/{key}/seen", status_code=204)
def milestone_seen(key: str, session: Session = Depends(get_session)):
    milestone = get_or_404(session, Milestone, key, "Δεν βρέθηκε")
    milestone.seen = True
    session.add(milestone)
    session.commit()


# --- settings ------------------------------------------------------------------

def get_profile(session: Session) -> Profile:
    profile = session.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, settings_json=Settings().model_dump_json())
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


@router.get("/settings", response_model=Settings)
def read_settings(session: Session = Depends(get_session)):
    return Settings(**json.loads(get_profile(session).settings_json))


@router.put("/settings", response_model=Settings)
def save_settings(body: Settings, session: Session = Depends(get_session)):
    profile = get_profile(session)
    profile.settings_json = body.model_dump_json()
    session.add(profile)
    session.commit()
    return body


# --- supporter (only with the student's consent, revocable) ---------------------

def supporter_out(s: SupporterAccess) -> SupporterOut:
    return SupporterOut(id=s.id, name=s.name, token=s.token, created_at=s.created_at, active=s.revoked_at is None)


@router.get("/supporters", response_model=list[SupporterOut])
def list_supporters(session: Session = Depends(get_session)):
    rows = session.exec(select(SupporterAccess).where(SupporterAccess.revoked_at == None))  # noqa: E711
    return [supporter_out(s) for s in rows]


@router.post("/supporters", response_model=SupporterOut, status_code=201)
def add_supporter(body: SupporterIn, session: Session = Depends(get_session)):
    access = SupporterAccess(name=body.name.strip(), token=secrets.token_urlsafe(16))
    session.add(access)
    session.commit()
    session.refresh(access)
    return supporter_out(access)


@router.delete("/supporters/{supporter_id}", status_code=204)
def revoke_supporter(supporter_id: int, session: Session = Depends(get_session)):
    access = get_or_404(session, SupporterAccess, supporter_id, "Δεν βρέθηκε αυτή η πρόσβαση")
    access.revoked_at = datetime.now()
    session.add(access)
    session.commit()


@router.get("/shared/{token}", response_model=ProgressOut)
def shared_progress(token: str, session: Session = Depends(get_session)):
    """What a supporter sees: support level and help per course. Never single answers."""
    access = session.exec(select(SupporterAccess).where(SupporterAccess.token == token)).first()
    if access is None or access.revoked_at is not None:
        raise HTTPException(404, "Αυτή η πρόσβαση δεν ισχύει πια.")
    return build_progress(session, date.today(), impersonal=True)
