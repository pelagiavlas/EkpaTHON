import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, delete, select

from app.db import get_session
from app.models import AvailabilityWindow, BlockedDate, Profile
from app.schemas import AvailabilityIn, ProfileOut, ProfileUpdate

router = APIRouter(tags=["profile"])


def get_profile(session: Session) -> Profile:
    profile = session.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def profile_out(profile: Profile) -> ProfileOut:
    data = profile.model_dump(exclude={"id", "ui_prefs"})
    return ProfileOut(**data, ui_prefs=json.loads(profile.ui_prefs))


@router.get("/profile", response_model=ProfileOut)
def read_profile(session: Session = Depends(get_session)):
    return profile_out(get_profile(session))


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, session: Session = Depends(get_session)):
    profile = get_profile(session)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(profile, key, json.dumps(value) if key == "ui_prefs" else value)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile_out(profile)


@router.get("/availability", response_model=AvailabilityIn)
def read_availability(session: Session = Depends(get_session)):
    windows = session.exec(select(AvailabilityWindow).order_by(AvailabilityWindow.weekday)).all()
    blocked = session.exec(select(BlockedDate).order_by(BlockedDate.day)).all()
    return AvailabilityIn(
        windows=[w.model_dump(exclude={"id"}) for w in windows],
        blocked_dates=[b.day for b in blocked],
    )


@router.put("/availability", response_model=AvailabilityIn)
def replace_availability(body: AvailabilityIn, session: Session = Depends(get_session)):
    session.exec(delete(AvailabilityWindow))
    session.exec(delete(BlockedDate))
    for w in body.windows:
        session.add(AvailabilityWindow(**w.model_dump()))
    for day in set(body.blocked_dates):
        session.add(BlockedDate(day=day))
    session.commit()
    return read_availability(session)
