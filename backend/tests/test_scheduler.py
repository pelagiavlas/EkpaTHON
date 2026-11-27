from datetime import date, timedelta

import pytest

from app.scheduler import (
    Availability,
    Chunk,
    Placement,
    Settings,
    Window,
    WorkItem,
    estimate_minutes,
    generate,
    parse_hhmm,
    split_into_chunks,
)
from app.scheduler.repetition import repetition_days
from app.scheduler.scoring import (
    calculate_score,
    consecutive_days_penalty,
    same_day_penalty,
    streak_penalty,
)

MONDAY = date(2026, 11, 30)


def every_evening(start="17:00", end="20:00"):
    return Availability([Window(d, parse_hhmm(start), parse_hhmm(end)) for d in range(7)])


def item(id=1, course="Μαθηματικά", kind="study", minutes=120, days=7):
    return WorkItem(id, course, kind, minutes, MONDAY + timedelta(days=days))


# --- availability ---------------------------------------------------------


def test_windows_only_on_their_weekday():
    av = Availability([Window(0, 600, 720)])
    assert av.windows_on(MONDAY) == [(600, 720)]
    assert av.windows_on(MONDAY + timedelta(days=1)) == []


def test_blocked_date_has_no_windows():
    av = Availability([Window(0, 600, 720)], blocked={MONDAY})
    assert av.windows_on(MONDAY) == []


def test_windows_clipped_to_now():
    av = Availability([Window(0, 600, 720)])
    assert av.windows_on(MONDAY, not_before=650) == [(650, 720)]
    assert av.windows_on(MONDAY, not_before=800) == []


def test_invalid_window_rejected():
    with pytest.raises(ValueError):
        Window(0, 700, 600)


# --- estimates and chunks -------------------------------------------------


def test_estimate_from_pages_uses_personal_reading_speed():
    assert estimate_minutes("study", pages=10, difficulty=1, minutes_per_page=3) == 30
    assert estimate_minutes("study", pages=10, difficulty=3, minutes_per_page=3) == 60


def test_explicit_estimate_wins():
    assert estimate_minutes("assignment", estimated_minutes=90) == 90


def test_estimate_needs_input():
    with pytest.raises(ValueError):
        estimate_minutes("assignment")


def test_split_uses_multiplier():
    assert len(split_into_chunks(item(minutes=120), 30)) == 4
    assert len(split_into_chunks(item(minutes=120), 30, multiplier=1.5)) == 6


def test_split_subtracts_done_work_and_never_returns_zero_for_open_work():
    assert len(split_into_chunks(item(minutes=120), 30, done_minutes=90)) == 1
    assert len(split_into_chunks(item(minutes=10), 30)) == 1
    assert split_into_chunks(item(minutes=120), 30, done_minutes=120) == []


@pytest.mark.parametrize("bad", [10, 60])
def test_chunk_length_limits(bad):
    with pytest.raises(ValueError):
        split_into_chunks(item(), bad)


# --- spaced repetition (same rule as StudyBuddy) --------------------------


def test_repetition_days_fixed_then_doubling():
    days = repetition_days(MONDAY, MONDAY + timedelta(days=200))
    offsets = [(d - MONDAY).days for d in days]
    assert offsets == [1, 7, 16, 35, 70, 140]


def test_repetition_days_stop_before_deadline():
    days = repetition_days(MONDAY, MONDAY + timedelta(days=7))
    assert [(d - MONDAY).days for d in days] == [1]


# --- scoring --------------------------------------------------------------


def chunk(course="Μαθηματικά", kind="study", minutes=30, deadline_days=10):
    return Chunk(1, course, kind, minutes, MONDAY + timedelta(days=deadline_days))


def test_streak_penalty_only_above_three_chunks():
    back_to_back = [Placement(chunk(), MONDAY, 600 + i * 35) for i in range(4)]
    assert streak_penalty(back_to_back[:3], long_break=15) == 0
    assert streak_penalty(back_to_back, long_break=15) == pytest.approx(0.3)


def test_long_break_resets_streak():
    starts = [600, 635, 670, 720, 755]  # long break before 720
    placements = [Placement(chunk(), MONDAY, s) for s in starts]
    assert streak_penalty(placements, long_break=15) == 0


def test_same_course_same_day_penalty():
    placements = [Placement(chunk(), MONDAY, 600 + i * 60) for i in range(5)]
    assert same_day_penalty(placements) == pytest.approx(0.4)


