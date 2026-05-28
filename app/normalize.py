"""Raw capture normalization step. Translates to Spanish and extracts initial structure."""

from __future__ import annotations

import logging
import datetime
from pathlib import Path

from app.config import get as _cfg
from app.llm_client import generate

LOGGER = logging.getLogger(__name__)

def normalize_to_spanish(content: str, filename: str) -> str | None:
    """Detect if content is English/mixed and normalize into clean Spanish.
    Returns normalized markdown content with frontmatter.
    """
    prompt = (
        "Eres un sistema de gestión de conocimiento personal 'Spanish-first'. "
        "Se te proporcionará una nota cruda, texto, transcripción o enlace capturado. "
        "Tu tarea es normalizar este contenido al ESPAÑOL, preservando significado, terminología importante y referencias (URLs). "
        "Si ya está en español, límpialo ligeramente sin sobreescribir mucho. "
        "Si es inglés o mixto, tradúcelo y sintetízalo al español. "
        "NO es una traducción literal, es una nota estructurada.\n\n"
        "Debes devolver el contenido EXACTAMENTE con esta estructura (incluyendo frontmatter YAML):\n\n"
        "---\n"
        "type: captura_normalizada\n"
        "idioma_original: spanish | english | mixed | unknown  (deduce cuál)\n"
        f"fecha: {datetime.date.today().isoformat()}\n"
        f"source_file: {filename}\n"
        "status: processed\n"
        "---\n\n"
        "# [Título humano en español]\n\n"
        "## Resumen\n"
        "[...]\n\n"
        "## Ideas importantes\n"
        "- [...]\n\n"
        "## Fragmentos útiles\n"
        "- [...]\n\n"
        "## Posibles conexiones\n"
        "- [[...]]\n\n"
        "## Preguntas que abre\n"
        "- ¿[...]?\n\n"
        "## Fuente original\n"
        f"- {filename}\n"
        "- [URLs encontradas]\n\n"
        "Contenido crudo a procesar:\n"
        "---------------------------\n"
        f"{content}\n"
    )

    try:
        response = generate(prompt)
        return response
    except Exception as exc:
        LOGGER.error("Failed to normalize content %s: %s", filename, exc)
        return None
