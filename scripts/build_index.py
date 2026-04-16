"""Build indices and metadata aggregations from wiki pages.

Generates three files inside ``data/wiki/``:
  - ``topics_index.md``   — alphabetical list of all topic slugs.
  - ``sources_index.md``  — which raw source files contributed to which topic.
  - ``open_questions.md`` — open questions extracted from wiki content by LLM.

Source attribution
------------------
The wiki compiler writes a ``## Sources`` section in each page.  This script
reads lines inside that section to extract referenced source filenames.  It
does NOT look for the pipeline delimiter (``--- Source: ... ---``) which only
exists during compilation, not in the final output.
"""

from __future__ import annotations

import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get as _cfg
from app.file_utils import ensure_project_dirs, list_markdown_files, read_text, write_text
from app.llm_client import generate

LOGGER = logging.getLogger(__name__)

_SPECIAL_FILES: frozenset[str] = frozenset(
    {"topics_index.md", "sources_index.md", "open_questions.md"}
)

# Matches lines like "- sample_raw.md" or "* some_file.md" in ## Sources sections
_SOURCE_LINE_RE = re.compile(r"[-*]\s+([\w.\-]+\.(?:md|markdown))", re.IGNORECASE)


def _extract_sources(text: str) -> list[str]:
    """Extract source filenames from the ``## Sources`` section of a wiki page."""
    sources: list[str] = []
    in_sources = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Sources":
            in_sources = True
            continue
        if in_sources:
            if stripped.startswith("## "):
                break  # Next section started
            m = _SOURCE_LINE_RE.match(stripped)
            if m:
                sources.append(m.group(1))
    return sources


def build_indices() -> None:
    ensure_project_dirs()
    cfg = _cfg()
    wiki_files = [
        f for f in list_markdown_files(cfg.wiki_dir) if f.name not in _SPECIAL_FILES
    ]

    if not wiki_files:
        LOGGER.warning("No wiki files to index.")
        return

    topics: list[str] = []
    source_map: dict[str, list[str]] = defaultdict(list)
    combined_text: list[str] = []

    for path in wiki_files:
        topic_name = path.stem.replace("-", " ").title()
        topics.append(topic_name)
        text = read_text(path)
        combined_text.append(f"--- {topic_name} ---\n{text[:1000]}")

        for src in _extract_sources(text):
            source_map[src].append(topic_name)

    # topics_index.md
    topics_content = "# Topics Index\n\n"
    for t in sorted(topics):
        topics_content += f"- {t}\n"
    write_text(cfg.wiki_dir / "topics_index.md", topics_content)
    LOGGER.info("Written topics_index.md (%d topics)", len(topics))

    # sources_index.md
    sources_content = "# Sources Index\n\n"
    if source_map:
        for src in sorted(source_map):
            sources_content += f"## {src}\n"
            for t in sorted(set(source_map[src])):
                sources_content += f"- {t}\n"
            sources_content += "\n"
    else:
        sources_content += "_No source attributions found in wiki pages._\n"
    write_text(cfg.wiki_dir / "sources_index.md", sources_content)
    LOGGER.info("Written sources_index.md (%d sources)", len(source_map))

    # open_questions.md
    open_q_prompt = (
        "Extract a list of implied or explicit open questions from the following "
        "wiki text.  Be concise — bullet points only, no preamble.\n\n"
        + "\n".join(combined_text)
    )

    try:
        LOGGER.info("Extracting open questions …")
        questions = generate(open_q_prompt).strip()
        open_q_content = f"# Open Questions\n\n{questions}\n"
        write_text(cfg.wiki_dir / "open_questions.md", open_q_content)
        LOGGER.info("Written open_questions.md")
    except Exception as exc:
        LOGGER.error("Failed to extract open questions: %s", exc)
        write_text(
            cfg.wiki_dir / "open_questions.md",
            "# Open Questions\n\n_Could not generate open questions (LLM error)._\n",
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_indices()
    LOGGER.info("Index building complete.")


if __name__ == "__main__":
    main()
