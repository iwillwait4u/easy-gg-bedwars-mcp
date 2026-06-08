from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative_scripting_mcp import server


class FandomCacheTests(unittest.TestCase):
    def test_status_search_and_read_cached_fandom_pages(self) -> None:
        original_cache_dir = server.FANDOM_CACHE_DIR
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            (cache_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "source": "Roblox BedWars Wiki on Fandom",
                        "page_count": 2,
                        "include_text": True,
                    }
                ),
                encoding="utf-8",
            )
            (cache_dir / "pages.json").write_text(
                json.dumps(
                    [
                        {
                            "title": "Commands",
                            "url": "https://robloxbedwars.fandom.com/wiki/Commands",
                            "summary": "Commands can be used in custom matches.",
                            "extract": "Commands can be used in custom matches. /spawn gives items.",
                            "categories": ["Gameplay", "UI"],
                            "length": 100,
                            "lastrevid": 1,
                        },
                        {
                            "title": "Kaida",
                            "url": "https://robloxbedwars.fandom.com/wiki/Kaida",
                            "summary": "A kit page.",
                            "extract": "A kit page.",
                            "categories": ["Kits"],
                            "length": 50,
                            "lastrevid": 2,
                        },
                    ]
                ),
                encoding="utf-8",
            )
            server.FANDOM_CACHE_DIR = cache_dir
            try:
                status = server.fandom_cache_status()
                search = server.search_fandom_cache("spawn", include_text=True)
                page = server.read_fandom_page("commands", include_text=True)
            finally:
                server.FANDOM_CACHE_DIR = original_cache_dir

        self.assertTrue(status["available"])
        self.assertEqual(status["page_count"], 2)
        self.assertEqual(search["results"][0]["title"], "Commands")
        self.assertTrue(page["found"])
        self.assertIn("/spawn", page["extract"])


if __name__ == "__main__":
    unittest.main()
