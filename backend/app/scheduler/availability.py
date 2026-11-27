"""User availability as time windows per weekday.

Ported from StudyBuddy's Availability.java, which stored "hours per weekday"
plus a list of unavailable dates. Here each weekday has explicit windows
(e.g. Monday 17:00-20:00) so every chunk gets a real start time.
"""

from dataclasses import dataclass, field
from datetime import date


def parse_hhmm(value: str) -> int:
    """'17:30' -> minutes since midnight."""
    hours, minutes = value.split(":")
    total = int(hours) * 60 + int(minutes)
    if not 0 <= total <= 24 * 60:
        raise ValueError(f"Invalid time: {value}")
    return total


def fmt_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass(frozen=True)
class Window:
    weekday: int  # 0 = Monday ... 6 = Sunday (Python convention; Java used 1..7)
    start: int  # minutes since midnight
    end: int

    def __post_init__(self):
        if not 0 <= self.weekday <= 6:
            raise ValueError("weekday must be between 0 and 6")
        if self.end <= self.start:
            raise ValueError("window end must be after start")


@dataclass
class Availability:
    windows: list[Window]
    blocked: set[date] = field(default_factory=set)

    def windows_on(self, day: date, not_before: int = 0) -> list[tuple[int, int]]:
        """Sorted (start, end) windows for a date, clipped to start at `not_before`."""
        if day in self.blocked:
            return []
        result = []
        for w in self.windows:
            if w.weekday != day.weekday():
                continue
            start = max(w.start, not_before)
            if start < w.end:
                result.append((start, w.end))
        return sorted(result)

    def minutes_on(self, day: date) -> int:
        return sum(end - start for start, end in self.windows_on(day))
