"""Script to ask questions against the wiki."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.qa_engine import ask_question


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a question against the wiki knowledge base.")
    parser.add_argument("question", type=str, help="The question to answer.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    out = ask_question(args.question)
    if not out:
        logging.error("Failed to generate answer.")
        sys.exit(1)
    print(out)


if __name__ == "__main__":
    main()
