"""Q&A logic based on wiki content."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get as _cfg
from app.file_utils import ensure_project_dirs, slugify, write_text
from app.llm_client import generate
from app.retriever import retrieve

LOGGER = logging.getLogger(__name__)


def ask_question(question: str) -> Path | None:
    """Answer *question* by retrieving relevant wiki pages and calling the LLM.

    The answer is saved to ``data/outputs/answers/<slug>.md``.  The filename
    is derived from the question text (not a timestamp) so that repeated calls
    with the same question overwrite the previous answer rather than creating
    an ever-growing pile of files.

    Returns:
        Path to the saved answer file, or *None* on failure.
    """
    ensure_project_dirs()
    cfg = _cfg()

    matches = retrieve(question, cfg.wiki_dir, top_k=5)

    if len(matches) < 3:
        LOGGER.warning("Only %d source(s) found. Expanding retrieval to ensure comparison.", len(matches))
        # Expand retrieval by lowering min_score and increasing top_k slightly
        matches = retrieve(question, cfg.wiki_dir, top_k=8, min_score=0.1)

    prompt_file = cfg.prompts_dir / "answer_question.md"
    if prompt_file.exists():
        from app.file_utils import read_text
        system_prompt = read_text(prompt_file).strip()
    else:
        system_prompt = (
            "You MUST compare multiple sources. Find relationships, contradictions, and patterns."
        )

    context_blocks = []
    for path, text in matches:
        context_blocks.append(f"Source: {path.name}\n---\n{text}\n---")
    
    context = "\n\n".join(context_blocks)

    full_prompt = (
        f"{system_prompt}\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}"
    )

    try:
        source_names = [p.name for p, _ in matches]
        if len(source_names) < 2:
            LOGGER.warning("Context grounded in only ONE source: %s. Analysis may be limited.", source_names)
        
        LOGGER.info("Generating analytical answer to: %s using files: %s", question, source_names)
        answer = generate(full_prompt)

        out_dir = cfg.outputs_dir / "answers"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Deterministic filename: derived from question, not timestamp
        out_path = out_dir / f"{slugify(question[:60])}.md"
        content = f"# Q: {question}\n\n{answer}\n"
        write_text(out_path, content)

        LOGGER.info("Answer saved → %s", out_path)
        return out_path
    except Exception as exc:
        LOGGER.error("Failed to generate answer: %s", exc)
        return None
