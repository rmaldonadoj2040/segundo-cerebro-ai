"""Daily pipeline: normalize → plan ontology → compile entities → derive → repair → index.

Builds a 5-type cultural knowledge map (conceptos / autores / libros /
tecnologias / tensiones).  Enforces the no-ghost-node invariant: by the time
control returns, every `[[wikilink]]` resolves to a real file with substantial
content; anything else has been demoted to plain text.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.concept_registry import ConceptRegistry, strip_frontmatter
from app.config import get as get_config
from app.content_generator import build_content
from app.file_utils import (
    ensure_project_dirs,
    list_markdown_files,
    read_text,
    write_text,
)
from app.normalize import normalize_to_spanish
from app.wiki_compiler import (
    ENTITY_TYPES,
    compile_entity_notes,
    generate_insights,
    generate_questions,
    plan_ontology,
)
from scripts.build_index import build_indices, ensure_graph_config

LOGGER = logging.getLogger(__name__)

TYPE_LABELS = {
    "concepto": "conceptos",
    "autor": "autores",
    "libro": "libros",
    "tecnologia": "tecnologías",
    "tension": "tensiones",
}


def _copy_tree_if_exists(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.mkdir(parents=True, exist_ok=True)


def _sync_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def _note_title(path: Path) -> str:
    content = strip_frontmatter(read_text(path))
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem.replace("-", " ").title()


def _descubrimientos_content(
    processed_files: list[str],
    entity_paths: dict[str, list[Path]],
    insights: list[dict],
    questions: list[dict],
    content_path: Path,
    date_str: str,
) -> str:
    lines = [f"# Descubrimientos del día — {date_str}\n"]
    lines.append("## Capturas procesadas")
    lines.extend(f"- {name}" for name in processed_files)

    type_labels = [
        ("concepto", "Conceptos"),
        ("autor", "Autores"),
        ("libro", "Libros e ideas"),
        ("tecnologia", "Tecnologías"),
        ("tension", "Tensiones"),
    ]
    for note_type, label in type_labels:
        lines.append("")
        lines.append(f"## {label}")
        paths = entity_paths.get(note_type, [])
        if paths:
            for path in paths:
                lines.append(f"- {_note_title(path)}")
        else:
            lines.append("_Sin entradas._")

    def _data_section(title: str, items: list[dict], key: str) -> None:
        lines.append("")
        lines.append(f"## {title}")
        if not items:
            lines.append("_Sin entradas._")
            return
        for item in items:
            lines.append(f"- {item['title']}: {item[key]}")

    _data_section("Insights más interesantes", insights, "description")
    _data_section("Preguntas abiertas", questions, "question")

    lines.append("")
    lines.append("## Idea de contenido del día")
    lines.append(f"- {content_path.name}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily pipeline")
    parser.add_argument("--scope", choices=["today", "all"], default="all")
    parser.add_argument("--question", type=str, help="Insight question")
    parser.add_argument("--content", type=str, help="Content prompt")
    parser.add_argument("--no-content", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    default_content = (
        "Convierte el insight más fuerte de hoy en una idea para reel o carrusel en español."
    )
    content_prompt = args.content or default_content

    ensure_project_dirs()
    cfg = get_config()

    capturas_files = list_markdown_files(cfg.captures_dir)
    if not capturas_files:
        print("No hay nuevas capturas para procesar.")
        print("Agrega archivos Markdown en data/capturas/ y vuelve a correr el comando.")
        sys.exit(0)

    if args.dry_run:
        print("--- DRY RUN MODE ---")
        print(f"Archivos a procesar: {[f.name for f in capturas_files]}")
        sys.exit(0)

    print(f"Procesando {len(capturas_files)} capturas...")

    try:
        with tempfile.TemporaryDirectory(prefix="llmks-run-") as tmp_dir:
            tmp_root = Path(tmp_dir)
            stage_map_dir = tmp_root / "vault"
            stage_outputs_dir = tmp_root / "outputs"
            stage_normalized_dir = tmp_root / "normalizado"

            stage_contenido_dir = stage_outputs_dir / "contenido"
            stage_descubrimientos_dir = stage_outputs_dir / "descubrimientos-diarios"

            # Start the staging vault fresh — do NOT inherit prior runs so
            # stale empty files cannot survive into a new run.
            stage_map_dir.mkdir(parents=True, exist_ok=True)
            _copy_tree_if_exists(cfg.outputs_dir, stage_outputs_dir)
            for d in (
                stage_normalized_dir,
                stage_contenido_dir,
                stage_descubrimientos_dir,
            ):
                d.mkdir(parents=True, exist_ok=True)
            # One folder per entity type — each becomes a graph cluster.
            for _note_type, (_folder, _prompt, _min) in ENTITY_TYPES.items():
                (stage_map_dir / _folder).mkdir(parents=True, exist_ok=True)

            normalized_paths: list[Path] = []
            for capture_path in capturas_files:
                print(f"Normalizando: {capture_path.name}...")
                raw = read_text(capture_path)
                normalized = normalize_to_spanish(raw, capture_path.name)
                if not normalized:
                    raise RuntimeError(f"Failed to normalize {capture_path.name}")
                # Normalized texts may contain raw `[[wikilinks]]` that the LLM
                # invented.  They live OUTSIDE the vault so they cannot create
                # Obsidian ghost nodes, but we strip the brackets for safety.
                normalized_clean = normalized.replace("[[", "").replace("]]", "")
                staged = stage_normalized_dir / capture_path.name
                write_text(staged, normalized_clean)
                normalized_paths.append(staged)

            print("Planificando ontología (5 tipos de nodo)...")
            registry = ConceptRegistry(stage_map_dir)
            ontology = plan_ontology(normalized_paths, registry, stage_map_dir)
            total_nodes = sum(len(v) for v in ontology.values())
            if len(ontology["concepto"]) < 6:
                raise RuntimeError(
                    f"Solo se planificaron {len(ontology['concepto'])} conceptos "
                    "— mínimo 6 esperado."
                )
            for note_type, entries in ontology.items():
                print(f"  → {len(entries)} {note_type}(s)")
            print(f"  → {total_nodes} nodos totales planificados.")

            # Compile every entity type into real notes (graph nodes).
            entity_paths: dict[str, list[Path]] = {}
            for note_type in ("concepto", "autor", "libro", "tecnologia", "tension"):
                if not ontology[note_type]:
                    entity_paths[note_type] = []
                    continue
                label = TYPE_LABELS.get(note_type, f"{note_type}s")
                print(f"Compilando {label}...")
                paths = compile_entity_notes(registry, normalized_paths, note_type)
                entity_paths[note_type] = paths
                print(f"  → {len(paths)} entradas compiladas.")

            if not entity_paths["concepto"]:
                raise RuntimeError("No se compiló ningún concepto.")

            # Insights and questions are dashboard data, never graph nodes.
            print("Generando insights...")
            insights = generate_insights(registry)
            print(f"  → {len(insights)} insights.")

            print("Generando preguntas...")
            questions = generate_questions(registry)
            print(f"  → {len(questions)} preguntas.")

            print("Construyendo dashboards...")
            build_indices(
                registry=registry,
                knowledge_map_dir=stage_map_dir,
                insights=insights,
                questions=questions,
            )

            print("Reparando wikilinks (no-ghost-node)...")
            stats = registry.repair_vault()
            print(
                f"  → {stats['files_scanned']} archivos revisados, "
                f"{stats['files_changed']} reescritos, "
                f"{stats['links_stripped']} links fantasma eliminados."
            )

            if args.no_content:
                raise RuntimeError(
                    "La opción --no-content no es compatible con la promesa actual."
                )

            print("Generando contenido...")
            content_path = build_content(
                content_prompt,
                wiki_dir=stage_map_dir,
                output_dir=stage_contenido_dir,
            )
            if content_path is None:
                raise RuntimeError("No se pudo generar la idea de contenido.")

            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            discoveries_path = stage_descubrimientos_dir / f"{today_str}.md"
            write_text(
                discoveries_path,
                _descubrimientos_content(
                    [path.name for path in capturas_files],
                    entity_paths,
                    insights,
                    questions,
                    content_path,
                    today_str,
                ),
            )

            print("Sincronizando vault definitivo...")
            # Wipe vault dir contents before sync to avoid stale ghost files
            # from prior runs.
            if cfg.knowledge_map_dir.exists():
                for item in cfg.knowledge_map_dir.iterdir():
                    if item.name == ".obsidian":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            _sync_tree(stage_map_dir, cfg.knowledge_map_dir)
            _sync_tree(stage_outputs_dir, cfg.outputs_dir)

            # Enforce clean graph mode on the real vault (preserves user's
            # visual tweaks; only rewrites the filter fields).
            ensure_graph_config(cfg.knowledge_map_dir)

            for staged in normalized_paths:
                final = cfg.archive_normalized_dir / staged.name
                write_text(final, read_text(staged))

            print("Moviendo capturas procesadas...")
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            for capture_path in capturas_files:
                destination = cfg.archive_originals_dir / capture_path.name
                if destination.exists():
                    destination = (
                        cfg.archive_originals_dir
                        / f"{capture_path.stem}_{timestamp}{capture_path.suffix}"
                    )
                shutil.move(str(capture_path), str(destination))

        print("Pipeline completado.")
    except Exception as exc:
        print(f"Error durante el pipeline: {exc}")
        print("Abortando. Las capturas permanecen intactas en data/capturas/.")
        sys.exit(1)


if __name__ == "__main__":
    main()
