"""Base time estimate for a work item, before the personal multiplier.

Ported from StudyBuddy's CalculativeAlgorithm.java:
    hours = pages * difficulty / (pagesPerMin * 60)
The reading speed (minutes per page) is now a per-student profile setting
instead of one value for everyone.
"""

DIFFICULTY_FACTOR = {1: 1.0, 2: 1.5, 3: 2.0}


def estimate_minutes(
    kind: str,
    pages: int | None = None,
    difficulty: int = 2,
    minutes_per_page: float = 3.0,
    estimated_minutes: float | None = None,
) -> float:
    """An explicit estimate wins; otherwise study items are estimated from pages."""
    if estimated_minutes is not None:
        if estimated_minutes <= 0:
            raise ValueError("estimated minutes must be positive")
        return float(estimated_minutes)
    if kind == "study" and pages:
        if difficulty not in DIFFICULTY_FACTOR:
            raise ValueError("difficulty must be 1, 2 or 3")
        return pages * minutes_per_page * DIFFICULTY_FACTOR[difficulty]
    raise ValueError("give either estimated minutes or pages (for study items)")
