"""Progress, settings and the optional supporter."""

import json
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.ekpa.clock import demo_enabled
from app.learning import service
from app.models import Course, Milestone, Profile, SupporterAccess
from app.routers.courses import get_or_404
from app.schemas import ProgressOut, ScopeIn, Settings, SupporterCheckOut, SupporterIn, SupporterOut

router = APIRouter(tags=["progress, settings & supporter"])

ASK_LESS_EVERY = timedelta(weeks=4)


def build_progress(session: Session, today: date, impersonal: bool = False, scope: str | None = None) -> ProgressOut:
    """scope="course" (the supporter's smaller view): only the message and the weeks of each course."""
    courses = session.exec(select(Course).order_by(Course.created_at)).all()
    milestones = [] if impersonal else session.exec(select(Milestone).order_by(Milestone.created_at)).all()
    progress = [service.course_progress(session, c, today, impersonal) for c in courses]
    if scope == "course":
        progress = [c.model_copy(update={"chapters": [], "days": [], "level_history": [], "concepts": []}) for c in progress]
    return ProgressOut(
        simulated=service.has_simulated_data(session),
        message=service.overall_message(session, today, impersonal),
        courses=progress,
        milestones=[service.milestone_out(m) for m in milestones],
        scope=scope,
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
    return SupporterOut(id=s.id, name=s.name, token=s.token, created_at=s.created_at, active=s.revoked_at is None,
                        scope=s.scope)


def supporters_to_ask(session: Session, now: datetime) -> list[SupporterCheckOut]:
    """Help fades, and so does the supporter's view: every 4 weeks «...να βλέπει λιγότερα;»"""
    rows = session.exec(select(SupporterAccess).where(SupporterAccess.revoked_at == None))  # noqa: E711
    return [SupporterCheckOut(id=s.id, name=s.name, scope=s.scope) for s in rows
            if now >= (s.ask_less_at or s.created_at + ASK_LESS_EVERY)]


@router.get("/supporters", response_model=list[SupporterOut])
def list_supporters(session: Session = Depends(get_session)):
    rows = session.exec(select(SupporterAccess).where(SupporterAccess.revoked_at == None))  # noqa: E711
    return [supporter_out(s) for s in rows]


@router.post("/supporters", response_model=SupporterOut, status_code=201)
def add_supporter(body: SupporterIn, session: Session = Depends(get_session)):
    access = SupporterAccess(name=body.name.strip(), token=secrets.token_urlsafe(16), scope=body.scope)
    session.add(access)
    session.commit()
    session.refresh(access)
    return supporter_out(access)


@router.delete("/supporters/{supporter_id}", status_code=204)
def revoke_supporter(supporter_id: int, session: Session = Depends(get_session)):
    """One tap: the link stops working at once."""
    access = get_or_404(session, SupporterAccess, supporter_id, "Δεν βρέθηκε αυτή η πρόσβαση")
    access.revoked_at = datetime.now()
    session.add(access)
    session.commit()


def active_access(session: Session, supporter_id: int) -> SupporterAccess:
    access = get_or_404(session, SupporterAccess, supporter_id, "Δεν βρέθηκε αυτή η πρόσβαση")
    if access.revoked_at is not None:
        raise HTTPException(404, "Αυτή η πρόσβαση έχει σταματήσει.")
    return access


@router.put("/supporters/{supporter_id}/scope", response_model=SupporterOut)
def change_scope(supporter_id: int, body: ScopeIn, session: Session = Depends(get_session)):
    access = active_access(session, supporter_id)
    access.scope = body.scope
    access.ask_less_at = datetime.now() + ASK_LESS_EVERY
    session.add(access)
    session.commit()
    return supporter_out(access)


@router.post("/supporters/{supporter_id}/keep", response_model=SupporterOut)
def keep_scope(supporter_id: int, session: Session = Depends(get_session)):
    """«Όχι, άφησέ το»: nothing changes, and we ask again in 4 weeks."""
    access = active_access(session, supporter_id)
    access.ask_less_at = datetime.now() + ASK_LESS_EVERY
    session.add(access)
    session.commit()
    return supporter_out(access)


@router.post("/supporters/{supporter_id}/ask-now", response_model=SupporterOut)
def ask_now(supporter_id: int, demo: bool = False, session: Session = Depends(get_session)):
    """Presentation only: ask «...να βλέπει λιγότερα;» now instead of in 4 weeks."""
    if not demo_enabled(demo):
        raise HTTPException(403, "Μόνο για την παρουσίαση.")
    access = active_access(session, supporter_id)
    access.ask_less_at = datetime.now()
    session.add(access)
    session.commit()
    return supporter_out(access)


@router.get("/shared/{token}", response_model=ProgressOut)
def shared_progress(token: str, session: Session = Depends(get_session)):
    """What a supporter sees, as much as the student chose (scope). Never single answers."""
    access = session.exec(select(SupporterAccess).where(SupporterAccess.token == token)).first()
    if access is None or access.revoked_at is not None:
        raise HTTPException(404, "Αυτή η πρόσβαση δεν ισχύει πια.")
    return build_progress(session, date.today(), impersonal=True, scope=access.scope)
