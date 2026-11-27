"""Spaced-repetition dates, ported unchanged from StudyBuddy's Repetition.java.

After the first study session of an item, revisions follow after 1, 7, 16
and 35 days, then the interval keeps doubling (70, 140, ...), as long as the
revision falls before the deadline.
"""

from datetime import date, timedelta

FIXED_INTERVALS = (1, 7, 16, 35)


def repetition_days(study_day: date, deadline: date) -> list[date]:
    days = [study_day + timedelta(days=d) for d in FIXED_INTERVALS]
    days = [d for d in days if d < deadline]
    interval = FIXED_INTERVALS[-1]
    while True:
        interval *= 2
        day = study_day + timedelta(days=interval)
        if day >= deadline:
            break
        days.append(day)
    return days
