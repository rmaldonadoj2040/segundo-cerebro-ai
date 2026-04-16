"""Wiki compilation logic.

Topic grouping strategy
-----------------------
1. **Seed-label match** (deterministic):
   If the file's first ``# Heading`` or its stem matches one of the seed
   labels in ``config.toml [topics] seed_labels``, that label is used
   directly — no LLM call required.

2. **LLM topic call** (for unmatched files):
   The LLM is asked for a short (1-3 word) topic label.  The response is
   normalised (stripped, title-cased, truncated to ``max_label_words`` words)
   before being used as a grouping key.  This prevents minor variations like
   "AI Agents" vs "AI Agent" from creating separate wiki pages.

Output file naming
------------------
Each topic maps to ``wiki_dir/<slugified-topic>.md``.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from app.config import get as _cfg
from app.file_utils import list_markdown_files, read_text, write_text, slugify
from app.llm_client import generate

LOGGER = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _first_heading(text: str) -> str:
    """Return the text of the first ``# Heading`` in *text*, or ''."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _normalise_topic(raw_label: str, max_words: int) -> str:
    """Strip, title-case, and truncate a topic label.

    Also removes surrounding quotes that the LLM sometimes adds.
    """
    label = raw_label.strip().strip("\"'").strip()
    label = re.sub(r"\s+", " ", label)          # collapse whitespace
    words = label.split()
    if len(words) > max_words:
        label = " ".join(words[:max_words])
    return label.title()


def _seed_match(text: str, stem: str, seed_labels: list[str]) -> str | None:
    """Return the matching seed label for *text* / *stem*, or *None*."""
    heading = _first_heading(text).lower()
    stem_lower = stem.lower().replace("-", " ").replace("_", " ")
    for label in seed_labels:
        label_lower = label.lower()
        if label_lower in heading or heading in label_lower:
            return label
        if label_lower in stem_lower or stem_lower in label_lower:
            return label
    return None


def _load_compile_prompt(topic: str) -> str:
    cfg = _cfg()
    prompt_file = cfg.prompts_dir / "compile_concept.md"
    if prompt_file.exists():
        return read_text(prompt_file).replace("{Topic Name}", topic)
    return (
        f"Compile a wiki page for {topic}. "
        "Use headings: # Title, ## Definition, ## Key Ideas, ## How it Works, "
        "## Connections, ## Sources."
    )


# ── Core functions ────────────────────────────────────────────────────────────

def assign_topics(files: list[Path]) -> dict[str, list[tuple[str, str]]]:
    """Group files into topic buckets.

    Returns:
        Mapping of ``topic_label → [(filename, text), …]``.
    """
    cfg = _cfg()
    topic_map: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for path in sorted(files):  # sorted for determinism
        if path.name.endswith("_summary.md"):
            continue

        text = read_text(path)

        # 1. Deterministic seed match (no LLM call)
        topic = _seed_match(text, path.stem, cfg.seed_labels)

        # 2. LLM fallback
        if topic is None:
            truncated = text[: cfg.max_context_chars]
            prompt = (
                "What is the single most specific 1-3 word topic representing this text? "
                "Reply ONLY with the topic name, no punctuation.\n\n"
                f"Text ({path.name}):\n{truncated}"
            )
            try:
                raw_label = generate(prompt)
                topic = _normalise_topic(raw_label, cfg.max_label_words)
                LOGGER.info("LLM assigned topic %r to %s", topic, path.name)
            except Exception as exc:
                LOGGER.error("Failed to assign topic for %s: %s", path.name, exc)
                topic = _normalise_topic(path.stem.replace("-", " "), cfg.max_label_words)
                LOGGER.warning("Falling back to stem-derived topic %r for %s", topic, path.name)

        topic_map[topic].append((path.name, text))

    return dict(topic_map)


def compile_topic(
    topic: str,
    sources: list[tuple[str, str]],
    wiki_dir: Path,
) -> Path | None:
    """Compile one topic's sources into a wiki page.

    If a wiki page already exists for *topic*, its existing content is
    included in the prompt so the LLM can update it without losing prior info.

    Args:
        topic:    Topic label (human-readable, e.g. "AI Agents").
        sources:  List of ``(filename, text)`` pairs.
        wiki_dir: Directory where the wiki page is written.

    Returns:
        Path to the written wiki page, or *None* on LLM failure.
    """
    cfg = _cfg()
    system_prompt = _load_compile_prompt(topic)

    context_lines: list[str] = []
    for name, text in sources:
        context_lines.append(f"--- Source: {name} ---")
        # Truncate each source to avoid exceeding context limits
        context_lines.append(text[: cfg.max_context_chars])

    context = "\n".join(context_lines)

    output_path = wiki_dir / f"{slugify(topic)}.md"
    if output_path.exists():
        existing_text = read_text(output_path)
        context = (
            "--- EXISTING WIKI PAGE (update without losing existing info) ---\n"
            f"{existing_text}\n\n"
            "--- NEW SOURCE INFO ---\n"
            f"{context}"
        )

    full_prompt = f"{system_prompt}\n\nTopic: {topic}\n\nContext:\n{context}"

    try:
        LOGGER.info("Compiling wiki page for topic: %s", topic)
        result = generate(full_prompt)
        write_text(output_path, result.strip() + "\n")
        return output_path
    except Exception as exc:
        LOGGER.error("Failed to compile topic %r: %s", topic, exc)
        return None


def compile_file(source_path: Path, wiki_dir: Path | None = None) -> Path | None:
    """Compile one raw Markdown file into the wiki directory."""
    if wiki_dir is None:
        wiki_dir = _cfg().wiki_dir
    topic_map = assign_topics([source_path])
    for topic, sources in topic_map.items():
        result = compile_topic(topic, sources, wiki_dir)
        if result:
            return result
    return None


def compile_all(raw_dir: Path | None = None, wiki_dir: Path | None = None) -> list[Path]:
    """Compile all Markdown files in the raw directory into wiki pages.

    Returns:
        Sorted list of paths to written wiki pages.
    """
    cfg = _cfg()
    if raw_dir is None:
        raw_dir = cfg.raw_dir
    if wiki_dir is None:
        wiki_dir = cfg.wiki_dir

    all_files = list_markdown_files(raw_dir)
    topic_map = assign_topics(all_files)

    outputs: list[Path] = []
    for topic, sources in sorted(topic_map.items()):  # sorted for determinism
        result = compile_topic(topic, sources, wiki_dir)
        if result:
            outputs.append(result)
    return outputs
