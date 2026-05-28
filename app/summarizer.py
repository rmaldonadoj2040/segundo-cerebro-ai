"""Summarize captured markdown files into the configured summaries directory."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get as _cfg
from app.file_utils import list_markdown_files, read_text, write_text
from app.llm_client import generate

LOGGER = logging.getLogger(__name__)

_SUMMARY_SUFFIX = "_summary.md"


def _load_prompt() -> str:
    cfg = _cfg()
    prompt_file = cfg.prompts_dir / "summarize_source.md"
    if prompt_file.exists():
        return read_text(prompt_file).strip()
    return "Summarize this source markdown briefly. Include key ideas."


def summarize_file(path: Path, out_dir: Path | None = None) -> Path | None:
    """Read a markdown file, generate a summary using the LLM, and save it.

    Skips files whose names already end in ``_summary.md`` to avoid re-summarizing
    previously generated output.

    Args:
        path:    The raw markdown file to summarise.
        out_dir: Directory where the summary is written.
                 Defaults to the configured summaries directory.

    Returns:
        Path to the written summary file, or *None* on failure.
    """
    if path.name.endswith(_SUMMARY_SUFFIX):
        return None

    if out_dir is None:
        out_dir = _cfg().summaries_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / f"{path.stem}{_SUMMARY_SUFFIX}"

    text = read_text(path)
    if not text.strip():
        LOGGER.warning("Skipping empty file: %s", path.name)
        return None

    system_prompt = _load_prompt()
    full_prompt = f"{system_prompt}\n\nSource Content:\n{text}"

    try:
        LOGGER.info("Summarizing %s", path.name)
        response = generate(full_prompt)
        output_content = f"# Summary of {path.name}\n\n{response}\n"
        write_text(summary_path, output_content)
        LOGGER.info("Saved summary → %s", summary_path.name)
        return summary_path
    except Exception as exc:
        LOGGER.error("Failed to summarize %s: %s", path.name, exc)
        return None


def summarize_all(raw_dir: Path | None = None) -> list[Path]:
    """Summarize all raw markdown files that aren't already summaries.

    Args:
        raw_dir: Directory containing raw markdown files.
                 Defaults to the configured captures directory.

    Returns:
        List of paths to written summary files.
    """
    if raw_dir is None:
        raw_dir = _cfg().raw_dir

    summaries: list[Path] = []
    files = list_markdown_files(raw_dir)

    if not files:
        LOGGER.warning("No markdown files found in %s", raw_dir)
        return summaries

    for path in files:
        res = summarize_file(path)
        if res:
            summaries.append(res)

    return summaries
