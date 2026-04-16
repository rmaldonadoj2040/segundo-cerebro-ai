"""Generate content from wiki topics."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.content_generator import build_content

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate content (IG, X thread, Insight).")
    parser.add_argument("topic", type=str, help="The topic or question for content generation.")
    return parser.parse_args()

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    
    out = build_content(args.topic)
    if not out:
        sys.exit(1)

if __name__ == "__main__":
    main()
