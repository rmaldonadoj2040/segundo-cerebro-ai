from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import get


class ConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        get.cache_clear()

    def test_path_overrides_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            captures = Path(tmp) / "captures"
            vault = Path(tmp) / "vault"
            with patch.dict(
                os.environ,
                {
                    "LLMKS_CAPTURES_DIR": str(captures),
                    "LLMKS_KNOWLEDGE_MAP_DIR": str(vault),
                    "OPENAI_API_KEY": "mock",
                },
                clear=False,
            ):
                get.cache_clear()
                cfg = get()

        self.assertEqual(cfg.captures_dir, captures)
        self.assertEqual(cfg.knowledge_map_dir, vault)
        self.assertEqual(cfg.llm_api_key, "mock")


if __name__ == "__main__":
    unittest.main()
