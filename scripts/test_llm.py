"""Quick smoke-test for the LLM connection.

Usage:
  OPENAI_API_KEY=mock python3 scripts/test_llm.py       # mock mode
  OPENAI_API_KEY=<key> python3 scripts/test_llm.py      # real API call
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.llm_client import generate


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info("Testing LLM client …")
    try:
        response = generate("Say hello in exactly five words.")
        print("LLM response:", response)
    except Exception as exc:
        logging.error("LLM test failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