def test_consecutive_days_penalty_only_for_study():
    study = [Placement(chunk(), MONDAY + timedelta(days=i), 600) for i in range(3)]
    assert consecutive_days_penalty(study) == pytest.approx(0.2)
    revision = [Placement(chunk(kind="revision"), MONDAY + timedelta(days=i), 600) for i in range(3)]
    assert consecutive_days_penalty(revision) == 0


def test_unscheduled_chunks_cost_the_most():
    assert calculate_score([], [chunk()], 15) == pytest.approx(4.0)


# --- generator ------------------------------------------------------------


def assert_valid(schedule, availability, settings):
    by_day = {}
    for p in schedule.placements:
        assert p.day < p.chunk.deadline
        assert any(s <= p.start and p.end <= e for s, e in availability.windows_on(p.day))
        by_day.setdefault(p.day, []).append(p)
    for day_placements in by_day.values():
        assert len(day_placements) <= settings.max_chunks_per_day
        day_placements.sort(key=lambda p: p.start)
        for prev, cur in zip(day_placements, day_placements[1:]):
            assert cur.start - prev.end >= settings.short_break


def test_generated_schedule_is_valid():
    av = every_evening()
    settings = Settings()
    items = [item(1, "Μαθηματικά", minutes=300), item(2, "Φυσική", "assignment", 180, days=4)]
    schedule = generate(items, av, MONDAY, settings, seed=1)
    assert schedule.unscheduled == []
    assert_valid(schedule, av, settings)


def test_first_item_is_scheduled():
    # StudyBuddy used 0 as "empty slot", so the task at index 0 was never placed.
    schedule = generate([item(0, minutes=30)], every_evening(), MONDAY, seed=1)
    assert [p.chunk.item_id for p in schedule.placements if p.chunk.kind == "study"] == [0]


def test_multiplier_changes_planned_time():
    items = [item(minutes=120)]
    normal = generate(items, every_evening(), MONDAY, seed=1)
    slower = generate(items, every_evening(), MONDAY, multipliers={"study": 1.5}, seed=1)
    study = lambda s: sum(p.chunk.minutes for p in s.placements if p.chunk.kind == "study")
    assert study(normal) == 120
    assert study(slower) == 180


def test_chunk_length_is_configurable():
    schedule = generate([item(minutes=90)], every_evening(), MONDAY, Settings(chunk_minutes=45), seed=1)
    assert {p.chunk.minutes for p in schedule.placements if p.chunk.kind == "study"} == {45}


def test_too_little_time_reports_unscheduled_chunks():
    av = every_evening("17:00", "17:30")  # one chunk per day
    schedule = generate([item(kind="assignment", minutes=300, days=3)], av, MONDAY, seed=1)
    assert len(schedule.unscheduled) == 10 - 3


def test_revisions_added_after_first_study_session():
    schedule = generate([item(minutes=30, days=10)], every_evening(), MONDAY, seed=1)
    kinds = [p.chunk.kind for p in schedule.placements]
    assert kinds.count("study") == 1
    assert kinds.count("revision") == 2  # day +1 and day +7


def test_start_minute_keeps_today_in_the_future():
    schedule = generate([item(minutes=60)], every_evening(), MONDAY, seed=1, start_minute=parse_hhmm("19:00"))
    today = [p for p in schedule.placements if p.day == MONDAY]
    assert all(p.start >= parse_hhmm("19:00") for p in today)


def test_same_seed_same_schedule():
    items = [item(1, minutes=200), item(2, "Φυσική", minutes=150)]
    a = generate(items, every_evening(), MONDAY, seed=42)
    b = generate(items, every_evening(), MONDAY, seed=42)
    assert [(p.day, p.start, p.chunk.course) for p in a.placements] == [
        (p.day, p.start, p.chunk.course) for p in b.placements
    ]


def test_best_of_many_is_at_least_as_good_as_one():
    items = [item(1, minutes=400), item(2, "Φυσική", minutes=300), item(3, "Χημεία", "assignment", 200)]
    one = generate(items, every_evening(), MONDAY, Settings(candidates=1), seed=3)
    many = generate(items, every_evening(), MONDAY, Settings(candidates=50), seed=3)
    assert many.score >= one.score


def test_no_items_gives_empty_schedule():
    schedule = generate([], every_evening(), MONDAY)
    assert schedule.placements == [] and schedule.unscheduled == []
