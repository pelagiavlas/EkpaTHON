"""Schedule scoring, ported from StudyBuddy's Scoring.java and extended.

Kept from StudyBuddy (start at 5.0, subtract penalties):
  - same course studied too much on the same day      (-0.2 per extra chunk)
  - same course studied on consecutive days           (-0.1 per day pair)
New:
  - more than 3 chunks in a row without a long break  (-0.3 per extra chunk)
  - chunks that could not be placed before deadline   (-1.0 each)
  - chunks crammed into the last day before deadline  (-0.05 each)
"""

from collections import Counter, defaultdict
from datetime import timedelta

START_SCORE = 5.0
SAME_COURSE_DAILY_LIMIT = 3
SAME_DAY_PENALTY = 0.2
CONSECUTIVE_DAYS_PENALTY = 0.1
MAX_STREAK = 3
STREAK_PENALTY = 0.3
UNSCHEDULED_PENALTY = 1.0
CRUNCH_PENALTY = 0.05


def same_day_penalty(placements) -> float:
    counts = Counter((p.day, p.chunk.course) for p in placements if p.chunk.kind == "study")
    extra = sum(max(0, n - SAME_COURSE_DAILY_LIMIT) for n in counts.values())
    return SAME_DAY_PENALTY * extra


def consecutive_days_penalty(placements) -> float:
    days_by_course = defaultdict(set)
    for p in placements:
        if p.chunk.kind == "study":
            days_by_course[p.chunk.course].add(p.day)
    pairs = sum(
        1 for days in days_by_course.values() for d in days if d + timedelta(days=1) in days
    )
    return CONSECUTIVE_DAYS_PENALTY * pairs


def longest_streaks(placements, long_break: int) -> list[int]:
    """Lengths of runs of chunks separated by less than `long_break` minutes."""
    streaks = []
    by_day = defaultdict(list)
    for p in placements:
        by_day[p.day].append(p)
    for day_placements in by_day.values():
        day_placements.sort(key=lambda p: p.start)
        streak = 1
        for prev, cur in zip(day_placements, day_placements[1:]):
            if cur.start - prev.end < long_break:
                streak += 1
            else:
                streaks.append(streak)
                streak = 1
        streaks.append(streak)
    return streaks


def streak_penalty(placements, long_break: int) -> float:
    extra = sum(max(0, s - MAX_STREAK) for s in longest_streaks(placements, long_break))
    return STREAK_PENALTY * extra


def crunch_penalty(placements) -> float:
    last_day = timedelta(days=1)
    crammed = sum(
        1 for p in placements if p.chunk.kind != "revision" and p.chunk.deadline - p.day == last_day
    )
    return CRUNCH_PENALTY * crammed


def calculate_score(placements, unscheduled, long_break: int) -> float:
    return (
        START_SCORE
        - same_day_penalty(placements)
        - consecutive_days_penalty(placements)
        - streak_penalty(placements, long_break)
        - crunch_penalty(placements)
        - UNSCHEDULED_PENALTY * len(unscheduled)
    )
