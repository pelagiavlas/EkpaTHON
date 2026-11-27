"""Start level for a new chapter, tested with synthetic histories."""

import pytest

from app.config import PredictionConfig
from app.learning.predict import ChapterHistory, score_to_level, suggest_start_level, weighted_score

CFG = PredictionConfig()


def ch(hints: float, wrong: float = 0.0, n: int = 10) -> ChapterHistory:
    return ChapterHistory(questions=n, hints_per_question=hints, wrong_rate=wrong)


def test_first_chapter_keeps_current_level():
    s = suggest_start_level([], current_level=1, cfg=CFG)
    assert s.level == 1 and s.score is None


def test_recent_chapters_count_more():
    improving = weighted_score([ch(3.0), ch(1.0)], CFG)
    worsening = weighted_score([ch(1.0), ch(3.0)], CFG)
    assert improving < worsening
    assert improving == pytest.approx((1.0 + 0.5 * 3.0) / 1.5)


def test_wrong_answers_raise_the_score():
    assert weighted_score([ch(1.0, wrong=0.5)], CFG) == pytest.approx(2.0)


@pytest.mark.parametrize("score, level", [(0.2, 4), (0.74, 4), (0.75, 3), (1.4, 3), (2.0, 2), (2.5, 1), (4.0, 1)])
def test_score_to_level(score, level):
    assert score_to_level(score, CFG) == level


def test_little_help_suggests_more_autonomy_but_one_step_at_a_time():
    s = suggest_start_level([ch(0.2), ch(0.1)], current_level=2, cfg=CFG)
    assert s.level == 3  # would be 4, capped at current + 1


def test_much_help_suggests_more_support():
    s = suggest_start_level([ch(1.0), ch(3.2, wrong=0.4)], current_level=3, cfg=CFG)
    assert s.level == 1


def test_typical_demo_history_suggests_level_3():
    # chapter 1: 3.0, chapter 2: 0.7 -> (0.7 + 0.5 * 3.0) / 1.5 = 1.47 -> level 3
    s = suggest_start_level([ch(2.4, 0.3), ch(0.5, 0.1)], current_level=3, cfg=CFG)
    assert s.level == 3
    assert "0,5" in s.reason


def test_chapters_without_answers_are_ignored():
    assert weighted_score([ch(3.0), ch(0.0, n=0)], CFG) == pytest.approx(3.0)
