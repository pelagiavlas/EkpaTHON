"""Which support level should a NEW chapter start from?

Looks at earlier chapters of the same course: hints per question and share of
wrong answers, with recent chapters counting more (exponential decay). The
weighted score is mapped to a level with the thresholds in config.toml.
The student sees the suggestion and can always pick another level.
"""

from dataclasses import dataclass

from app.config import PredictionConfig
from app.learning.fading import MAX_LEVEL, MIN_LEVEL


@dataclass
class ChapterHistory:
    questions: int
    hints_per_question: float
    wrong_rate: float  # 0..1


@dataclass
class Suggestion:
    level: int
    score: float | None
    reason: str


def _fmt(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def weighted_score(history: list[ChapterHistory], cfg: PredictionConfig) -> float | None:
    """history: oldest chapter first. Chapters without answered questions are ignored."""
    used = [h for h in history if h.questions > 0]
    if not used:
        return None
    total = weight_sum = 0.0
    for age, h in enumerate(reversed(used)):
        w = cfg.recency_decay**age
        total += w * (h.hints_per_question + cfg.wrong_weight * h.wrong_rate)
        weight_sum += w
    return total / weight_sum


def score_to_level(score: float, cfg: PredictionConfig) -> int:
    for level, limit in zip((4, 3, 2), cfg.thresholds):
        if score < limit:
            return level
    return 1


def suggest_start_level(history: list[ChapterHistory], current_level: int, cfg: PredictionConfig) -> Suggestion:
    score = weighted_score(history, cfg)
    if score is None:
        return Suggestion(current_level, None, "Δεν έχεις ακόμα απαντήσει ερωτήσεις σε αυτό το μάθημα.")
    level = min(score_to_level(score, cfg), current_level + cfg.max_step_up)
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    recent = [h for h in history if h.questions > 0][-1]
    reason = (
        f"Στο προηγούμενο κεφάλαιο χρειάστηκες κατά μέσο όρο "
        f"{_fmt(recent.hints_per_question)} υποδείξεις ανά ερώτηση."
    )
    return Suggestion(level, round(score, 2), reason)
