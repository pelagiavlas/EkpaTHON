"""Work items and the chunks they are split into.

StudyBuddy's Task.java had a fixed length (2 hours for study/assignment,
20 minutes for revision). Here an item's total time is
base estimate x personal multiplier (from the prediction model), and it is
split into chunks of a configurable length (15-45 minutes).
"""

import math
from dataclasses import dataclass
from datetime import date

KINDS = ("study", "revision", "assignment")
MIN_CHUNK = 15
MAX_CHUNK = 45


@dataclass
class WorkItem:
    id: int
    course: str
    kind: str  # "study" or "assignment"; revisions are generated
    base_minutes: float
    deadline: date  # chunks must be placed strictly before this date
    title: str = ""


@dataclass(eq=False)  # identity equality: two identical chunks are still different chunks
class Chunk:
    item_id: int
    course: str
    kind: str
    minutes: int
    deadline: date


def validate_chunk_minutes(chunk_minutes: int) -> None:
    if not MIN_CHUNK <= chunk_minutes <= MAX_CHUNK:
        raise ValueError(f"chunk length must be between {MIN_CHUNK} and {MAX_CHUNK} minutes")


def split_into_chunks(
    item: WorkItem, chunk_minutes: int, multiplier: float = 1.0, done_minutes: float = 0.0
) -> list[Chunk]:
    validate_chunk_minutes(chunk_minutes)
    remaining = item.base_minutes * multiplier - done_minutes
    if remaining <= 0:
        return []
    # Round to the nearest whole chunk, but never less than one.
    count = max(1, math.floor(remaining / chunk_minutes + 0.5))
    return [
        Chunk(item.id, item.course, item.kind, chunk_minutes, item.deadline) for _ in range(count)
    ]
