"""Prediction model v1: a personal time multiplier per task kind.

multiplier = how much longer (or shorter) this student really needs compared
to the estimate. Starts at 1.0 and after every completed task moves towards
actual / estimate with an exponential moving average, so recent tasks count
more and a single odd day does not swing it too much.
"""

ALPHA = 0.3
MIN_MULTIPLIER = 0.5
MAX_MULTIPLIER = 3.0


def update_multiplier(current: float, actual_minutes: float, estimated_minutes: float, alpha: float = ALPHA) -> float:
    if actual_minutes <= 0 or estimated_minutes <= 0:
        return current
    ratio = actual_minutes / estimated_minutes
    updated = (1 - alpha) * current + alpha * ratio
    return min(MAX_MULTIPLIER, max(MIN_MULTIPLIER, updated))
