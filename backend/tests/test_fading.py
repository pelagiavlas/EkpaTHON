"""Fading rules: proposals only, both directions, numbers from config, per level kind."""

from app.config import FadingConfig, load_config
from app.learning.fading import Outcome, easy_text_proposal, is_struggle, is_success, propose

CFG = FadingConfig()
GOOD = Outcome(hints_used=0, correct=True)
ONE_HINT = Outcome(hints_used=1, correct=True)
MANY_HINTS = Outcome(hints_used=3, correct=True)
WRONG = Outcome(hints_used=0, correct=False)
WRONG_FIRST = Outcome(hints_used=1, correct=True, wrong_tries=1)
SEARCHED = Outcome(hints_used=0, correct=True, search=True)  # found it in the original (steps α-γ)
FELL_BACK = Outcome(hints_used=1, correct=True, search=True, fell_back=True)


def test_success_needs_right_first_time_with_at_most_one_hint():
    assert is_success(GOOD, CFG) and is_success(ONE_HINT, CFG)
    assert not is_success(Outcome(2, True), CFG)
    assert not is_success(WRONG_FIRST, CFG)
    assert not is_success(WRONG, CFG)


def test_struggle_is_wrong_or_many_hints():
    assert is_struggle(WRONG, CFG) and is_struggle(MANY_HINTS, CFG) and is_struggle(WRONG_FIRST, CFG)
    assert not is_struggle(Outcome(2, True), CFG)


def test_searching_the_original_is_not_a_struggle():
    assert is_success(SEARCHED, CFG) and not is_struggle(SEARCHED, CFG)


def test_falling_back_to_explanations_is_a_struggle():
    assert is_struggle(FELL_BACK, CFG) and not is_success(FELL_BACK, CFG)


def test_three_successes_in_a_row_propose_less_help():
    assert propose(1, [GOOD, ONE_HINT, GOOD], CFG) == "up"
    assert propose(3, [SEARCHED] * 3, CFG) == "up"


def test_two_successes_are_not_enough():
    assert propose(1, [GOOD, GOOD], CFG) is None


def test_a_break_in_the_streak_resets_it():
    assert propose(1, [GOOD, GOOD, Outcome(2, True), GOOD, GOOD], CFG) is None


def test_two_struggles_in_last_three_propose_more_help():
    assert propose(3, [GOOD, MANY_HINTS, WRONG], CFG) == "down"
    assert propose(3, [FELL_BACK, SEARCHED, FELL_BACK], CFG) == "down"


def test_one_struggle_in_three_is_fine():
    assert propose(3, [GOOD, WRONG, Outcome(2, True)], CFG) is None


def test_no_proposal_beyond_the_edges():
    assert propose(4, [GOOD, GOOD, GOOD], CFG) is None
    assert propose(1, [WRONG, WRONG, WRONG], CFG) is None


def test_easy_text_used_often_at_level_3_offers_one_level_back():
    assert easy_text_proposal(3, [True, False, True], CFG)
    assert not easy_text_proposal(3, [True, False, False], CFG)
    assert not easy_text_proposal(3, [True, True], CFG)  # not enough visits yet
    assert not easy_text_proposal(2, [True, True, True], CFG)  # Easy-to-Read IS the text at levels 1-2


def test_numbers_come_from_config():
    strict = FadingConfig(up_after_successes=5)
    assert propose(1, [GOOD] * 3, strict) is None
    assert propose(1, [GOOD] * 5, strict) == "up"


def test_config_file_loads():
    config = load_config()
    assert config.fading.up_after_successes == 3 and config.fading.easy_window == 3
    assert config.search.max_wrong_picks == 3
    assert config.engine == "bkt"


def test_self_checked_is_never_a_success():
    close = Outcome(hints_used=0, correct=True, self_checked=True)
    not_yet = Outcome(hints_used=0, correct=False, self_checked=True)
    assert not is_success(close, CFG) and not is_struggle(close, CFG)
    assert is_struggle(not_yet, CFG)
    assert propose(1, [close] * 3, CFG) is None
