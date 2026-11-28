"""Timetable and syllabus logic (plain functions, no database).

- next_class: the next class from "now", and whether we are before, during or after it.
- ended_classes: classes that already ended (for "Σήμερα κάνατε την ενότητα Χ;").
- predict_unit: which unit a class is about. The student's own confirmations win over
  the plan: if teaching is behind schedule, the prediction follows what really happened.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass
class Slot:
    course_id: int
    weekday: int  # 0 = Monday
    start: time
    end: time
    room: str


@dataclass
class ClassTime:
    course_id: int
    day: date
    start: time
    end: time
    room: str

    def starts(self) -> datetime:
        return datetime.combine(self.day, self.start)

    def ends(self) -> datetime:
        return datetime.combine(self.day, self.end)


@dataclass
class Unit:
    id: int
    position: int
    title: str
    week: int


def parse_time(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def classes_on(slots: list[Slot], day: date) -> list[ClassTime]:
    return sorted(
        (ClassTime(s.course_id, day, s.start, s.end, s.room) for s in slots if s.weekday == day.weekday()),
        key=lambda c: c.start,
    )


def next_class(slots: list[Slot], now: datetime, horizon_days: int = 14) -> tuple[ClassTime, str] | None:
    """The next class that has not ended yet. Phase: "before" (later today), "during", or "later" (another day)."""
    for offset in range(horizon_days):
        day = now.date() + timedelta(days=offset)
        for c in classes_on(slots, day):
            if c.ends() <= now:
                continue
            if offset > 0:
                return c, "later"
            return c, "during" if c.starts() <= now else "before"
    return None


def ended_classes(slots: list[Slot], now: datetime, days_back: int = 7) -> list[ClassTime]:
    """Classes that ended in the last `days_back` days, most recent first."""
    ended = []
    for offset in range(days_back + 1):
        day = now.date() - timedelta(days=offset)
        ended += [c for c in classes_on(slots, day) if c.ends() <= now]
    return sorted(ended, key=lambda c: c.ends(), reverse=True)


def week_of(day: date, semester_start: date) -> int:
    return (day - semester_start).days // 7 + 1


def predict_unit(units: list[Unit], confirmed_positions: list[int], day: date, semester_start: date) -> Unit | None:
    """The unit a class on `day` is probably about."""
    ordered = sorted(units, key=lambda u: u.position)
    if not ordered:
        return None
    if confirmed_positions:
        last = max(confirmed_positions)
        return next((u for u in ordered if u.position > last), None)
    week = week_of(day, semester_start)
    planned = [u for u in ordered if u.week <= week]
    return next((u for u in ordered if u.week == week), planned[-1] if planned else ordered[0])


def teaching_position(units: list[Unit], confirmed_positions: list[int], today: date, semester_start: date) -> Unit | None:
    """Where teaching is now: the last confirmed unit, otherwise the plan for this week."""
    ordered = sorted(units, key=lambda u: u.position)
    if confirmed_positions:
        last = max(confirmed_positions)
        return next((u for u in ordered if u.position == last), None)
    week = week_of(today, semester_start)
    planned = [u for u in ordered if u.week <= week]
    return planned[-1] if planned else None
