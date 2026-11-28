"""Bayesian Knowledge Tracing: formulas, guess effect, what counts as evidence."""

import pytest

from app.config import BKTConfig, load_config
from app.learning import bkt

CFG = BKTConfig()  # p_init 0.3, p_learn 0.15, p_slip 0.1, guess 0.5 / 0.33 / 0.05


def test_config_file_has_the_agreed_parameters():
    cfg = load_config().bkt
    assert (cfg.p_init, cfg.p_learn, cfg.p_slip) == (0.3, 0.15, 0.1)
    assert (cfg.p_guess_two_choices, cfg.p_guess_three_choices, cfg.p_guess_open) == (0.5, 0.33, 0.05)


def test_posterior_after_a_right_answer_by_hand():
    # 0.3*0.9 / (0.3*0.9 + 0.7*0.5) = 0.27 / 0.62
    assert bkt.posterior(0.3, True, guess=0.5, slip=0.1) == pytest.approx(0.27 / 0.62)


def test_posterior_after_a_wrong_answer_by_hand():
    # 0.3*0.1 / (0.3*0.1 + 0.7*0.5) = 0.03 / 0.38
    assert bkt.posterior(0.3, False, guess=0.5, slip=0.1) == pytest.approx(0.03 / 0.38)


def test_learning_step_by_hand():
    assert bkt.learn(0.4, 0.15) == pytest.approx(0.4 + 0.6 * 0.15)


def test_update_is_posterior_then_learning():
    p = bkt.posterior(0.3, True, 0.5, 0.1)
    assert bkt.update(0.3, True, 0.5, CFG) == pytest.approx(p + (1 - p) * 0.15)


def test_guessing_matters_two_choices_vs_open():
    two = bkt.update(0.3, True, bkt.guess_for(2, CFG), CFG)
    three = bkt.update(0.3, True, bkt.guess_for(3, CFG), CFG)
    open_ = bkt.update(0.3, True, bkt.guess_for(0, CFG), CFG)
    assert two < three < open_
    assert round(two, 2) == 0.52 and open_ > 0.9  # one open answer says much more than one lucky click


def test_four_right_two_choice_answers_pass_the_threshold():
    p, path = CFG.p_init, []
    for _ in range(4):
        p = bkt.update(p, True, 0.5, CFG)
        path.append(round(p, 2))
    assert path == [0.52, 0.71, 0.84, 0.92]


def test_wrong_answers_lower_knowledge_but_learning_still_happens():
    after_wrong = bkt.update(0.6, False, 0.5, CFG)
    assert after_wrong < 0.6
    assert after_wrong > bkt.posterior(0.6, False, 0.5, 0.1)  # the learning step


def test_right_with_two_hints_counts_as_not_yet_known():
    assert bkt.evidence(True, 0, help_used=1, self_checked=False, shown_options=2, cfg=CFG).correct is True
    assert bkt.evidence(True, 0, help_used=2, self_checked=False, shown_options=2, cfg=CFG).correct is False
    assert bkt.evidence(True, 1, help_used=0, self_checked=False, shown_options=2, cfg=CFG).correct is False


def test_self_check_is_not_evidence():
    assert bkt.evidence(True, 0, 0, self_checked=True, shown_options=0, cfg=CFG) is None


@pytest.mark.parametrize("p, key, words", [
    (0.3, "learning", "Το μαθαίνεις"), (0.7, "almost", "Σχεδόν το ξέρεις"), (0.95, "known", "Το ξέρεις"),
])
def test_labels_are_words(p, key, words):
    assert bkt.label_key(p, CFG) == key and bkt.LABELS[key] == words
