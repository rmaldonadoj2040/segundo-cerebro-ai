from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.file_utils import write_text
from app.retriever import retrieve


class RetrieverTests(unittest.TestCase):
    def test_retrieve_excludes_dashboard_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_text(vault / "Inicio.md", "# Inicio\n\ncreatividad creatividad creatividad")
            write_text(
                vault / "conceptos" / "creatividad.md",
                "# Creatividad\n\nLa creatividad asistida por IA requiere criterio.",
            )

            results = retrieve("creatividad IA", vault)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].name, "creatividad.md")


if __name__ == "__main__":
    unittest.main()
