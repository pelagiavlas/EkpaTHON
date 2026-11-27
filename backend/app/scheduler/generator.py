"""Schedule generation: best-of-N random valid schedules.

Ported from StudyBuddy's SimulateAnnealing.java + TaskAssignment.java.
Despite the original class name this is not simulated annealing: it builds
N random valid schedules on top of the user's availability and keeps the one
with the best score. That idea is kept and named honestly here.

Changes compared to the Java version:
  - chunks get real start times inside availability windows, with a short
    or long break after each one (the random break pattern is part of the
    search, and scoring penalises long streaks);
  - the next chunk is picked at random weighted by deadline urgency, instead
    of a plain shuffle that could drop near-deadline work;
  - no global state, no "0 means empty" sentinel (task #0 was never placed),
    and a seed for reproducible results.
"""

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .availability import Availability
from .repetition import repetition_days
from .scoring import calculate_score
from .tasks import Chunk, WorkItem, split_into_chunks, validate_chunk_minutes


@dataclass
class Settings:
    chunk_minutes: int = 30
    short_break: int = 5
    long_break: int = 15
    max_chunks_per_day: int = 6
    revision_minutes: int = 15
    candidates: int = 50  # same as StudyBuddy


@dataclass
class Placement:
    chunk: Chunk
    day: date
    start: int  # minutes since midnight

    @property
    def end(self) -> int:
        return self.start + self.chunk.minutes


@dataclass
class Schedule:
    placements: list[Placement] = field(default_factory=list)
    unscheduled: list[Chunk] = field(default_factory=list)
    score: float = 0.0


def build_chunks(
    items: list[WorkItem],
    settings: Settings,
    multipliers: dict[str, float] | None = None,
    done_minutes: dict[int, float] | None = None,
) -> list[Chunk]:
    multipliers = multipliers or {}
    done_minutes = done_minutes or {}
    chunks = []
    for item in items:
        chunks += split_into_chunks(
            item,
            settings.chunk_minutes,
            multipliers.get(item.kind, 1.0),
            done_minutes.get(item.id, 0.0),
        )
    return chunks


def generate(
    items: list[WorkItem],
    availability: Availability,
    start: date,
    settings: Settings | None = None,
    multipliers: dict[str, float] | None = None,
    done_minutes: dict[int, float] | None = None,
    seed: int | None = None,
    start_minute: int = 0,
) -> Schedule:
    """Return the best of `settings.candidates` random schedules.

    `start_minute` stops chunks being placed earlier than "now" on the start day.
    """
    settings = settings or Settings()
    validate_chunk_minutes(settings.chunk_minutes)
    chunks = build_chunks(items, settings, multipliers, done_minutes)
    if not chunks:
        return Schedule(score=calculate_score([], [], settings.long_break))

    rng = random.Random(seed)
    best = None
    for _ in range(settings.candidates):
        candidate = random_candidate(chunks, availability, start, settings, rng, start_minute)
        candidate.score = calculate_score(
            candidate.placements, candidate.unscheduled, settings.long_break
        )
        if best is None or candidate.score > best.score:
            best = candidate
    best.placements.sort(key=lambda p: (p.day, p.start))
    return best


def random_candidate(
    chunks: list[Chunk],
    availability: Availability,
    start: date,
    settings: Settings,
    rng: random.Random,
    start_minute: int = 0,
) -> Schedule:
    remaining = list(chunks)
    placements = []
    pending_revisions: dict[date, list[Chunk]] = defaultdict(list)
    revised = set()  # (course, date): at most one revision per course per day
    started_items = set()
    long_break_chance = rng.uniform(0.0, 0.6)  # each candidate tries a different break pattern

    last_day = max(c.deadline for c in chunks) - timedelta(days=1)
    day = start
    while day <= last_day:
        due_revisions = pending_revisions.pop(day, [])
        placed_today = 0
        not_before = start_minute if day == start else 0
        for window_start, window_end in availability.windows_on(day, not_before):
            cursor = window_start
            while placed_today < settings.max_chunks_per_day:
                fits = lambda c: c.deadline > day and cursor + c.minutes <= window_end
                revisions = [c for c in due_revisions if fits(c)]
                if revisions:
                    # Revisions are short and tied to a date, so they go first (as in StudyBuddy).
                    chunk = revisions[0]
                    due_revisions.remove(chunk)
                else:
                    options = [c for c in remaining if fits(c)]
                    if not options:
                        break
                    weights = [1 / (c.deadline - day).days for c in options]
                    chunk = rng.choices(options, weights=weights)[0]
                    remaining.remove(chunk)

                placements.append(Placement(chunk, day, cursor))
                placed_today += 1
                if chunk.kind == "study" and chunk.item_id not in started_items:
                    started_items.add(chunk.item_id)
                    for rev_day in repetition_days(day, chunk.deadline):
                        if (chunk.course, rev_day) not in revised:
                            revised.add((chunk.course, rev_day))
                            pending_revisions[rev_day].append(
                                Chunk(
                                    chunk.item_id,
                                    chunk.course,
                                    "revision",
                                    settings.revision_minutes,
                                    chunk.deadline,
                                )
                            )
                take_long = rng.random() < long_break_chance
                cursor += chunk.minutes + (settings.long_break if take_long else settings.short_break)
        day += timedelta(days=1)

    return Schedule(placements=placements, unscheduled=remaining)
