"""Authoritative concept registry.

The registry is the single source of truth for which `[[wikilinks]]` are allowed
in the vault.  A link is allowed only if the registry resolves it to a real
file with substantial content (≥ ``MIN_CONTENT_CHARS`` after stripping
frontmatter).  Anything else gets converted to plain text by the repair pass.

Lifecycle
---------
1. **Planning** — register seed concept names (files do not exist yet).  The
   names are passed to the LLM as the *only* allowed link targets.
2. **Compilation** — each registered name becomes a real Markdown file.
3. **Authorization** — after every write, `is_authorized` checks the file on
   disk: it must exist and pass the content threshold.
4. **Repair** — `repair_text` rewrites or strips every `[[X]]` based on the
   final authorized state.  Nothing else may leave a dangling link.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.file_utils import read_text, slugify

# Minimum real-content length (frontmatter excluded) for a note to count as a
# legitimate, non-empty graph node.  Entity notes range from short technology
# entries to long concept essays — 200 chars is the universal floor below which
# a file is treated as empty / a ghost target.
MIN_CONTENT_CHARS = 200

_WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    """Remove a leading YAML frontmatter block, if present."""
    return _FRONTMATTER_RE.sub("", text, count=1)


def canonical_key(value: str) -> str:
    """Normalize *value* into a comparable key.

    - Strips accents and non-word characters.
    - Lowercases.
    - Collapses whitespace / hyphens / underscores.
    """
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^\w\s/-]", "", without_accents, flags=re.UNICODE)
    cleaned = re.sub(r"[-\s_]+", " ", cleaned)
    return cleaned.strip().lower()


@dataclass(frozen=True)
class ConceptEntry:
    name: str           # human-readable display name ("Efecto Google")
    slug: str           # filename slug ("efecto-google")
    note_type: str      # "concepto" | "tensión" | "insight" | "pregunta"
    path: Path          # absolute path where the file lives (or will live)

    def relative_to(self, base_dir: Path) -> str:
        return self.path.relative_to(base_dir).with_suffix("").as_posix()


class ConceptRegistry:
    """Maps canonical concept keys to their real file targets."""

    def __init__(self, vault_dir: Path) -> None:
        self.vault_dir = vault_dir
        self._by_key: dict[str, ConceptEntry] = {}
        self._entries: list[ConceptEntry] = []
        # Hub concepts — the high-degree anchors of the graph.
        self.hub_names: list[str] = []

    # ── Registration ────────────────────────────────────────────────────────

    def register(self, name: str, *, note_type: str, dir_path: Path) -> ConceptEntry:
        """Reserve a slot for *name*.

        Re-registering the same canonical name with the same note_type returns
        the existing entry (so two LLM calls with different casings collapse).
        Re-registering with a DIFFERENT type disambiguates by appending the
        type to the slug, so a "Proceso Creativo" tensión/insight/pregunta
        can never overwrite the "Proceso Creativo" concept.
        """
        name = name.strip()
        existing = self.lookup(name)
        if existing is not None and existing.note_type == note_type:
            return existing

        base_slug = slugify(name)
        if not base_slug:
            raise ValueError(f"Cannot register empty/unslugifiable name: {name!r}")

        slug = base_slug
        if existing is not None and existing.note_type != note_type:
            slug = f"{base_slug}-{slugify(note_type) or note_type}"

        path = dir_path / f"{slug}.md"
        entry = ConceptEntry(name=name, slug=slug, note_type=note_type, path=path)

        self._entries.append(entry)
        # Only register the human name and slug as lookup keys when this is the
        # first entry under that name; for disambiguated entries we only key on
        # the relative path so future lookups of the bare name keep resolving
        # to the original (typically the concept).
        if existing is None:
            self._by_key[canonical_key(name)] = entry
            self._by_key[canonical_key(slug)] = entry
        rel = path.relative_to(self.vault_dir).with_suffix("").as_posix()
        self._by_key[canonical_key(rel)] = entry
        return entry

    def register_path(self, name: str, *, note_type: str, file_path: Path) -> ConceptEntry:
        """Register an entry that lives at *file_path* exactly.

        Use this when the on-disk filename does not match ``slugify(name)`` —
        for example, dashboard files like ``indice_de_temas.md``.
        """
        name = name.strip()
        slug = file_path.stem
        entry = ConceptEntry(name=name, slug=slug, note_type=note_type, path=file_path)
        self._entries.append(entry)
        self._by_key[canonical_key(name)] = entry
        self._by_key[canonical_key(slug)] = entry
        rel = file_path.relative_to(self.vault_dir).with_suffix("").as_posix()
        self._by_key[canonical_key(rel)] = entry
        return entry

    def entries(self, note_type: str | None = None) -> list[ConceptEntry]:
        if note_type is None:
            return list(self._entries)
        return [e for e in self._entries if e.note_type == note_type]

    def names(self, note_type: str | None = None) -> list[str]:
        return [e.name for e in self.entries(note_type)]

    # ── Lookup & authorization ──────────────────────────────────────────────

    def lookup(self, target: str) -> ConceptEntry | None:
        if not target:
            return None
        key = canonical_key(target.split("#", 1)[0])
        return self._by_key.get(key)

    def lookup_by_path(self, path: Path) -> ConceptEntry | None:
        """Resolve an entry by the actual file path on disk."""
        for entry in self._entries:
            if entry.path == path:
                return entry
        return None

    def is_authorized(self, target: str) -> bool:
        entry = self.lookup(target)
        if entry is None:
            return False
        return self._has_real_content(entry.path, entry.note_type)

    @staticmethod
    def _has_real_content(path: Path, note_type: str = "concepto") -> bool:
        if not path.exists() or not path.is_file():
            return False
        try:
            text = read_text(path)
        except Exception:
            return False
        body = strip_frontmatter(text).strip()
        # Reject title-only files universally.
        non_blank_lines = [ln for ln in body.splitlines() if ln.strip()]
        if len(non_blank_lines) <= 1:
            return False
        # Index/dashboard files are system-generated and exempt from the
        # full content threshold — they just need to exist and have body.
        if note_type == "indice":
            return len(body) > 0
        return len(body) >= MIN_CONTENT_CHARS

    def authorized_entries(self) -> list[ConceptEntry]:
        seen: set[Path] = set()
        out: list[ConceptEntry] = []
        for entry in self._entries:
            if entry.path in seen:
                continue
            seen.add(entry.path)
            if self._has_real_content(entry.path):
                out.append(entry)
        return out

    def authorized_names(self, note_type: str | None = None) -> list[str]:
        entries = self.authorized_entries()
        if note_type is not None:
            entries = [e for e in entries if e.note_type == note_type]
        return [e.name for e in entries]

    # ── Repair ──────────────────────────────────────────────────────────────

    def format_link(self, target: str, alias: str | None = None) -> str:
        """Return a properly formatted `[[path|alias]]` or the plain alias."""
        target_clean = target.split("#", 1)[0].strip()
        section = target.split("#", 1)[1].strip() if "#" in target else ""
        display = (alias or target_clean).strip()

        entry = self.lookup(target_clean)
        if entry is None or not self._has_real_content(entry.path):
            return display  # plain text — no ghost link
        rel = entry.relative_to(self.vault_dir)
        link_target = f"{rel}#{section}" if section else rel
        return f"[[{link_target}|{display}]]"

    def repair_text(self, text: str) -> str:
        """Replace every `[[X]]` with a valid link or plain text.

        After this runs, no surviving `[[X]]` can point to a missing or empty
        file — that is the no-ghost-node invariant.
        """
        def _replace(match: re.Match[str]) -> str:
            inner = match.group(1)
            if "|" in inner:
                target, alias = inner.split("|", 1)
            else:
                target, alias = inner, None
            return self.format_link(target, alias)

        return _WIKILINK_RE.sub(_replace, text)

    def repair_file(self, path: Path) -> bool:
        """Repair wikilinks in *path*.  Returns True if the file changed."""
        original = read_text(path)
        repaired = self.repair_text(original)
        if repaired != original:
            path.write_text(repaired, encoding="utf-8")
            return True
        return False

    def repair_vault(self) -> dict[str, int]:
        """Repair every Markdown file in the vault.

        Returns counters: ``{"files_scanned": N, "files_changed": M, "links_stripped": K}``.
        """
        stripped = 0
        changed = 0
        scanned = 0
        for path in self.vault_dir.rglob("*.md"):
            if path.is_file():
                scanned += 1
                original = read_text(path)
                # Count strips for reporting
                before_links = len(_WIKILINK_RE.findall(original))
                repaired = self.repair_text(original)
                after_links = len(_WIKILINK_RE.findall(repaired))
                stripped += max(0, before_links - after_links)
                if repaired != original:
                    path.write_text(repaired, encoding="utf-8")
                    changed += 1
        return {"files_scanned": scanned, "files_changed": changed, "links_stripped": stripped}

    # ── Prompt helpers ──────────────────────────────────────────────────────

    def prompt_block(self, note_type: str = "concepto") -> str:
        """Return a bulleted list of authorized concept names for prompts."""
        names = [e.name for e in self.entries(note_type)]
        return "\n".join(f"- {name}" for name in names)
