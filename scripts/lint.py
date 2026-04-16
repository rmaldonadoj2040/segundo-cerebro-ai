"""Run the wiki linter and exit with a non-zero code when issues are found."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.wiki_linter import lint_wiki


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        report_path, issue_count = lint_wiki()
        logging.info("Report written to %s", report_path)
        if issue_count:
            logging.warning("%d issue(s) found in wiki.", issue_count)
            sys.exit(1)
    except Exception as exc:
        logging.error("Linter failed: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
