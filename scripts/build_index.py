"""Build vault dashboards and the cinematic graph configuration.

The graph has seven visible node folders: conceptos / autores / libros /
tecnologias / tensiones / insights / preguntas.

Dashboard files (vault root, hidden from the Graph View):
  - ``topics_index.md``        — landing page: every node grouped by type.
  - ``sources_index.md``       — which capture produced which node.
  - ``insights_summary.md``    — list of generated insights.
  - ``open_questions.md``      — list of open questions.
  - ``Capturas.md``            — onboarding note.

``ensure_graph_config`` writes ``.obsidian/graph.json`` with per-type colour
groups and a filter that hides the dashboards.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.concept_registry import ConceptRegistry, strip_frontmatter
from app.config import get as _cfg
from app.file_utils import ensure_project_dirs, list_markdown_files, read_text, write_text

LOGGER = logging.getLogger(__name__)

DASHBOARD_NAMES = (
    "topics_index",
    "Capturas",
    "sources_index",
    "insights_summary",
    "open_questions",
)
_DASHBOARD_FILES = frozenset(f"{n.lower()}.md" for n in DASHBOARD_NAMES)

# note_type -> (folder, plural label)
ENTITY_LAYOUT: list[tuple[str, str, str]] = [
    ("concepto", "conceptos", "Conceptos"),
    ("autor", "autores", "Autores"),
    ("libro", "libros", "Libros e ideas"),
    ("tecnologia", "tecnologias", "Tecnologías"),
    ("tension", "tensiones", "Tensiones"),
    ("insight", "insights", "Insights"),
    ("pregunta", "preguntas", "Preguntas"),
]

# Per-type node colours for the Obsidian Graph View (decimal RGB).
GRAPH_COLORS: list[tuple[str, int]] = [
    ("path:conceptos/", 0xE0A33A),    # amber  — ideas / hubs
    ("path:autores/", 0x5B8DD9),      # blue   — thinkers
    ("path:libros/", 0x5BA86B),       # green  — books / historical ideas
    ("path:tecnologias/", 0xD9614F),  # coral  — technologies / platforms
    ("path:tensiones/", 0x9C6FCB),    # purple — philosophical tensions
    ("path:insights/", 0x4CAF50),     # green  — insights
    ("path:preguntas/", 0xF44336),    # red    — preguntas
]

_SOURCE_LINE_RE = re.compile(r"[-*]\s+([^\n]+\.(?:md|markdown))", re.IGNORECASE)


def _extract_sources(text: str) -> list[str]:
    sources: list[str] = []
    in_sources = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("## Sources", "## Fuentes"):
            in_sources = True
            continue
        if in_sources:
            if stripped.startswith("## "):
                break
            m = _SOURCE_LINE_RE.match(stripped)
            if m:
                sources.append(m.group(1))
    return sources


def _extract_title(path: Path, text: str) -> str:
    for line in strip_frontmatter(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip().replace("**", "")
            title = re.sub(r"^\d+[\.\)]\s*", "", title)
            return re.sub(r"\s+", " ", title).strip()
    return path.stem.replace("-", " ").title()


def _entity_link(registry: ConceptRegistry, path: Path, title: str, base_dir: Path) -> str:
    """Path-based wikilink to an entity file (with a human alias)."""
    entry = registry.lookup_by_path(path) or registry.lookup(title) or registry.lookup(path.stem)
    if entry is not None:
        rel = entry.relative_to(base_dir)
    else:
        rel = path.relative_to(base_dir).with_suffix("").as_posix()
    return f"[[{rel}|{title}]]"


def _related_inline(registry: ConceptRegistry, names: list[str]) -> str:
    return ", ".join(registry.format_link(n) for n in names if n)


# ── Graph configuration ──────────────────────────────────────────────────────

def _graph_filter_query() -> str:
    return " ".join(f"-path:{name}.md" for name in DASHBOARD_NAMES)


def ensure_graph_config(knowledge_map_dir: Path) -> None:
    """Write clean graph mode + per-type colour groups to ``.obsidian/graph.json``."""
    obsidian_dir = knowledge_map_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    graph_path = obsidian_dir / "graph.json"

    config: dict = {}
    if graph_path.exists():
        try:
            config = json.loads(graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

    config.setdefault("showTags", False)
    config.setdefault("showAttachments", False)
    config.setdefault("showOrphans", True)
    config.setdefault("collapse-filter", False)
    config.setdefault("collapse-color-groups", False)
    config["search"] = _graph_filter_query()
    config["hideUnresolved"] = True
    config["colorGroups"] = [
        {"query": query, "color": {"a": 1, "rgb": rgb}}
        for query, rgb in GRAPH_COLORS
    ]

    graph_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Graph config (filter + colours) written to %s", graph_path)


# ── Dashboards ───────────────────────────────────────────────────────────────

def build_indices(
    *,
    registry: ConceptRegistry,
    knowledge_map_dir: Path | None = None,
) -> None:
    ensure_project_dirs()
    cfg = _cfg()
    knowledge_map_dir = knowledge_map_dir or cfg.wiki_dir

    # Collect entity files per type.
    by_type: dict[str, list[Path]] = {}
    for note_type, folder, _label in ENTITY_LAYOUT:
        files = [
            f
            for f in list_markdown_files(knowledge_map_dir / folder)
            if f.name.lower() not in _DASHBOARD_FILES
        ]
        by_type[note_type] = sorted(files)

    if not any(by_type.values()):
        LOGGER.warning("No entity files to index.")
        return

    titles: dict[Path, str] = {}
    for files in by_type.values():
        for path in files:
            titles[path] = _extract_title(path, read_text(path))

    # Register dashboards so repair keeps links toward them.
    for name in DASHBOARD_NAMES:
        registry.register_path(
            name, note_type="indice", file_path=knowledge_map_dir / f"{name}.md"
        )

    hub_keys = {h.lower() for h in registry.hub_names}

    def _link(path: Path) -> str:
        return _entity_link(registry, path, titles[path], knowledge_map_dir)

    # ── topics_index.md ──────────────────────────────────────────────────────────
    inicio: list[str] = [
        "# Índice de Temas\n",
        "Mapa vivo del pensamiento contemporáneo, generado a partir de las capturas.",
        "El Graph View muestra conceptos, autores, libros, tecnologías, "
        "tensiones, insights y preguntas.\n",
    ]
    for note_type, _folder, label in ENTITY_LAYOUT:
        files = by_type.get(note_type, [])
        if not files:
            continue
        inicio.append(f"## {label}")
        for path in files:
            star = " ★" if titles[path].lower() in hub_keys else ""
            inicio.append(f"- {_link(path)}{star}")
        inicio.append("")

    inicio.append("## Cómo navegar")
    inicio.append("- ★ marca los conceptos *hub*: los nodos centrales del mapa.")
    inicio.append("- Revisa [[sources_index|Índice de fuentes]] para trazar cada idea.")
    inicio.append("- En el Graph View, cada color es un tipo de nodo.")
    write_text(knowledge_map_dir / "topics_index.md", "\n".join(inicio).rstrip() + "\n")

    # ── sources_index.md ───────────────────────────────────────────────
    source_map: dict[str, list[Path]] = defaultdict(list)
    for files in by_type.values():
        for path in files:
            for src in _extract_sources(read_text(path)):
                source_map[src].append(path)
    if source_map:
        lines = ["# Índice de Fuentes\n"]
        for src in sorted(source_map):
            lines.append(f"## {src}")
            for path in sorted(set(source_map[src])):
                lines.append(f"- {_link(path)}")
            lines.append("")
        sources_content = "\n".join(lines).rstrip() + "\n"
    else:
        sources_content = "# Índice de Fuentes\n\n_No se encontraron fuentes._\n"
    write_text(knowledge_map_dir / "sources_index.md", sources_content)

    # ── insights_summary.md ─────────────────────────────────────────────
    lines = ["# Resumen de Insights\n"]
    insights_files = by_type.get("insight", [])
    if insights_files:
        for path in insights_files:
            lines.append(f"- {_link(path)}")
    else:
        lines.append("_No se generaron insights._")
    write_text(knowledge_map_dir / "insights_summary.md", "\n".join(lines).rstrip() + "\n")

    # ── open_questions.md ──────────────────────────────────────────────
    lines = ["# Preguntas Abiertas\n"]
    preguntas_files = by_type.get("pregunta", [])
    if preguntas_files:
        for path in preguntas_files:
            lines.append(f"- {_link(path)}")
    else:
        lines.append("_No se generaron preguntas abiertas._")
    write_text(knowledge_map_dir / "open_questions.md", "\n".join(lines).rstrip() + "\n")

    # ── Capturas.md ────────────────────────────────────────────────────────
    write_text(
        knowledge_map_dir / "Capturas.md",
        (
            "# Capturas\n\n"
            "Coloca aquí notas crudas, enlaces o transcripciones antes de correr el pipeline.\n\n"
            "## Flujo\n"
            "- Agrega archivos Markdown en `data/inbox/`.\n"
            "- Ejecuta `python3 scripts/run_daily.py`.\n"
            "- Abre [[topics_index]] para explorar el mapa generado.\n"
        ),
    )


def main() -> None:
    """Standalone rebuild from whatever entity files already exist on disk."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    cfg = _cfg()
    registry = ConceptRegistry(cfg.knowledge_map_dir)
    for note_type, folder, _label in ENTITY_LAYOUT:
        for path in list_markdown_files(cfg.knowledge_map_dir / folder):
            title = _extract_title(path, read_text(path))
            registry.register(
                title, note_type=note_type, dir_path=cfg.knowledge_map_dir / folder
            )
    build_indices(registry=registry, knowledge_map_dir=cfg.wiki_dir)
    registry.repair_vault()
    ensure_graph_config(cfg.wiki_dir)
    LOGGER.info("Index building complete.")


if __name__ == "__main__":
    main()
