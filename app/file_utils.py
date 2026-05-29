"""Small file helpers used by the command-line scripts."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.config import get as _cfg

# ── Convenience path aliases (read from config at import time) ───────────────
# These replicate the old module-level constants so existing import sites still
# work without changes.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _c():  # pragma: no cover – thin shim so callers don't have to import config
    return _cfg()


@property  # type: ignore[misc]  – used at module level via __getattr__
def _lazy(name: str) -> Path:  # noqa: D401
    return getattr(_cfg(), name)


# Lazy module-level attributes so the config is not evaluated until first use.
def __getattr__(name: str) -> Path:
    mapping = {
        "RAW_DIR": "raw_dir",
        "WIKI_DIR": "wiki_dir",
        "OUTPUTS_DIR": "outputs_dir",
        "PROMPTS_DIR": "prompts_dir",
        "DATA_DIR": None,  # kept for backward compat
    }
    if name in mapping:
        attr = mapping[name]
        if attr is None:
            return PROJECT_ROOT / "data"
        return getattr(_cfg(), attr)
    raise AttributeError(name)


# ── Directory helpers ────────────────────────────────────────────────────────

def ensure_project_dirs() -> None:
    """Create the expected data directories if they do not exist.

    Under clean graph mode, each note type gets its own vault subdirectory.
    """
    cfg = _cfg()
    for directory in (
        cfg.inbox_dir,
        cfg.raw_dir,
        cfg.wiki_dir,
        cfg.outputs_dir,
        cfg.archive_originals_dir,
        cfg.archive_normalized_dir,
        cfg.conceptos_dir,
        cfg.autores_dir,
        cfg.libros_dir,
        cfg.tecnologias_dir,
        cfg.tensiones_dir,
        cfg.insights_dir,
        cfg.preguntas_dir,
        cfg.respuestas_dir,
        cfg.contenido_dir,
        cfg.descubrimientos_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# ── I/O helpers ──────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    """Read UTF-8 text from a file, falling back to latin-1 if needed."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text to a file, creating parent directories first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def list_markdown_files(directory: Path) -> list[Path]:
    """Return Markdown files in a directory, sorted by name.

    Handles missing directories gracefully — returns an empty list.
    Does NOT recurse into subdirectories.
    """
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".markdown"}
    )


def list_markdown_files_recursive(directory: Path) -> list[Path]:
    """Return Markdown files in a directory tree, sorted by relative path."""
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".markdown"}
    )


# ── String helpers ───────────────────────────────────────────────────────────

_NON_WORD_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACE_RE = re.compile(r"[-\s_]+", re.UNICODE)


def slugify(value: str) -> str:
    """Convert text into a simple lowercase filename slug.

    Uses only ASCII alphanumeric characters and hyphens.
    Consecutive non-alphanumeric characters are collapsed into a single hyphen.
    Leading/trailing hyphens are stripped.

    >>> slugify("Hello, World!")
    'hello-world'
    >>> slugify("  ")
    'untitled'
    """
    cleaned = _NON_WORD_RE.sub("", value).strip().lower()
    slug = _SPACE_RE.sub("-", cleaned).strip("-")
    return slug or "untitled"


# ── Ingest helper ──────────────────────────────────────────────────────────

def ingest_source_file(source: Path, name: str | None = None) -> Path:
    """Copy a Markdown source file into the raw data directory.

    Raises:
        FileNotFoundError: if *source* does not exist.
        ValueError: if *source* is not a Markdown file.
    """
    ensure_project_dirs()
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    if source.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"Only Markdown files (.md / .markdown) can be ingested; got: {source.suffix!r}")

    destination_name = name or source.name
    if Path(destination_name).suffix == "":
        destination_name = f"{destination_name}.md"
    destination = _cfg().inbox_dir / destination_name
    shutil.copy2(source, destination)
    return destination
