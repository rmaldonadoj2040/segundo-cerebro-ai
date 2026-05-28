"""Core application package for Segundo Cerebro AI.

Loads ``.env`` from the project root automatically when the package is
first imported.  This means every ``scripts/*.py`` entry-point gets the
environment variables from ``.env`` without any extra setup.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv  # type: ignore[import]

    load_dotenv(_ENV_FILE, override=False)  # shell env vars take precedence
except ImportError:
    # dotenv is optional — the app still works with env vars set manually
    pass
