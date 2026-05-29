"""Copy a Markdown source file into the configured captures directory."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.file_utils import ingest_source_file


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Ingest a Markdown file into data/inbox.")
    parser.add_argument("source", type=Path, help="Path to the Markdown file to ingest.")
    parser.add_argument("--name", help="Optional destination filename (with or without .md).")
    return parser.parse_args()


def main() -> None:
    """Run the ingest command."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    try:
        destination = ingest_source_file(args.source, name=args.name)
        logging.info("Ingested → %s", destination)
    except FileNotFoundError as exc:
        logging.error("%s", exc)
        sys.exit(1)
    except ValueError as exc:
        logging.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
