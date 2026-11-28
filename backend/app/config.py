"""Settings from config.toml (fading rules, search hints, Bayesian Knowledge Tracing)."""

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
    easy_down: int = 2
    easy_window: int = 3


@dataclass(frozen=True)
class SearchConfig:
    max_wrong_picks: int = 3


@dataclass(frozen=True)
class BKTConfig:
    p_init: float = 0.3
    p_learn: float = 0.15
    p_slip: float = 0.1
    p_guess_two_choices: float = 0.5
    p_guess_three_choices: float = 0.33
    p_guess_open: float = 0.05
    known_max_help: int = 1
    up_threshold: float = 0.90
    down_threshold: float = 0.40
    min_observations: int = 2
    label_almost: float = 0.60
    label_known: float = 0.90


@dataclass(frozen=True)
class Config:
    fading: FadingConfig
    search: SearchConfig
    bkt: BKTConfig
    engine: str = "bkt"  # "bkt" or "rules" (the simple rules of [fading], kept as fallback)


@lru_cache
def load_config(path: Path = CONFIG_PATH) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return Config(
        fading=FadingConfig(**data.get("fading", {})),
        search=SearchConfig(**data.get("search", {})),
        bkt=BKTConfig(**data.get("bkt", {})),
        engine=data.get("engine", {}).get("fading", "bkt"),
    )
