"""Settings from config.toml (fading rules and prediction thresholds)."""

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass(frozen=True)
class FadingConfig:
    up_after_successes: int = 3
    success_max_hints: int = 1
    down_window: int = 3
    down_struggles: int = 2
    struggle_min_hints: int = 3


@dataclass(frozen=True)
class PredictionConfig:
    recency_decay: float = 0.5
    wrong_weight: float = 2.0
    thresholds: tuple[float, float, float] = (0.75, 1.5, 2.5)
    max_step_up: int = 1


@lru_cache
def load_config(path: Path = CONFIG_PATH) -> tuple[FadingConfig, PredictionConfig]:
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    prediction = dict(data.get("prediction", {}))
    if "thresholds" in prediction:
        prediction["thresholds"] = tuple(prediction["thresholds"])
    return FadingConfig(**data.get("fading", {})), PredictionConfig(**prediction)
