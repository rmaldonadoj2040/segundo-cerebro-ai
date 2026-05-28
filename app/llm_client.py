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
import re

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


def _extract_raw_section(prompt: str) -> str:
    marker = "Contenido crudo a procesar:"
    if marker in prompt:
        return prompt.split(marker, 1)[1]
    return prompt


def _extract_sources(prompt: str) -> list[str]:
    sources = re.findall(r"--- Source: ([^\n]+) ---", prompt)
    if sources:
        return sources
    from_frontmatter = re.findall(r"source_file:\s*([^\n]+)", prompt)
    return list(dict.fromkeys(from_frontmatter))


def _mock_domain(prompt_lower: str) -> str:
    if any(token in prompt_lower for token in ("creativity", "originality", "creatividad")):
        return "creativity"
    if any(token in prompt_lower for token in ("burnout", "agotamiento", "productividad")):
        return "productivity"
    if any(token in prompt_lower for token in ("aprendizaje", "attention", "atención", "concentración")):
        return "learning"
    return "general"


def _mock_response(prompt: str) -> str:
    """Return a deterministic stub response for mock mode.

    Concept extraction prompts return 1-3 concept names.
    Compilation prompts return a templated wiki page (Spanish).
    All other prompts get a generic response.
    """
    prompt_lower = prompt.lower()
    domain = _mock_domain(prompt_lower)

    if (
        "extrae una ontología de 5 tipos" in prompt_lower
        and "## conceptos" in prompt_lower
        and "## hubs" in prompt_lower
    ):
        return (
            "## CONCEPTOS\n"
            "- Mente extendida\n"
            "- Memoria externa\n"
            "- Economía de la atención\n"
            "- Trabajo profundo\n"
            "- Fragmentación atencional\n"
            "- Creatividad asistida por IA\n"
            "- Originalidad\n"
            "- Dependencia cognitiva\n"
            "- Sobrecarga informativa\n"
            "- Curaduría personal\n\n"
            "## AUTORES\n"
            "- Andy Clark\n"
            "- Herbert Simon\n"
            "- Nicholas Carr\n"
            "- Cal Newport\n"
            "- Marshall McLuhan\n\n"
            "## LIBROS\n"
            "- The Shallows\n"
            "- Deep Work\n"
            "- La mente extendida\n"
            "- Zettelkasten\n\n"
            "## TECNOLOGIAS\n"
            "- Obsidian\n"
            "- Google\n"
            "- TikTok\n"
            "- Algoritmos de recomendación\n\n"
            "## TENSIONES\n"
            "- Velocidad vs Profundidad\n"
            "- Automatización vs Autonomía\n"
            "- Información vs Conocimiento\n"
            "- Productividad vs Bienestar\n\n"
            "## HUBS\n"
            "- Mente extendida\n"
            "- Economía de la atención\n"
            "- Creatividad asistida por IA\n"
        )

    if "type: captura_normalizada" in prompt and "contenido crudo a procesar" in prompt_lower:
        raw_text = _extract_raw_section(prompt)
        if domain == "creativity":
            return (
                "---\n"
                "type: captura_normalizada\n"
                "idioma_original: english\n"
                "fecha: 2026-05-15\n"
                "source_file: test-english.md\n"
                "status: processed\n"
                "---\n\n"
                "# IA, creatividad y originalidad\n\n"
                "## Resumen\n"
                "La captura plantea que la IA acelera la producción creativa, pero también puede empujar a los creadores hacia plantillas y atajos.\n\n"
                "## Ideas importantes\n"
                "- La automatización reduce fricción creativa.\n"
                "- La velocidad puede desplazar la originalidad.\n"
                "- La tensión central es velocidad vs originalidad.\n\n"
                "## Fragmentos útiles\n"
                "- Las herramientas de IA pueden hacer que los creadores dependan de sugerencias automáticas.\n\n"
                "## Posibles conexiones\n"
                "- [[Creatividad asistida por IA]]\n"
                "- [[Originalidad]]\n\n"
                "## Preguntas que abre\n"
                "- ¿La automatización amplía la creatividad o la estandariza?\n\n"
                "## Fuente original\n"
                "- test-english.md\n"
            )
        if domain == "productivity":
            return (
                "---\n"
                "type: captura_normalizada\n"
                "idioma_original: mixed\n"
                "fecha: 2026-05-15\n"
                "source_file: test-mixto.md\n"
                "status: processed\n"
                "---\n\n"
                "# Productividad, herramientas y agotamiento\n\n"
                "## Resumen\n"
                "La captura sostiene que muchas herramientas de productividad prometen ahorrar tiempo, pero en la práctica añaden notificaciones, presión y trabajo de coordinación.\n\n"
                "## Ideas importantes\n"
                "- La productividad digital puede convertirse en carga operativa.\n"
                "- Más herramientas no siempre equivalen a más claridad.\n"
                "- La tensión central es productividad vs bienestar.\n\n"
                "## Fragmentos útiles\n"
                "- La productividad moderna puede convertirse en una forma elegante de agotamiento.\n\n"
                "## Posibles conexiones\n"
                "- [[Productividad digital]]\n"
                "- [[Agotamiento]]\n\n"
                "## Preguntas que abre\n"
                "- ¿Cuándo una herramienta deja de ahorrar tiempo y empieza a consumirlo?\n\n"
                "## Fuente original\n"
                "- test-mixto.md\n"
            )
        if domain == "learning":
            return (
                "---\n"
                "type: captura_normalizada\n"
                "idioma_original: spanish\n"
                "fecha: 2026-05-15\n"
                "source_file: test-espanol.md\n"
                "status: processed\n"
                "---\n\n"
                "# IA, aprendizaje y atención\n\n"
                "## Resumen\n"
                "La captura explora cómo la IA acelera el aprendizaje, pero también puede fomentar dependencia cognitiva y empeorar la fragmentación de la atención.\n\n"
                "## Ideas importantes\n"
                "- La IA acelera el acceso a información.\n"
                "- La inmediatez puede reducir el esfuerzo mental.\n"
                "- La combinación de IA y redes sociales afecta la concentración profunda.\n\n"
                "## Fragmentos útiles\n"
                "- La tecnología puede hacernos pensar más rápido sin ayudarnos a pensar mejor.\n\n"
                "## Posibles conexiones\n"
                "- [[Aprendizaje asistido por IA]]\n"
                "- [[Atención fragmentada]]\n\n"
                "## Preguntas que abre\n"
                "- ¿La tecnología nos ayuda a pensar mejor o solo a pensar más rápido?\n\n"
                "## Fuente original\n"
                "- test-espanol.md\n"
            )
        return (
            "---\n"
            "type: captura_normalizada\n"
            "idioma_original: unknown\n"
            "fecha: 2026-05-15\n"
            "source_file: captura.md\n"
            "status: processed\n"
            "---\n\n"
            "# Captura normalizada\n\n"
            "## Resumen\n"
            "Contenido normalizado en español.\n\n"
            "## Ideas importantes\n"
            "- Idea principal resumida.\n\n"
            "## Fragmentos útiles\n"
            "- Fragmento relevante.\n\n"
            "## Posibles conexiones\n"
            "- [[Concepto relacionado]]\n\n"
            "## Preguntas que abre\n"
            "- ¿Qué conviene explorar ahora?\n\n"
            "## Fuente original\n"
            "- captura.md\n"
        )

    # Concept extraction prompt (Extract N distinct concept names)
    if "extract" in prompt_lower and "distinct" in prompt_lower and "concept" in prompt_lower:
        if domain == "creativity":
            return "Creatividad asistida por IA\nOriginalidad\nAutomatización creativa"
        if domain == "productivity":
            return "Productividad digital\nAgotamiento\nSobrecarga de notificaciones"
        if domain == "learning":
            return "Aprendizaje asistido por IA\nAtención fragmentada\nDependencia cognitiva"
        return "Conocimiento práctico\nTensión central\nPregunta abierta"

    # Topic assignment prompt (expects just a label back)
    if "single most specific" in prompt_lower and "topic" in prompt_lower:
        for kw, label in _MOCK_TOPIC_KEYWORDS.items():
            if kw in prompt_lower:
                return label
        return "Concepto General"

    if "compila una nota de" in prompt_lower and "entidad:" in prompt_lower:
        topic_match = re.search(r"Entidad:\s*(.+)", prompt)
        topic = topic_match.group(1).strip() if topic_match else "Concepto de Prueba"
        sources = _extract_sources(prompt) or ["captura.md"]
        source_lines = "\n".join(f"- {source}" for source in sources)
        return (
            f"# {topic}\n\n"
            "## Qué significa\n"
            f"{topic} nombra una relación importante entre herramientas, atención y criterio. "
            "En las fuentes aparece como una forma de entender cómo los sistemas digitales "
            "pueden ampliar la memoria, acelerar la producción y, al mismo tiempo, cambiar "
            "los hábitos con los que pensamos. No es solo una etiqueta temática: funciona "
            "como un punto de lectura para observar qué delegamos, qué conservamos y qué "
            "tipo de fricción sigue siendo necesaria.\n\n"
            "La idea central es que una tecnología cognitiva nunca es neutral. Cuando una "
            "nota, un motor de búsqueda, una herramienta de IA o un grafo de conocimiento "
            "entra en el flujo de trabajo, también reorganiza la atención. Puede volver "
            "más visible una conexión que estaba dispersa, pero puede esconder el esfuerzo "
            "que hacía valiosa esa conexión.\n\n"
            "## Por qué importa\n"
            "Importa porque el proyecto no busca acumular archivos, sino producir un mapa "
            "navegable que ayude a pensar mejor. La utilidad de un segundo cerebro depende "
            "de la calidad de sus relaciones: si todo se enlaza con todo, el mapa pierde "
            "criterio; si nada se conecta, el archivo queda muerto.\n\n"
            "También importa porque la IA introduce una tensión práctica. Puede reducir la "
            "fricción de resumir y ordenar, pero el usuario todavía debe decidir qué merece "
            "ser preservado, qué debe vincularse y qué pregunta queda abierta.\n\n"
            "## Conexiones\n"
            "- [[Mente extendida]]\n"
            "- [[Economía de la atención]]\n"
            "- [[Creatividad asistida por IA]]\n\n"
            "## Insight clave\n"
            "La automatización más útil no elimina el pensamiento: elimina ruido para que "
            "el pensamiento pueda volverse más deliberado. El riesgo aparece cuando la "
            "comodidad sustituye el criterio que debía fortalecer.\n\n"
            "## Pregunta abierta\n"
            "¿Cómo diseñar un sistema que ayude a conectar ideas sin convertir cada conexión "
            "en una asociación automática y superficial?\n\n"
            "## Fuentes\n"
            f"{source_lines}\n"
        )

    if "tensiones" in prompt_lower:
        if domain == "creativity":
            return (
                "Velocidad vs Originalidad - Crear más rápido puede empobrecer la voz propia.\n"
                "Automatización vs Criterio - Delegar demasiadas decisiones debilita la intención autoral."
            )
        if domain == "productivity":
            return (
                "Productividad vs Bienestar - Más herramientas pueden producir más presión que alivio.\n"
                "Eficiencia vs Atención - Optimizar cada minuto puede fragmentar el trabajo profundo."
            )
        if domain == "learning":
            return (
                "Rapidez vs Pensamiento - Obtener respuestas inmediatas puede reducir la reflexión.\n"
                "Aprendizaje vs Autonomía - La ayuda constante puede erosionar la autonomía intelectual."
            )
        return "Comodidad vs Comprensión - Resolver rápido no siempre implica entender mejor."

    if "insights" in prompt_lower:
        if domain == "creativity":
            return (
                "Voz Estética - La creatividad asistida por IA acelera la producción, pero puede volver intercambiables las decisiones estéticas.\n"
                "Riesgo de Edición - Cuando la herramienta propone demasiado, el creador corre el riesgo de editar en vez de imaginar."
            )
        if domain == "productivity":
            return (
                "Redistribución del Trabajo - Muchas herramientas de productividad no ahorran trabajo: lo redistribuyen en coordinación.\n"
                "Obsesión de Optimización - La obsesión por optimizar el tiempo puede convertirse en agotamiento socialmente aceptable."
            )
        if domain == "learning":
            return (
                "Atajo de Criterio - La IA puede acortar el camino hacia una respuesta sin acercarnos al esfuerzo cognitivo.\n"
                "Atención Sostenida - El verdadero riesgo no es acceder rápido a información, sino dejar de ejercitar la atención."
            )
        return "Conveniencia vs Esfuerzo - La conveniencia tecnológica suele desplazar el esfuerzo cognitivo, no eliminarlo."

    if "preguntas" in prompt_lower:
        if domain == "creativity":
            return (
                "Automatización Creativa - ¿Qué parte de la creatividad conviene automatizar y cuál debe seguir siendo artesanal?\n"
                "Voz Singular - ¿Cómo preservar una voz propia cuando las herramientas sugieren patrones similares?\n"
                "Originalidad Técnica - ¿La velocidad de producción está degradando la originalidad percibida?"
            )
        if domain == "productivity":
            return (
                "Costo de Herramientas - ¿Cuándo una herramienta de productividad deja de ahorrar tiempo y empieza a consumirlo?\n"
                "Límite de Eficiencia - ¿Qué señales muestran que la eficiencia ya está dañando el bienestar?\n"
                "Clasificación de Productividad - ¿Cómo distinguir productividad real de hiperactividad organizada?"
            )
        if domain == "learning":
            return (
                "Autonomía Intelectual - ¿Cómo usar IA para aprender sin debilitar la autonomía intelectual?\n"
                "Foco Profundo - ¿Qué prácticas protegen la concentración profunda en entornos saturados de respuestas rápidas?\n"
                "Comprensión Genuina - ¿Cómo diferenciar comprensión genuina de simple velocidad de acceso?"
            )
        return "Pregunta Sostenida - ¿Qué pregunta valdría la pena sostener sin apresurar una respuesta?"

    if "generate 3 pieces of content about" in prompt_lower:
        return (
            "## Reel\n"
            "- Hook: La IA te ahorra tiempo, pero puede cobrarte atención.\n"
            "- Insight: Cuanto más inmediata es la respuesta, menos entrenamos criterio.\n"
            "- Tensión: velocidad vs profundidad.\n"
            "- Cierre: usa la IA para avanzar, no para dejar de pensar.\n\n"
            "## Carrusel\n"
            "1. La promesa: producir más rápido.\n"
            "2. El costo oculto: dependencia cognitiva.\n"
            "3. La pregunta: ¿ganas eficiencia o pierdes criterio?\n\n"
            "## Idea utilizable\n"
            "- Comparar una tarea hecha con respuesta instantánea vs una tarea con reflexión guiada."
        )

    if "compila los textos proporcionados en una nota estructurada" in prompt_lower:
        topic_match = re.search(r"Topic:\s*(.+)", prompt)
        topic = topic_match.group(1).strip() if topic_match else "Concepto de Prueba"
        sources = _extract_sources(prompt) or ["captura.md"]
        source_lines = "\n".join(f"- {source}" for source in sources)
        if domain == "creativity":
            links = "- [[Originalidad]]\n- [[Fricción creativa]]"
        elif domain == "productivity":
            links = "- [[Zettelkasten]]\n- [[Cognitive offloading]]"
        elif domain == "learning":
            links = "- [[Atención fragmentada]]\n- [[Mente extendida]]"
        else:
            links = "- [[Concepto relacionado]]"

        return (
            f"# {topic}\n\n"
            "## Qué significa\n"
            f"{topic} es un concepto clave que emerge de las fuentes proporcionadas. En esencia, se refiere a la dinámica central en la cual las herramientas tecnológicas alteran la forma en que interactuamos con la información y la creación.\n\n"
            "A diferencia de un entendimiento superficial, esto implica que las herramientas no son solo extensiones pasivas, sino agentes que moldean nuestras expectativas y procesos. Modificar este equilibrio requiere consciencia y decisiones deliberadas sobre cómo delegamos nuestro esfuerzo cognitivo.\n\n"
            "## Por qué importa\n"
            "Este concepto es fundamental porque define la línea entre utilizar la tecnología como un multiplicador de capacidades y convertirla en un sustituto de nuestro propio criterio. Comprender esta distinción nos permite diseñar mejores procesos de trabajo y aprendizaje.\n\n"
            "## Conexiones\n"
            f"{links}\n\n"
            "## Insight clave\n"
            "El mayor riesgo de delegar tareas cognitivas no es la pérdida de habilidades, sino la erosión de nuestra capacidad para tolerar la fricción que antecede a las buenas ideas.\n\n"
            "## Pregunta abierta\n"
            "¿Cómo podemos diseñar sistemas que nos asistan en la ejecución técnica sin robarnos la fricción necesaria para el pensamiento original?\n\n"
            "## Fuentes\n"
            f"{source_lines}\n"
        )

    if (
        "patterns across files" in prompt_lower
        or "question:" in prompt_lower
        or ("pregunta:" in prompt_lower and "contexto:" in prompt_lower)
    ):
        return (
            "## Patrones entre archivos\n"
            "Los archivos comparados apuntan a una misma tensión entre conveniencia y criterio.\n\n"
            "## Contradicciones / Tensiones\n"
            "Algunas capturas celebran la velocidad; otras subrayan el costo cognitivo de depender de ella.\n\n"
            "## Diferencias clave entre fuentes\n"
            "Cambian el foco: aprendizaje, creatividad y productividad muestran el mismo patrón desde contextos distintos.\n\n"
            "## Qué falta o está poco desarrollado\n"
            "Faltan ejemplos longitudinales sobre hábitos sostenidos y efectos a largo plazo.\n\n"
            "## Conclusión\n"
            "La IA aporta fricción baja, pero exige más disciplina humana para sostener profundidad."
        )

    # Generic fallback response — still Spanish and structurally valid.
    return (
        "# Concepto de Prueba\n\n"
        "## Idea central\n"
        "Una definición de marcador de posición generada en modo mock.\n\n"
        "## Por qué importa\n"
        "Este concepto es importante porque demuestra la funcionalidad del sistema.\n\n"
        "## Cómo funciona\n"
        "Explicación de marcador de posición de los mecanismos involucrados.\n\n"
        "## Insights no obvios\n"
        "- Insight sorprendente uno\n"
        "- Insight sorprendente dos\n\n"
        "## Tensiones relacionadas\n"
        "- [[Comodidad vs Comprensión]]\n\n"
        "## Conexiones con otros conceptos\n"
        "- [[Concepto relacionado]]\n\n"
        "## Fuentes\n"
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
