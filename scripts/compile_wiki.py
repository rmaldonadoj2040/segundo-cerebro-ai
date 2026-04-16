"""Compile raw Markdown files into structured wiki pages."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.file_utils import RAW_DIR, WIKI_DIR, ensure_project_dirs
from app.wiki_compiler import compile_all, compile_file


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Compile raw Markdown into wiki pages.")
    parser.add_argument("--source", type=Path, help="Optional single raw Markdown file to compile.")
    return parser.parse_args()


def main() -> None:
    """Run the wiki compiler."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    ensure_project_dirs()
    args = parse_args()

    if args.source:
        source = args.source.expanduser()
        if not source.is_absolute():
            source = ROOT / source if (ROOT / source).exists() else RAW_DIR / source
        outputs = [compile_file(source, wiki_dir=WIKI_DIR)]
    else:
        outputs = compile_all(raw_dir=RAW_DIR, wiki_dir=WIKI_DIR)

    if not outputs:
        logging.info("No raw Markdown files found in %s", RAW_DIR)
        return
    logging.info("Compiled %d wiki page(s).", len(outputs))


if __name__ == "__main__":
    main()
