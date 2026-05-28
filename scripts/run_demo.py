"""Run a zero-cost demo in ``demo_workspace/`` using mock LLM responses."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "demo_workspace"
SAMPLE_DOCS = ROOT / "examples" / "sample_docs"


def _demo_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "OPENAI_API_KEY": "mock",
            "LLM_MODEL": env.get("LLM_MODEL", "gpt-4o-mini"),
            "LLMKS_CAPTURES_DIR": str(DEMO_ROOT / "capturas"),
            "LLMKS_KNOWLEDGE_MAP_DIR": str(DEMO_ROOT / "vault"),
            "LLMKS_OUTPUTS_DIR": str(DEMO_ROOT / "outputs"),
            "LLMKS_ARCHIVE_ORIGINALS_DIR": str(DEMO_ROOT / "archivo" / "originales"),
            "LLMKS_ARCHIVE_NORMALIZED_DIR": str(DEMO_ROOT / "archivo" / "normalizado"),
        }
    )
    return env


def _run(args: list[str], env: dict[str, str]) -> None:
    print("$ " + " ".join(args))
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    captures_dir = DEMO_ROOT / "capturas"
    captures_dir.mkdir(parents=True, exist_ok=True)

    for source in sorted(SAMPLE_DOCS.glob("*.md")):
        shutil.copy2(source, captures_dir / source.name)

    env = _demo_env()
    _run([sys.executable, "scripts/run_daily.py", "--verbose"], env)
    _run([sys.executable, "scripts/validate_vault.py"], env)
    _run(
        [
            sys.executable,
            "scripts/ask.py",
            "¿Qué relación hay entre atención, creatividad e IA?",
        ],
        env,
    )

    print()
    print("Demo complete.")
    print(f"Vault: {DEMO_ROOT / 'vault'}")
    print(f"Answers: {DEMO_ROOT / 'outputs' / 'respuestas'}")


if __name__ == "__main__":
    main()
