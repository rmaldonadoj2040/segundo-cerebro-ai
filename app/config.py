"""Load project configuration from config.toml with env-var overrides.

Priority order (highest first):
  1. Environment variables (OPENAI_API_KEY, LLM_MODEL, LLM_BASE_URL …)
  2. config.toml values
  3. Hard-coded defaults (as fall-backs inside this module)

Call ``get()`` to retrieve the fully-merged config object.
"""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _PROJECT_ROOT / "config.toml"


def _load_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file without third-party libraries.

    Uses ``tomllib`` (Python ≥ 3.11) or ``tomli`` as a fallback.
    Returns an empty dict if neither is available or the file is missing.
    """
    if not path.exists():
        LOGGER.warning("config.toml not found at %s — using defaults.", path)
        return {}

    # Try stdlib tomllib (Python 3.11+)
    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore[import]

        with open(path, "rb") as fh:
            return tomllib.load(fh)

    # Fallback: tomli (third-party, optional)
    try:
        import tomli  # type: ignore[import]

        with open(path, "rb") as fh:
            return tomli.load(fh)
    except ImportError:
        LOGGER.warning(
            "tomllib / tomli not available — config.toml will be ignored. "
            "Python 3.11+ is recommended."
        )
        return {}


@lru_cache(maxsize=1)
def get() -> "Config":
    """Return the singleton Config object (loaded once, cached thereafter)."""
    raw = _load_toml(_CONFIG_PATH)
    return Config(raw)


class Config:
    """Typed accessor for project configuration."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw
        root = _PROJECT_ROOT

        # ── Paths ────────────────────────────────────────────────────────────
        paths = raw.get("paths", {})
        self.raw_dir: Path = root / paths.get("raw_dir", "data/raw")
        self.wiki_dir: Path = root / paths.get("wiki_dir", "data/wiki")
        self.outputs_dir: Path = root / paths.get("outputs_dir", "data/outputs")
        self.prompts_dir: Path = root / paths.get("prompts_dir", "prompts")
        self.summaries_dir: Path = self.outputs_dir / "summaries"

        # ── LLM ──────────────────────────────────────────────────────────────
        llm = raw.get("llm", {})
        self.llm_model: str = (
            os.getenv("LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or llm.get("model", "gpt-4o-mini")
        )
        self.llm_base_url: str | None = (
            os.getenv("LLM_BASE_URL")
            or llm.get("base_url")
            or None
        )
        self.llm_timeout: float = float(llm.get("timeout", 30))
        self.llm_max_retries: int = int(llm.get("max_retries", 2))

        # API key: env var wins
        self.llm_api_key: str = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY")
            or llm.get("api_key", "")
        )

        # ── Wiki quality ─────────────────────────────────────────────────────
        wiki = raw.get("wiki", {})
        self.max_context_chars: int = int(wiki.get("max_context_chars", 4000))
        self.required_sections: list[str] = wiki.get(
            "required_sections",
            [
                "## Definition",
                "## Key Ideas",
                "## How it Works",
                "## Connections",
                "## Sources",
            ],
        )
        self.min_page_words: int = int(wiki.get("min_page_words", 30))

        # ── Topic grouping ────────────────────────────────────────────────────
        topics = raw.get("topics", {})
        self.seed_labels: list[str] = topics.get("seed_labels", [])
        self.max_label_words: int = int(topics.get("max_label_words", 3))
