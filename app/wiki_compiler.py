"""Ontology compiler — turns capturas into a 5-type cultural knowledge map.

Node ontology
-------------
The vault is built from five entity types, each its own folder / graph cluster:

  - ``concepto``    — abstract ideas (the hubs of the graph)
  - ``autor``       — thinkers
  - ``libro``       — books / historical ideas
  - ``tecnologia``  — platforms / technologies
  - ``tension``     — philosophical tensions (bridge nodes)

Pipeline
--------
1. **plan_ontology** — one LLM call extracts the whole ontology (entities of
   every type + hub designation) from the normalized capturas, and registers
   every entity in the ConceptRegistry up-front.
2. **compile_entity_notes** — each registered entity becomes a real Markdown
   note.  The prompt embeds the authorized link list so the LLM may only emit
   ``[[wikilinks]]`` toward known entities.
3. **generate_insights / generate_questions** — return plain data that the
   index builder embeds into dashboards (they never become graph nodes).

After every write the caller runs ``registry.repair_vault()`` so no surviving
``[[wikilink]]`` points at a missing or empty file.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.concept_registry import (
    ConceptEntry,
    ConceptRegistry,
    canonical_key,
    strip_frontmatter,
)
from app.config import get as _cfg
from app.file_utils import read_text, write_text
from app.llm_client import generate

LOGGER = logging.getLogger(__name__)

# note_type -> (folder name, compile prompt, minimum body chars)
ENTITY_TYPES: dict[str, tuple[str, str, int]] = {
    "concepto": ("conceptos", "compile_concept.md", 400),
    "autor": ("autores", "compile_autor.md", 220),
    "libro": ("libros", "compile_libro.md", 220),
    "tecnologia": ("tecnologias", "compile_tecnologia.md", 200),
    "tension": ("tensiones", "compile_tension.md", 220),
}

# Soft caps so the graph stays in the 25-35 node range.
ENTITY_CAPS: dict[str, int] = {
    "concepto": 14,
    "autor": 8,
    "libro": 7,
    "tecnologia": 7,
    "tension": 6,
}
MAX_HUBS = 4


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generate_frontmatter(note_type: str, cfg) -> str:
    publishable = "yes" if note_type != "pregunta" else "no"
    return (
        "---\n"
        f"type: {note_type}\n"
        f"audience: {cfg.generation_audience}\n"
        f"status: {cfg.generation_status}\n"
        f"publishable: {publishable}\n"
        "---\n"
    )


def _clean_generated_title(raw_title: str) -> str:
    cleaned = raw_title.strip()
    cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -:#\"'`")


def _extract_title(text: str) -> str | None:
    for line in strip_frontmatter(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return _clean_generated_title(stripped[2:])
    return None


def _ensure_h1(body: str, expected: str) -> str:
    """Guarantee the body starts with `# <expected>`."""
    body = body.lstrip()
    if body.startswith("# "):
        lines = body.splitlines()
        lines[0] = f"# {expected}"
        return "\n".join(lines)
    return f"# {expected}\n\n{body}"


_WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


def _wikilink_to_plain(text: str) -> str:
    """Convert every `[[target|alias]]` in *text* to its display text."""
    def _repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if "|" in inner:
            return inner.split("|", 1)[1].strip()
        return inner.split("#", 1)[0].strip()
    return _WIKILINK_RE.sub(_repl, text)


def links_only_in_connections(body: str) -> str:
    """Keep wikilinks only inside the `## Conexiones` section.

    Inline links scattered through prose make the Obsidian graph hyper-dense.
    Every node's graph edges should come from one deliberate section, so links
    anywhere else are demoted to plain text.
    """
    out: list[str] = []
    in_connections = False
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_connections = stripped.lower().startswith("## conexiones")
        out.append(line if in_connections else _wikilink_to_plain(line))
    return "\n".join(out)


def _load_prompt(name: str) -> str:
    return read_text(_cfg().prompts_dir / name)


def _dir_for(vault_dir: Path, note_type: str) -> Path:
    return vault_dir / ENTITY_TYPES[note_type][0]


# ── Phase 1: ontology planning ───────────────────────────────────────────────

_PLAN_SECTIONS: list[tuple[str, tuple[str, ...]]] = [
    ("concepto", ("CONCEPTO",)),
    ("autor", ("AUTOR",)),
    ("libro", ("LIBRO", "IDEA")),
    ("tecnologia", ("TECNOLOG",)),
    ("tension", ("TENSION", "TENSIÓN")),
    ("hubs", ("HUB",)),
]


def _parse_ontology(response: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {key: [] for key, _ in _PLAN_SECTIONS}
    current: str | None = None
    for raw_line in response.splitlines():
        raw = raw_line.strip()
        if not raw:
            continue
        header = raw.lstrip("#").strip().rstrip(":").upper()
        matched = None
        if len(header) <= 28:
            for key, keywords in _PLAN_SECTIONS:
                if any(kw in header for kw in keywords):
                    matched = key
                    break
        if matched:
            current = matched
            continue
        if current is None:
            continue
        name = raw.lstrip("-*•").strip()
        name = re.sub(r"^\d+[\.\)]\s*", "", name)
        name = re.sub(r"\s*\(.*?\)\s*$", "", name)  # drop trailing parenthetical
        name = _clean_generated_title(name)
        if name and len(name) <= 60:
            buckets[current].append(name)
    return buckets


def _dedupe(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        key = canonical_key(name)
        if key and key not in seen:
            seen.add(key)
            out.append(name)
    return out


def plan_ontology(
    capture_paths: list[Path],
    registry: ConceptRegistry,
    vault_dir: Path,
) -> dict[str, list[ConceptEntry]]:
    """Extract the full 5-type ontology and register every entity.

    Returns a mapping ``note_type -> [ConceptEntry, ...]``.
    """
    cfg = _cfg()
    excerpts = []
    for path in capture_paths:
        excerpts.append(f"--- {path.name} ---\n{read_text(path)[: cfg.max_context_chars]}")
    combined = "\n\n".join(excerpts)

    prompt = (
        "Eres el curador de un 'mapa vivo del pensamiento contemporáneo' para Obsidian.\n"
        "Lee las capturas y extrae una ONTOLOGÍA de 5 tipos de nodo. El mapa debe ser\n"
        "cinematográfico: pocos nodos, muy reconocibles, con clusters semánticos fuertes.\n\n"
        "Objetivo total: entre 25 y 35 nodos. Nombres CORTOS y elegantes (1-4 palabras).\n\n"
        "Extrae exactamente estas secciones (usa estos encabezados literales):\n\n"
        "## CONCEPTOS\n"
        "10-12 ideas abstractas centrales (ej. 'Mente extendida', 'Economía de la atención').\n"
        "Evita categorías vagas. Deben formar 3 clusters: segundo cerebro / memoria, "
        "atención / sobrecarga, creatividad / IA generativa.\n\n"
        "## AUTORES\n"
        "5-7 pensadores REALES nombrados o claramente implicados en los textos "
        "(ej. 'Nicholas Carr', 'Herbert Simon', 'Cal Newport', 'Andy Clark').\n\n"
        "## LIBROS\n"
        "4-6 libros o ideas históricas concretas (ej. 'The Shallows', 'Deep Work', "
        "'La mente extendida', 'Zettelkasten').\n\n"
        "## TECNOLOGIAS\n"
        "4-6 plataformas o tecnologías concretas (ej. 'Google', 'TikTok', 'Obsidian', "
        "'Algoritmos de recomendación').\n\n"
        "## TENSIONES\n"
        "3-5 tensiones filosóficas, cada una con formato 'X vs Y' (ej. 'Velocidad vs Profundidad').\n\n"
        "## HUBS\n"
        "3-4 conceptos (de la lista CONCEPTOS) que serán los nodos centrales del grafo.\n\n"
        "Devuelve SOLO las secciones con una entidad por línea, sin explicaciones.\n\n"
        f"Capturas:\n{combined}"
    )

    raw = generate(prompt)
    buckets = _parse_ontology(raw)

    result: dict[str, list[ConceptEntry]] = {}
    for note_type in ("concepto", "autor", "libro", "tecnologia", "tension"):
        names = _dedupe(buckets.get(note_type, []))[: ENTITY_CAPS[note_type]]
        entries: list[ConceptEntry] = []
        dir_path = _dir_for(vault_dir, note_type)
        for name in names:
            entry = registry.register(name, note_type=note_type, dir_path=dir_path)
            entries.append(entry)
        result[note_type] = entries
        LOGGER.info("Planned %d %s entities", len(entries), note_type)

    # Resolve hub names against the registered concepts.
    hub_names: list[str] = []
    for raw_hub in _dedupe(buckets.get("hubs", []))[:MAX_HUBS]:
        entry = registry.lookup(raw_hub)
        if entry is not None and entry.note_type == "concepto":
            hub_names.append(entry.name)
    if not hub_names and result["concepto"]:
        hub_names = [e.name for e in result["concepto"][:MAX_HUBS]]
    registry.hub_names = hub_names
    LOGGER.info("Hubs: %s", ", ".join(hub_names))

    return result


# ── Phase 2: entity compilation ──────────────────────────────────────────────

def _format_authorized_block(registry: ConceptRegistry, exclude: str | None) -> str:
    exclude_key = canonical_key(exclude) if exclude else None
    labels = [
        ("concepto", "CONCEPTOS"),
        ("autor", "AUTORES"),
        ("libro", "LIBROS"),
        ("tecnologia", "TECNOLOGÍAS"),
        ("tension", "TENSIONES"),
    ]
    blocks: list[str] = []
    for note_type, label in labels:
        names = [
            e.name
            for e in registry.entries(note_type)
            if canonical_key(e.name) != exclude_key
        ]
        if names:
            blocks.append(f"{label}:\n" + "\n".join(f"- {n}" for n in names))
    return "\n\n".join(blocks)


def compile_entity_notes(
    registry: ConceptRegistry,
    capture_paths: list[Path],
    note_type: str,
) -> list[Path]:
    """Compile a real Markdown note for every registered entity of *note_type*."""
    cfg = _cfg()
    _, prompt_file, min_chars = ENTITY_TYPES[note_type]
    template = _load_prompt(prompt_file)
    hubs = ", ".join(registry.hub_names) or "—"

    sources = [(p.name, read_text(p)) for p in capture_paths]
    context = "\n\n".join(
        f"--- Source: {name} ---\n{text[: cfg.max_context_chars]}"
        for name, text in sources
    )

    written: list[Path] = []
    for entry in registry.entries(note_type):
        authorized = _format_authorized_block(registry, exclude=entry.name)
        system_prompt = (
            template.replace("{Topic Name}", entry.name)
            .replace("{Authorized Targets}", authorized)
            .replace("{Hubs}", hubs)
        )
        full_prompt = f"{system_prompt}\n\nEntidad: {entry.name}\n\nContexto:\n{context}"

        try:
            LOGGER.info("Compiling %s: %s", note_type, entry.name)
            result = generate(full_prompt)
        except Exception as exc:
            LOGGER.error("LLM failed for %s %s: %s", note_type, entry.name, exc)
            continue

        body = _ensure_h1(result.strip(), entry.name)
        # Graph edges come only from the Conexiones section — strip the rest.
        body = links_only_in_connections(body)
        if len(body) < min_chars:
            LOGGER.warning(
                "%s %s produced only %d chars (need %d); skipping.",
                note_type,
                entry.name,
                len(body),
                min_chars,
            )
            continue

        write_text(entry.path, _generate_frontmatter(note_type, cfg) + body + "\n")
        written.append(entry.path)

    return written


# ── Phase 3: derived data for dashboards (not graph nodes) ───────────────────

def _concept_summary_block(registry: ConceptRegistry, max_chars: int = 700) -> str:
    lines: list[str] = []
    for entry in registry.authorized_entries():
        if entry.note_type != "concepto":
            continue
        text = strip_frontmatter(read_text(entry.path)).strip()
        lines.append(f"### {entry.name}\n{text[:max_chars]}")
    return "\n\n".join(lines)


_TITLE_SEP_RE = re.compile(r"\s+[-—–]\s+|:\s+")


def _parse_titled_lines(response: str) -> list[tuple[str, str]]:
    """Parse `Título - Descripción` lines, tolerant of separators and bullets."""
    out: list[tuple[str, str]] = []
    for raw in response.splitlines():
        line = raw.strip().strip("-*•").strip()
        line = re.sub(r"^\d+[\.\)]\s*", "", line).replace("**", "")
        if not line:
            continue
        match = _TITLE_SEP_RE.search(line)
        if not match:
            continue
        title = _clean_generated_title(line[: match.start()])
        title = " ".join(title.split()[:6])
        desc = line[match.end():].strip()
        if title and len(desc) > 8:
            out.append((title, desc))
    return out


def _related_authorized_concepts(
    registry: ConceptRegistry,
    text: str,
    count: int = 3,
) -> list[str]:
    chosen: list[str] = []
    lower = text.lower()
    for entry in registry.authorized_entries():
        if entry.note_type == "concepto" and entry.name.lower() in lower:
            chosen.append(entry.name)
    if not chosen:
        chosen = [
            e.name for e in registry.authorized_entries() if e.note_type == "concepto"
        ][:count]
    return chosen[:count]


def generate_insights(registry: ConceptRegistry) -> list[dict]:
    summaries = _concept_summary_block(registry)
    if not summaries:
        return []
    prompt = (
        "Identifica exactamente 5 insights profundos y no obvios a partir de estos conceptos.\n"
        "Un insight es una observación perspicaz, idealmente paradójica.\n"
        "Reglas: título corto (máx. 4 palabras); formato 'Título - Explicación de una línea'.\n\n"
        f"Conceptos:\n{summaries}"
    )
    try:
        response = generate(prompt)
    except Exception as exc:
        LOGGER.error("Insight generation failed: %s", exc)
        return []
    out = []
    for title, desc in _parse_titled_lines(response)[:5]:
        out.append({
            "title": title,
            "description": desc,
            "related": _related_authorized_concepts(registry, desc),
        })
    return out


def generate_questions(registry: ConceptRegistry) -> list[dict]:
    summaries = _concept_summary_block(registry)
    if not summaries:
        return []
    prompt = (
        "Genera exactamente 5 preguntas abiertas y reflexivas a partir de estos conceptos.\n"
        "Reglas: título corto (máx. 4 palabras); formato 'Título Corto - ¿Pregunta larga?'.\n\n"
        f"Conceptos:\n{summaries}"
    )
    try:
        response = generate(prompt)
    except Exception as exc:
        LOGGER.error("Question generation failed: %s", exc)
        return []
    out = []
    for title, question in _parse_titled_lines(response)[:5]:
        if not question.endswith("?"):
            continue
        out.append({
            "title": title,
            "question": question,
            "related": _related_authorized_concepts(registry, question, count=2),
        })
    return out
