from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.file_utils import write_text
from scripts.validate_vault import validate


class ValidateVaultTests(unittest.TestCase):
    def test_validate_flags_broken_wikilinks(self) -> None:
        body = (
            "# Nodo de prueba\n\n"
            "Este nodo tiene contenido suficiente para superar el umbral mínimo. "
            "Repite una explicación sustancial sobre atención, memoria externa, "
            "creatividad, criterio, fuentes y vínculos para simular una nota real. "
            "La intención es probar que el validador detecta enlaces inexistentes "
            "sin depender de llamadas a modelos ni de un vault real. " * 2
            + "\n\n[[Nodo inexistente]]\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_text(vault / "conceptos" / "nodo.md", body)
            write_text(
                vault / ".obsidian" / "graph.json",
                json.dumps(
                    {
                        "search": " ".join(
                            f"-path:{name}"
                            for name in (
                                "inicio.md",
                                "capturas.md",
                                "indice_de_temas.md",
                                "indice_de_fuentes.md",
                                "resumen_de_insights.md",
                                "preguntas_abiertas.md",
                            )
                        ),
                        "colorGroups": [
                            {"query": "path:conceptos/"},
                            {"query": "path:autores/"},
                            {"query": "path:libros/"},
                            {"query": "path:tecnologias/"},
                            {"query": "path:tensiones/"},
                        ],
                    }
                ),
            )

            output = StringIO()
            with redirect_stdout(output):
                code = validate(vault)

        self.assertEqual(code, 1)
        self.assertIn("BROKEN WIKILINKS", output.getvalue())


if __name__ == "__main__":
    unittest.main()
