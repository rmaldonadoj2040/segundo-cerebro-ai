"""Script to summarize raw markdown files."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get as _cfg
from app.file_utils import ensure_project_dirs
from app.summarizer import summarize_all, summarize_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize raw Markdown files.")
    parser.add_argument(
        "--source",
        type=Path,
        help="Optional single file to summarize. Defaults to all files in data/capturas.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ensure_project_dirs()
    args = parse_args()

    try:
        if args.source:
            source = args.source.expanduser().resolve()
            result = summarize_file(source)
            generated = [result] if result else []
        else:
            generated = summarize_all()
        logging.info("Summarized %d file(s).", len(generated))
    except Exception as exc:
        logging.error("Summarization failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
