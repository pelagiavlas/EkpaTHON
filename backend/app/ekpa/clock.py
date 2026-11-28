"""The app clock. In demo mode "today" is set so that there is always a class at 11:00.

Demo mode = DEMO_MODE=true in backend/.env, or ?demo=1 sent by the app.
- date: DEMO_DATE (YYYY-MM-DD) if set, otherwise the nearest day (from today) with a class at 11:00;
- time: the time chosen in the app ("before" / "after" the class), else DEMO_TIME, else 09:30.
"""

import os
from datetime import date, datetime, time, timedelta

from app.ekpa.schedule import Slot, parse_time

DEMO_CLASS_TIME = time(11, 0)
DEMO_TIMES = {"before": "09:30", "after": "13:00"}


def demo_enabled(requested: bool) -> bool:
    return requested or os.getenv("DEMO_MODE", "false").strip().lower() in ("1", "true", "yes")


def demo_day(slots: list[Slot], today: date) -> date:
    if os.getenv("DEMO_DATE"):
        return date.fromisoformat(os.environ["DEMO_DATE"])
    for offset in range(7):
        day = today + timedelta(days=offset)
        if any(s.weekday == day.weekday() and s.start == DEMO_CLASS_TIME for s in slots):
            return day
    return today


def current_time(demo: bool, slots: list[Slot], moment: str | None = None, real_now: datetime | None = None) -> datetime:
    real_now = real_now or datetime.now()
    if not demo:
        return real_now
    clock = DEMO_TIMES.get(moment or "", None) or os.getenv("DEMO_TIME") or DEMO_TIMES["before"]
    return datetime.combine(demo_day(slots, real_now.date()), parse_time(clock))
