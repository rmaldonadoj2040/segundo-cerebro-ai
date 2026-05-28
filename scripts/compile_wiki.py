"""Deprecated entry point — kept for backwards compatibility.

Concept compilation now requires the registry-backed two-phase pipeline
(plan concepts → compile → derive → repair).  That whole flow lives in
``run_daily.py``; there is no longer a standalone per-file compiler.

Running this script simply delegates to the daily pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_daily import main as run_daily_main


def main() -> None:
    print("compile_wiki.py is deprecated — delegating to run_daily.py")
    run_daily_main()


if __name__ == "__main__":
    main()
