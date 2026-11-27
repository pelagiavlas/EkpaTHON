"""Fading rules: proposals only, both directions, numbers from config."""

from app.config import FadingConfig
from app.learning.fading import Outcome, is_struggle, is_success, propose

CFG = FadingConfig()
GOOD = Outcome(hints_used=0, correct=True)
ONE_HINT = Outcome(hints_used=1, correct=True)
MANY_HINTS = Outcome(hints_used=3, correct=True)
WRONG = Outcome(hints_used=0, correct=False)
WRONG_FIRST = Outcome(hints_used=1, correct=True, wrong_tries=1)


def test_success_needs_right_first_time_with_at_most_one_hint():
    assert is_success(GOOD, CFG) and is_success(ONE_HINT, CFG)
    assert not is_success(Outcome(2, True), CFG)
    assert not is_success(WRONG_FIRST, CFG)
    assert not is_success(WRONG, CFG)


def test_struggle_is_wrong_or_many_hints():
    assert is_struggle(WRONG, CFG) and is_struggle(MANY_HINTS, CFG) and is_struggle(WRONG_FIRST, CFG)
    assert not is_struggle(Outcome(2, True), CFG)


def test_three_successes_in_a_row_propose_less_help():
    assert propose(1, [GOOD, ONE_HINT, GOOD], CFG) == "up"


def test_two_successes_are_not_enough():
    assert propose(1, [GOOD, GOOD], CFG) is None


def test_a_break_in_the_streak_resets_it():
    assert propose(1, [GOOD, GOOD, Outcome(2, True), GOOD, GOOD], CFG) is None


def test_two_struggles_in_last_three_propose_more_help():
    assert propose(3, [GOOD, MANY_HINTS, WRONG], CFG) == "down"
    assert propose(3, [WRONG, GOOD, MANY_HINTS], CFG) == "down"


def test_one_struggle_in_three_is_fine():
    assert propose(3, [GOOD, WRONG, Outcome(2, True)], CFG) is None


def test_no_proposal_beyond_the_edges():
    assert propose(4, [GOOD, GOOD, GOOD], CFG) is None
    assert propose(1, [WRONG, WRONG, WRONG], CFG) is None


def test_numbers_come_from_config():
    strict = FadingConfig(up_after_successes=5)
    assert propose(1, [GOOD] * 3, strict) is None
    assert propose(1, [GOOD] * 5, strict) == "up"


def test_config_file_loads():
    from app.config import load_config

    fading, prediction = load_config()
    assert fading.up_after_successes == 3
    assert prediction.thresholds == (0.75, 1.5, 2.5)
