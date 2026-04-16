"""Content Generator module — produces repurposed content from wiki pages."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get as _cfg
from app.file_utils import ensure_project_dirs, slugify, write_text
from app.llm_client import generate
from app.retriever import retrieve

LOGGER = logging.getLogger(__name__)


def build_content(topic_or_question: str) -> Path | None:
    """Generate repurposed content (IG reel, X thread, business insight).

    Retrieves relevant wiki pages for *topic_or_question*, then asks the LLM
    to generate three content forms.

    The output filename is derived from the topic string (deterministic) so
    repeated calls overwrite prior output rather than accumulating files.

    Returns:
        Path to the saved content file, or *None* on failure.
    """
    ensure_project_dirs()
    cfg = _cfg()

    matches = retrieve(topic_or_question, cfg.wiki_dir)

    prompt_file = cfg.prompts_dir / "content_from_wiki.md"
    if prompt_file.exists():
        from app.file_utils import read_text
        system_prompt = read_text(prompt_file).strip()
    else:
        system_prompt = (
            "Generate user-facing content from the wiki context. "
            "Keep the output grounded in the provided wiki pages."
        )

    context_blocks = [
        f"---\nSource: {path.name}\n{text}\n---" for path, text in matches
    ]
    context = "\n\n".join(context_blocks)

    full_prompt = (
        f"{system_prompt}\n\n"
        f"Generate 3 pieces of content about: {topic_or_question}\n\n"
        "1) IG Reel:\n"
        "   - Hook (pattern interrupt)\n"
        "   - Insight\n"
        "   - Tension/problem\n"
        "   - Takeaway\n"
        "2) X Thread:\n"
        "   - Opinionated\n"
        "   - Specific\n"
        "   - Not explanatory-only\n"
        "3) Business Insight:\n"
        "   - Must be concrete and actionable\n\n"
        f"Context:\n{context}"
    )

    try:
        source_names = [p.name for p, _ in matches]
        LOGGER.info("Generating content for: %s using concepts from: %s", topic_or_question, source_names)
        content = generate(full_prompt)

        out_dir = cfg.outputs_dir / "content"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Deterministic filename: derived from topic, not timestamp
        out_path = out_dir / f"{slugify(topic_or_question[:60])}.md"
        final_text = f"# Content: {topic_or_question}\n\n{content}\n"
        write_text(out_path, final_text)

        LOGGER.info("Content saved → %s", out_path)
        return out_path
    except Exception as exc:
        LOGGER.error("Failed to generate content: %s", exc)
        return None
