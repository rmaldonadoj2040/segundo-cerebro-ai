"""Strict vault validator (5-type ontology, clean graph mode).

Enforces two invariants for the Obsidian vault:

1. **No ghost nodes.** Every ``[[wikilink]]`` resolves to a real file with
   substantial content.
2. **Clean graph.** Graph nodes belong to exactly five entity folders —
   ``conceptos``, ``autores``, ``libros``, ``tecnologias``, ``tensiones``.
   Dashboards live at the vault root and are filtered out of the Graph View.
   Nothing else may exist as a Markdown file.

A run passes (``Status: OK``, exit code 0) only when EVERY check is clean:

- No 0-byte files / Obsidian placeholder files.
- No "title-only" files (single H1 with no body).
- No entity note shorter than ``MIN_BODY_CHARS`` chars (frontmatter excluded).
- No broken wikilinks.
- No excessively long titles (more than ``MAX_TITLE_WORDS`` words).
- No stray Markdown nodes outside the five entity folders.
- ``.obsidian/graph.json`` hides the dashboards AND defines per-type colours.

Anything else prints ``Status: ERROR`` with a per-category breakdown and exits
non-zero.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get as get_config

MIN_BODY_CHARS = 200
MAX_TITLE_WORDS = 10

ENTITY_FOLDERS = {"conceptos", "autores", "libros", "tecnologias", "tensiones"}

DASHBOARD_FILES = {
    "inicio.md",
    "capturas.md",
    "indice_de_temas.md",
    "indice_de_fuentes.md",
    "resumen_de_insights.md",
    "preguntas_abiertas.md",
}

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _canonical(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    no_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^\w\s/-]", "", no_accents, flags=re.UNICODE)
    return re.sub(r"[-\s_]+", " ", cleaned).strip().lower()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _has_real_content(text: str) -> bool:
    body = _strip_frontmatter(text).strip()
    if len(body) < MIN_BODY_CHARS:
        return False
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    return len(non_blank) > 1


def _graph_config_ok(vault: Path) -> tuple[bool, str]:
    """Check graph.json hides dashboards AND defines per-type node colours."""
    graph_path = vault / ".obsidian" / "graph.json"
    if not graph_path.exists():
        return False, "graph.json missing — dashboards would show as nodes"
    try:
        config = json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"graph.json unreadable ({exc})"

    search = config.get("search", "").lower()
    missing = [name for name in DASHBOARD_FILES if f"-path:{name}" not in search]
    if missing:
        return False, f"graph filter does not exclude: {', '.join(sorted(missing))}"

    color_queries = {
        g.get("query", "") for g in config.get("colorGroups", []) if isinstance(g, dict)
    }
    uncolored = [
        folder for folder in ENTITY_FOLDERS
        if f"path:{folder}/" not in color_queries
    ]
    if uncolored:
        return False, f"missing colour groups for: {', '.join(sorted(uncolored))}"
    return True, "dashboards filtered, 5 node types coloured"


def validate(vault: Path | None = None) -> int:
    vault = (vault or get_config().knowledge_map_dir).resolve()

    if not vault.exists():
        print("Status: ERROR")
        print(f"Reason: vault directory does not exist at {vault}")
        return 2

    md_files = [p for p in vault.rglob("*.md") if p.is_file()]
    if not md_files:
        print("Status: ERROR")
        print("Reason: vault has no Markdown files.")
        return 2

    # Authorized link targets: a file that exists AND has real content
    # (dashboards are authorized regardless of length).
    authorized: dict[str, Path] = {}
    for path in md_files:
        is_dashboard = path.name.lower() in DASHBOARD_FILES and path.parent == vault
        if is_dashboard or _has_real_content(_read(path)):
            authorized[_canonical(path.stem)] = path
            authorized[_canonical(path.relative_to(vault).with_suffix("").as_posix())] = path

    empty: list[Path] = []
    short: list[tuple[Path, int]] = []
    title_only: list[Path] = []
    broken_links: list[tuple[Path, str]] = []
    long_titles: list[Path] = []
    stray_nodes: list[Path] = []

    node_counts: dict[str, int] = {folder: 0 for folder in ENTITY_FOLDERS}

    for path in md_files:
        rel = path.relative_to(vault)
        is_dashboard = path.name.lower() in DASHBOARD_FILES and path.parent == vault
        parent_name = path.parent.name
        is_entity = path.parent.parent == vault and parent_name in ENTITY_FOLDERS
        if is_entity:
            node_counts[parent_name] += 1

        # Structural check: only entity folders and root dashboards are allowed.
        if not is_dashboard and not is_entity:
            stray_nodes.append(rel)

        if path.stat().st_size == 0:
            empty.append(rel)
            continue

        text = _read(path)
        body = _strip_frontmatter(text).strip()
        non_blank = [ln for ln in body.splitlines() if ln.strip()]

        if not body:
            empty.append(rel)
            continue

        if not is_dashboard and len(body) < MIN_BODY_CHARS:
            short.append((rel, len(body)))

        if len(non_blank) <= 1 and non_blank[0].lstrip().startswith("#"):
            title_only.append(rel)

        if len(path.stem.split()) > MAX_TITLE_WORDS:
            long_titles.append(rel)

        for match in _WIKILINK_RE.finditer(text):
            inner = match.group(1).split("|", 1)[0]
            target = inner.split("#", 1)[0].strip()
            if target and _canonical(target) not in authorized:
                broken_links.append((rel, match.group(1)))

    graph_ok, graph_msg = _graph_config_ok(vault)

    errors = bool(
        empty or short or title_only or broken_links
        or long_titles or stray_nodes or not graph_ok
    )

    total_nodes = sum(node_counts.values())

    print("=" * 50)
    print("VAULT VALIDATION REPORT")
    print("=" * 50)
    print(f"Vault path: {vault}")
    print(f"Files scanned: {len(md_files)}")
    print(f"Graph nodes: {total_nodes}")
    for folder in ("conceptos", "autores", "libros", "tecnologias", "tensiones"):
        print(f"  - {folder}: {node_counts[folder]}")
    print(f"Graph config: {'OK' if graph_ok else 'FAIL'} — {graph_msg}")
    print()

    def _block(title: str, items: list, formatter) -> None:
        if not items:
            return
        print(f"--- {title} ({len(items)}) ---")
        for item in items:
            print(f"  {formatter(item)}")
        print()

    _block("EMPTY / PLACEHOLDER FILES", empty, str)
    _block("SHORT FILES", short, lambda p: f"{p[0]} ({p[1]} chars, need ≥ {MIN_BODY_CHARS})")
    _block("TITLE-ONLY FILES", title_only, str)
    _block("BROKEN WIKILINKS", broken_links, lambda p: f"{p[0]}  →  [[{p[1]}]]")
    _block("VERY LONG TITLES", long_titles, str)
    _block("STRAY GRAPH NODES (not an entity type, not a dashboard)", stray_nodes, str)

    status = "ERROR" if errors else "OK"
    print(f"Status: {status}")
    return 1 if errors else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the generated Obsidian vault.")
    parser.add_argument("--vault", type=Path, help="Vault directory. Defaults to config/env path.")
    args = parser.parse_args()
    sys.exit(validate(args.vault))


if __name__ == "__main__":
    main()
