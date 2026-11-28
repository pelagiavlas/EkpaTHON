"""Bayesian Knowledge Tracing: how likely is it that the student KNOWS a concept?

Plain Python, standard BKT (Corbett & Anderson, 1995). For each concept we keep
P(L) = probability the concept is known. After every observed answer:

  correct:  P(L|ok)    = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
  wrong:    P(L|wrong) = P(L)S     / [P(L)S     + (1-P(L))(1-G)]
  then learning:  P(L)' = P(L|obs) + (1 - P(L|obs)) T

S = slip (knows it but answers wrong), G = guess (does not know it but answers right),
T = learn (learns it during this attempt). G depends on the question the student saw:
two choices are easy to guess, an open question is not.

The student never sees these numbers, only words ("Το μαθαίνεις", ...).
"""

from dataclasses import dataclass

from app.config import BKTConfig


def posterior(p_known: float, correct: bool, guess: float, slip: float) -> float:
    if correct:
        known, unknown = p_known * (1 - slip), (1 - p_known) * guess
    else:
        known, unknown = p_known * slip, (1 - p_known) * (1 - guess)
    total = known + unknown
    return known / total if total else p_known


def learn(p_known: float, p_learn: float) -> float:
    return p_known + (1 - p_known) * p_learn


def update(p_known: float, correct: bool, guess: float, cfg: BKTConfig) -> float:
    return learn(posterior(p_known, correct, guess, cfg.p_slip), cfg.p_learn)


def guess_for(shown_options: int, cfg: BKTConfig) -> float:
    """shown_options: 2 or 3 for choice questions, 0 for an open question."""
    if shown_options == 2:
        return cfg.p_guess_two_choices
    if shown_options == 3:
        return cfg.p_guess_three_choices
    return cfg.p_guess_open


@dataclass
class Evidence:
    """What one finished attempt tells BKT. None = it tells nothing (e.g. self-check)."""

    correct: bool
    guess: float


def evidence(correct: bool, wrong_tries: int, help_used: int, self_checked: bool,
             shown_options: int, cfg: BKTConfig) -> Evidence | None:
    """Only a right answer, right the first time, with at most `known_max_help` hints counts
    as 'knows it'. A right answer after more help counts as 'not yet' for knowledge
    (the learning step still applies). Self-checked answers are not evidence."""
    if self_checked:
        return None
    known = correct and wrong_tries == 0 and help_used <= cfg.known_max_help
    return Evidence(correct=known, guess=guess_for(shown_options, cfg))


LABELS = {
    "learning": "Το μαθαίνεις",
    "almost": "Σχεδόν το ξέρεις",
    "known": "Το ξέρεις",
}


def label_key(p_known: float, cfg: BKTConfig) -> str:
    if p_known >= cfg.label_known:
        return "known"
    if p_known >= cfg.label_almost:
        return "almost"
    return "learning"
