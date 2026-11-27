"""Fading support: help is reduced step by step as the student manages alone.

Support level per task kind, from 3 (most help) to 0 (least):
  3 - steps always visible, reminder before each chunk, Easy-to-Read on by default
  2 - steps always visible
  1 - steps hidden behind "Δείξε τα βήματα"
  0 - only the title
Three chunks in a row without "Χρειάζομαι βοήθεια" lower the level by one;
asking for help raises it by one straight away. Help is never taken away for good.
"""

MAX_LEVEL = 3
STREAK_TO_FADE = 3


def next_support(level: int, streak: int, asked_help: bool) -> tuple[int, int]:
    """Return (new_level, new_streak) after a finished chunk."""
    if asked_help:
        return min(MAX_LEVEL, level + 1), 0
    streak += 1
    if streak >= STREAK_TO_FADE and level > 0:
        return level - 1, 0
    return level, streak


def help_reduction(weekly_rates: list[float]) -> float | None:
    """Percent drop in help requests per chunk, first week vs last week."""
    if len(weekly_rates) < 2 or weekly_rates[0] == 0:
        return None
    return round(100 * (weekly_rates[0] - weekly_rates[-1]) / weekly_rates[0], 1)
