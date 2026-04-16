"""OpenAI-compatible LLM client abstraction.

Environment variables (all optional — see also config.toml):
  OPENAI_API_KEY  or  LLM_API_KEY  — your API key
  LLM_MODEL       — model name (default: gpt-4o-mini)
  LLM_BASE_URL    — override base URL for OpenAI-compatible endpoints

Mock mode:
  Set OPENAI_API_KEY=mock (or LLM_API_KEY=mock) to return deterministic
  stub responses without any network calls.  Useful for CI and dry-runs.
"""

from __future__ import annotations

import logging
import os

LOGGER = logging.getLogger(__name__)

# ── Mock mode ────────────────────────────────────────────────────────────────

_MOCK_KEY = "mock"

_MOCK_TOPIC_KEYWORDS: dict[str, str] = {
    "retrieval": "Retrieval Augmented Generation",
    "rag": "Retrieval Augmented Generation",
    "agent": "AI Agents",
    "productivity": "Productivity",
    "knowledge": "Knowledge Management",
    "machine learning": "Machine Learning",
    "llm": "Large Language Models",
}


def _mock_response(prompt: str) -> str:
    """Return a deterministic stub response for mock mode.

    Topic-assignment prompts get a stable label derived from prompt keywords.
    All other prompts get a templated multi-section response that satisfies
    the wiki linter's required-sections check.
    """
    prompt_lower = prompt.lower()

    # Topic assignment prompt (expects just a label back)
    if "single most specific" in prompt_lower and "topic" in prompt_lower:
        for kw, label in _MOCK_TOPIC_KEYWORDS.items():
            if kw in prompt_lower:
                return label
        return "General Concept"

    # Generic wiki / summary response — includes all required sections so
    # the linter doesn't flag mock output as broken.
    return (
        "## Definition\n"
        "A placeholder definition generated in mock mode.\n\n"
        "## Key Ideas\n"
        "- Key idea one\n"
        "- Key idea two\n\n"
        "## How it Works\n"
        "Placeholder explanation of mechanics.\n\n"
        "## Connections\n"
        "- Related concept A\n\n"
        "## Sources\n"
        "- (mock)\n"
    )


# ── Public API ───────────────────────────────────────────────────────────────

def generate(prompt: str) -> str:
    """Send *prompt* to the configured LLM and return the text response.

    Raises:
        ValueError: if no API key is configured and mock mode is not active.
        openai.APIError / openai.APITimeoutError: propagated from the client.
    """
    from app.config import get as _cfg  # local import avoids circular deps

    cfg = _cfg()
    api_key = cfg.llm_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""

    if not api_key:
        raise ValueError(
            "No LLM API key found.  Set OPENAI_API_KEY in your environment or "
            "in config.toml under [llm] api_key."
        )

    if api_key.strip().lower() == _MOCK_KEY:
        LOGGER.debug("Mock LLM response triggered.")
        return _mock_response(prompt)

    # Real API call — import here so the module loads even without openai installed
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'openai' package is not installed.  Run: pip install openai"
        ) from exc

    client_kwargs: dict = {
        "api_key": api_key,
        "timeout": cfg.llm_timeout,
        "max_retries": cfg.llm_max_retries,
    }
    if cfg.llm_base_url:
        client_kwargs["base_url"] = cfg.llm_base_url

    client = OpenAI(**client_kwargs)

    LOGGER.info("Sending prompt to %s …", cfg.llm_model)

    response = client.chat.completions.create(
        model=cfg.llm_model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    LOGGER.info("Received response from LLM.")
    return content.strip() if content else ""
