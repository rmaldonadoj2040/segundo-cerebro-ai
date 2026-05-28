"""Linting for wiki pages.

Checks performed on every wiki concept page:
  1. **Very short page** — fewer than ``config.wiki.min_page_words`` words.
  2. **Missing required section** — each section in
     ``config.wiki.required_sections`` must be present.
  3. **Empty section** — a ``## Heading`` line immediately followed by the
     next heading or end-of-file with no intervening content.
  4. **TODO placeholder** — lines containing ``TODO`` or ``FIXME``.

The report is written to ``outputs/reports/wiki_health.md``.
The function returns ``(report_path, issue_count)`` so callers can propagate
a non-zero exit code when the wiki has problems.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get as _cfg
from app.file_utils import ensure_project_dirs, list_markdown_files, read_text, write_text

LOGGER = logging.getLogger(__name__)

_SPECIAL_FILES: frozenset[str] = frozenset(
    {
        "topics_index.md",
        "sources_index.md",
        "open_questions.md",
        "indice_de_temas.md",
        "indice_de_fuentes.md",
        "preguntas_abiertas.md",
        "resumen_de_insights.md",
        "inicio.md",
        "capturas.md",
    }
)


def _check_page(path: Path, text: str, required_sections: list[str], min_words: int) -> list[str]:
    """Return a list of issue strings for *path*.  Empty list means no issues."""
    issues: list[str] = []
    lines = text.splitlines()

    # 1. Very short page
    if len(text.split()) < min_words:
        issues.append(f"- Very short page (< {min_words} words)")

    # 2. Missing required sections
    for req in required_sections:
        if req not in text:
            issues.append(f"- Missing section: `{req}`")

    # 3. Empty sections
    in_section = False
    section_heading = ""
    content_seen = False
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("## "):
            if in_section and not content_seen:
                issues.append(f"- Empty section: `{section_heading}`")
            in_section = True
            section_heading = line
            content_seen = False
        elif in_section and line and not line.startswith("#"):
            content_seen = True
    # Check last section
    if in_section and not content_seen:
        issues.append(f"- Empty section: `{section_heading}`")

    # 4. TODO / FIXME placeholders
    for i, raw_line in enumerate(lines, start=1):
        if "TODO" in raw_line or "FIXME" in raw_line:
            issues.append(f"- Unresolved TODO/FIXME on line {i}")

    return issues


def lint_wiki() -> tuple[Path, int]:
    """Run structural checks on all wiki concept pages.

    Returns:
        ``(report_path, total_issue_count)``  — callers should exit with a
        non-zero code when *total_issue_count* > 0.
    """
    ensure_project_dirs()
    cfg = _cfg()

    note_dirs = (
        cfg.conceptos_dir,
        cfg.autores_dir,
        cfg.libros_dir,
        cfg.tecnologias_dir,
        cfg.tensiones_dir,
    )
    concept_files = [
        path
        for directory in note_dirs
        for path in list_markdown_files(directory)
        if path.name.lower() not in _SPECIAL_FILES
    ]

    report_lines: list[str] = ["# Wiki Health Report\n"]
    total_issues = 0

    if not concept_files:
        report_lines.append("_No wiki pages found._\n")
    else:
        for path in concept_files:
            text = read_text(path)
            issues = _check_page(
                path,
                text,
                cfg.required_sections,
                cfg.min_page_words,
            )
            total_issues += len(issues)

            report_lines.append(f"### {path.name}")
            if issues:
                report_lines.extend(issues)
            else:
                report_lines.append("- ✓ Everything looks good!")
            report_lines.append("")

    if total_issues:
        report_lines.insert(1, f"> **{total_issues} issue(s) found.**\n")
    else:
        report_lines.insert(1, "> **Wiki is healthy — no issues found.**\n")

    out_dir = cfg.outputs_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wiki_health.md"

    write_text(out_path, "\n".join(report_lines))
    LOGGER.info("Wiki linter report → %s (%d issue(s))", out_path, total_issues)
    return out_path, total_issues
