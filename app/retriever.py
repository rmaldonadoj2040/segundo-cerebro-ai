"""Shared keyword-based retrieval used by the QA engine and content generator.

No vector databases.  Uses a simple TF-inspired scoring scheme:
  - Filter out common English stop-words
  - For each wiki page, count how many query keywords appear in its text
  - Return pages sorted by match count (descending), capped at *top_k*

This is more precise than the old ``any(len(w) > 3 ...)`` approach because:
  1. Stop-words are explicitly excluded (not approximated by length).
  2. Pages are *ranked* rather than binary included/excluded.
  3. Substring matching is done at word boundaries (\\b) to avoid
     "agent" matching "management".
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.file_utils import list_markdown_files_recursive, read_text

LOGGER = logging.getLogger(__name__)

# ── Stop-words ───────────────────────────────────────────────────────────────
# A minimal but practical English stop-word list.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a about above after again against all also am an and any are aren't as at
    be because been before being below between both but by can't cannot could
    couldn't did didn't do does doesn't doing don't down during each few for
    from further get got had hadn't has hasn't have haven't having he he'd
    he'll he's her here here's hers herself him himself his how how's i i'd
    i'll i'm i've if in into is isn't it it's its itself let's me more most
    mustn't my myself no nor not of off on once only or other ought our ours
    ourselves out over own same shan't she she'd she'll she's should shouldn't
    so some such than that that's the their theirs them themselves then there
    there's these they they'd they'll they're they've this those through to too
    under until up very was wasn't we we'd we'll we're we've were weren't what
    what's when when's where where's which while who who's whom why why's will
    with won't would wouldn't you you'd you'll you're you've your yours yourself
    yourselves
    """.split()
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _expand_keyword(kw: str) -> list[str]:
    """Return simple morphological variations of the keyword."""
    vars_ = {kw}
    if kw.endswith("e"):
        vars_.update([kw + "s", kw + "d", kw[:-1] + "ing"])
    elif kw.endswith("y"):
        vars_.update([kw[:-1] + "ies", kw[:-1] + "ied", kw + "ing"])
    else:
        vars_.update([kw + "s", kw + "es", kw + "ing", kw + "ed"])
    return list(vars_)

def _extract_keywords(text: str) -> list[str]:
    """Return lowercase alpha tokens that are not stop-words."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _score(query: str, keywords: list[str], doc_text: str) -> float:
    """Score document based on frequency, headings, and exact phrase."""
    doc_lower = doc_text.lower()
    score = 0.0

    headings_text = " ".join(
        line.strip() for line in doc_lower.splitlines() 
        if line.strip().startswith("#")
    )

    query_lower = query.lower()
    clean_query = re.sub(r'[^\w\s]', '', query_lower).strip()
    if clean_query and clean_query in doc_lower:
        score += 10.0

    matched_keywords = 0
    for kw in keywords:
        variations = _expand_keyword(kw)
        kw_matched = False
        for var in variations:
            pattern = r"\b" + re.escape(var) + r"\b"
            freq_matches = len(re.findall(pattern, doc_lower))
            if freq_matches > 0:
                score += freq_matches * 1.0
                kw_matched = True
            
            heading_matches = len(re.findall(pattern, headings_text))
            if heading_matches > 0:
                score += heading_matches * 5.0
                
        if kw_matched:
            matched_keywords += 1
            
    if keywords and matched_keywords < len(keywords) / 2:
        score -= 5.0
        
    return score


# ── Public API ───────────────────────────────────────────────────────────────

_INDEX_FILENAMES: frozenset[str] = frozenset(
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


def _get_document_keywords(text: str) -> set[str]:
    """Extract a set of significant keywords from document text."""
    return set(_extract_keywords(text))


def retrieve(
    query: str,
    wiki_dir: Path,
    top_k: int = 5,
    min_score: float = 1.0,
) -> list[tuple[Path, str]]:
    """Return the top-*k* wiki pages most relevant to *query*.

    Pages are ranked by the number of query keywords they contain.
    Index/meta files are always excluded.

    Args:
        query:    Natural-language question or topic description.
        wiki_dir: Directory containing wiki markdown files.
        top_k:    Maximum number of pages to return.
        min_score: Pages scoring below this threshold are excluded.
                   Set to 0 to include all pages (fallback mode).

    Returns:
        List of ``(path, text)`` pairs, best match first.
        Returns multiple pages if possible, applying a diversity penalty.
    """
    wiki_files = [
        f for f in list_markdown_files_recursive(wiki_dir) if f.name.lower() not in _INDEX_FILENAMES
    ]

    if not wiki_files:
        return []

    keywords = _extract_keywords(query)

    if not keywords:
        # Query was all stop-words — return first 3 files as generic fallback
        return [(p, read_text(p)) for p in wiki_files[:min(3, len(wiki_files))]]

    all_scored: list[tuple[float, Path, str, set[str]]] = []
    for path in wiki_files:
        text = read_text(path)
        s = _score(query, keywords, text)
        if s >= min_score:
            all_scored.append((s, path, text, _get_document_keywords(text)))

    # Sort descending by initial score
    all_scored.sort(key=lambda x: (-x[0], x[1].name))

    results: list[tuple[Path, str]] = []
    selected_keywords: set[str] = set()

    # Re-rank with diversity penalty
    while all_scored and len(results) < top_k:
        # Calculate scores with penalty for overlap with already selected docs
        best_candidate_idx = -1
        best_diversity_score = -float('inf')

        for i, (base_score, path, text, doc_kws) in enumerate(all_scored):
            # Penalty: subtract points for each keyword that overlaps with selected ones
            overlap = len(doc_kws.intersection(selected_keywords))
            diversity_score = base_score - (overlap * 0.5)
            
            if diversity_score > best_diversity_score:
                best_diversity_score = diversity_score
                best_candidate_idx = i

        if best_candidate_idx != -1:
            score, path, text, doc_kws = all_scored.pop(best_candidate_idx)
            results.append((path, text))
            selected_keywords.update(doc_kws)
            LOGGER.info("Selected %s (final score %s) for query: %r", path.name, score, query)
        else:
            break

    if results:
        return results

    # Nothing matched — return first 3 files as a last-resort fallback
    return [(p, read_text(p)) for p in wiki_files[:min(3, len(wiki_files))]]
