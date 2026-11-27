"""Support levels and fading rules.

Four support levels per course (never a label for the person):
  1 Πλήρης βοήθεια       - Easy-to-Read with pictures and sound, questions with 2 choices
  2 Καθοδηγούμενη        - Easy-to-Read, questions with 3 choices, hints on request
  3 Λιγότερη βοήθεια     - fewer pictures, simple open questions, strategy questions
  4 Αυτονομία            - the student picks what they need, help only on request

The rules only PROPOSE a change. The student decides.
"""

from dataclasses import dataclass

from app.config import FadingConfig

MIN_LEVEL = 1
MAX_LEVEL = 4
LEVEL_NAMES = {
    1: "Πλήρης βοήθεια",
    2: "Καθοδηγούμενη βοήθεια",
    3: "Λιγότερη βοήθεια",
    4: "Αυτονομία",
}


@dataclass
class Outcome:
    hints_used: int
    correct: bool
    wrong_tries: int = 0


def is_success(o: Outcome, cfg: FadingConfig) -> bool:
    return o.correct and o.wrong_tries == 0 and o.hints_used <= cfg.success_max_hints


def is_struggle(o: Outcome, cfg: FadingConfig) -> bool:
    return not o.correct or o.wrong_tries > 0 or o.hints_used >= cfg.struggle_min_hints


def propose(level: int, outcomes: list[Outcome], cfg: FadingConfig) -> str | None:
    """'up' (less help), 'down' (more help) or None. `outcomes` oldest first,
    only those since the last level decision."""
    recent = outcomes[-cfg.up_after_successes:]
    if level < MAX_LEVEL and len(recent) == cfg.up_after_successes and all(is_success(o, cfg) for o in recent):
        return "up"
    window = outcomes[-cfg.down_window:]
    if level > MIN_LEVEL and len(window) == cfg.down_window:
        if sum(is_struggle(o, cfg) for o in window) >= cfg.down_struggles:
            return "down"
    return None


def proposal_message(direction: str, course_name: str) -> str:
    if direction == "up":
        return f"Στο μάθημα «{course_name}» τα καταφέρνεις όλο και πιο πολύ χωρίς βοήθεια. Θες να δοκιμάσεις λιγότερη βοήθεια;"
    return f"Το μάθημα «{course_name}» έχει τώρα πιο δύσκολη ύλη. Θες λίγο περισσότερη βοήθεια;"
