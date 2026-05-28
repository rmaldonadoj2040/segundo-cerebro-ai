"""Reset the isolated demo workspace.

This removes only ``demo_workspace/``. It never touches the user's real
``data/``, ``vault/`` or ``outputs/`` directories.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "demo_workspace"


def main() -> None:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    for directory in (
        DEMO_ROOT / "capturas",
        DEMO_ROOT / "vault",
        DEMO_ROOT / "outputs",
        DEMO_ROOT / "archivo" / "originales",
        DEMO_ROOT / "archivo" / "normalizado",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    print(f"Demo workspace reset: {DEMO_ROOT}")


if __name__ == "__main__":
    main()
