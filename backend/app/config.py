"""Settings from config.toml (fading rules, search hints)."""

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


@lru_cache
def load_config(path: Path = CONFIG_PATH) -> tuple[FadingConfig, SearchConfig]:
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return FadingConfig(**data.get("fading", {})), SearchConfig(**data.get("search", {}))
