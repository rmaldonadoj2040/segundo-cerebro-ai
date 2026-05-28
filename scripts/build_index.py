"""Build vault dashboards and the cinematic graph configuration.

The graph has five visible node types — concepto / autor / libro / tecnologia /
tension — one folder each.  Insights and open questions are NOT nodes: they are
embedded as text inside the dashboard files.

Dashboard files (vault root, hidden from the Graph View):
  - ``Inicio.md``              — landing page: every node grouped by type,
                                 plus embedded insights and questions.
  - ``indice_de_temas.md``     — index of all nodes by type.
  - ``indice_de_fuentes.md``   — which capture produced which node.
  - ``resumen_de_insights.md`` — embedded insights.
  - ``preguntas_abiertas.md``  — embedded open questions.
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
    "Inicio",
    "Capturas",
    "indice_de_temas",
    "indice_de_fuentes",
    "resumen_de_insights",
    "preguntas_abiertas",
)
_DASHBOARD_FILES = frozenset(f"{n.lower()}.md" for n in DASHBOARD_NAMES)

# note_type -> (folder, plural label)
ENTITY_LAYOUT: list[tuple[str, str, str]] = [
    ("concepto", "conceptos", "Conceptos"),
    ("autor", "autores", "Autores"),
    ("libro", "libros", "Libros e ideas"),
    ("tecnologia", "tecnologias", "Tecnologías"),
    ("tension", "tensiones", "Tensiones"),
]

# Per-type node colours for the Obsidian Graph View (decimal RGB).
GRAPH_COLORS: list[tuple[str, int]] = [
    ("path:conceptos/", 0xE0A33A),    # amber  — ideas / hubs
    ("path:autores/", 0x5B8DD9),      # blue   — thinkers
    ("path:libros/", 0x5BA86B),       # green  — books / historical ideas
    ("path:tecnologias/", 0xD9614F),  # coral  — technologies / platforms
    ("path:tensiones/", 0x9C6FCB),    # purple — philosophical tensions
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
    insights: list[dict] | None = None,
    questions: list[dict] | None = None,
) -> None:
    ensure_project_dirs()
    cfg = _cfg()
    knowledge_map_dir = knowledge_map_dir or cfg.knowledge_map_dir
    insights = insights or []
    questions = questions or []

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

    # ── indice_de_temas.md ─────────────────────────────────────────────────
    topics = ["# Índice de Temas\n"]
    for note_type, _folder, label in ENTITY_LAYOUT:
        files = by_type[note_type]
        if not files:
            continue
        topics.append(f"## {label}")
        for path in files:
            topics.append(f"- {_link(path)}")
        topics.append("")
    write_text(knowledge_map_dir / "indice_de_temas.md", "\n".join(topics).rstrip() + "\n")

    # ── indice_de_fuentes.md ───────────────────────────────────────────────
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
    write_text(knowledge_map_dir / "indice_de_fuentes.md", sources_content)

    # ── resumen_de_insights.md ─────────────────────────────────────────────
    lines = ["# Resumen de Insights\n"]
    if insights:
        for item in insights:
            lines.append(f"## {item['title']}")
            lines.append(item["description"])
            related = _related_inline(registry, item.get("related", []))
            if related:
                lines.append(f"\n**Conceptos relacionados:** {related}")
            lines.append("")
    else:
        lines.append("_No se generaron insights._")
    write_text(knowledge_map_dir / "resumen_de_insights.md", "\n".join(lines).rstrip() + "\n")

    # ── preguntas_abiertas.md ──────────────────────────────────────────────
    lines = ["# Preguntas Abiertas\n"]
    if questions:
        for item in questions:
            lines.append(f"## {item['title']}")
            lines.append(item["question"])
            related = _related_inline(registry, item.get("related", []))
            if related:
                lines.append(f"\n**Conceptos relacionados:** {related}")
            lines.append("")
    else:
        lines.append("_No se generaron preguntas abiertas._")
    write_text(knowledge_map_dir / "preguntas_abiertas.md", "\n".join(lines).rstrip() + "\n")

    # ── Inicio.md ──────────────────────────────────────────────────────────
    inicio: list[str] = [
        "# Inicio\n",
        "Mapa vivo del pensamiento contemporáneo, generado a partir de las capturas.",
        "El Graph View muestra cinco tipos de nodo: conceptos, autores, libros, "
        "tecnologías y tensiones.\n",
    ]
    for note_type, _folder, label in ENTITY_LAYOUT:
        files = by_type[note_type]
        if not files:
            continue
        inicio.append(f"## {label}")
        for path in files:
            star = " ★" if titles[path].lower() in hub_keys else ""
            inicio.append(f"- {_link(path)}{star}")
        inicio.append("")

    inicio.append("## Insights destacados")
    if insights:
        for item in insights:
            inicio.append(f"- **{item['title']}**: {item['description']}")
    else:
        inicio.append("_Sin insights._")
    inicio.append("")

    inicio.append("## Preguntas abiertas")
    if questions:
        for item in questions:
            inicio.append(f"- **{item['title']}**: {item['question']}")
    else:
        inicio.append("_Sin preguntas._")
    inicio.append("")

    inicio.append("## Cómo navegar")
    inicio.append("- ★ marca los conceptos *hub*: los nodos centrales del mapa.")
    inicio.append("- Abre [[indice_de_temas|Índice de temas]] para ver todo por tipo.")
    inicio.append("- Revisa [[indice_de_fuentes|Índice de fuentes]] para trazar cada idea.")
    inicio.append("- En el Graph View, cada color es un tipo de nodo.")
    write_text(knowledge_map_dir / "Inicio.md", "\n".join(inicio).rstrip() + "\n")

    # ── Capturas.md ────────────────────────────────────────────────────────
    write_text(
        knowledge_map_dir / "Capturas.md",
        (
            "# Capturas\n\n"
            "Coloca aquí notas crudas, enlaces o transcripciones antes de correr el pipeline.\n\n"
            "## Flujo\n"
            "- Agrega archivos Markdown en `data/capturas/`.\n"
            "- Ejecuta `python3 scripts/run_daily.py`.\n"
            "- Abre [[Inicio]] para explorar el mapa generado.\n"
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
    build_indices(registry=registry)
    registry.repair_vault()
    ensure_graph_config(cfg.knowledge_map_dir)
    LOGGER.info("Index building complete.")


if __name__ == "__main__":
    main()
