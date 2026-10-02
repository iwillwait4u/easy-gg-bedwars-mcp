from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creative_scripting_mcp import server


class SyncPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name: str, content: str = "-- example\n") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_preview_matches_upload_names_and_does_not_mutate_or_upload(self) -> None:
        script = self.write("scripts/sub/game.lua", 'print("ok")\n')
        helper = self.write("scripts/main.lua", server.GENERATED_MAIN_CODE)
        self.write("drafts/draft.lua")
        self.write("scripts/.deleted/old.lua")
        before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch.object(server.httpx, "post") as post:
            result = server.preview_directory_sync(str(self.root))
        post.assert_not_called()
        self.assertTrue(result["ready_to_sync"])
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["files"][0]["upload_name"], "game.lua")
        self.assertEqual(result["files"][0]["sha256"], hashlib.sha256(script.read_bytes()).hexdigest())
        self.assertEqual(result["total_bytes"], script.stat().st_size)
        self.assertEqual(result["would_remove_generated_helpers"], ["scripts/main.lua"])
        self.assertTrue(helper.exists())
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        self.assertFalse(result["uploaded"])

    def test_duplicate_basenames_and_validation_errors_block_readiness(self) -> None:
        self.write("scripts/one/Game.lua", "if true then\n")
        self.write("scripts/two/game.lua")
        result = server.preview_directory_sync(str(self.root))
        self.assertFalse(result["transport_ready"])
        self.assertFalse(result["ready_to_sync"])
        self.assertEqual(result["duplicate_names"], ["Game.lua", "game.lua"])
        self.assertGreater(result["validation_error_count"], 0)

    def test_empty_preview_requires_explicit_delete_all(self) -> None:
        result = server.preview_directory_sync(str(self.root))
        self.assertFalse(result["ready_to_sync"])
        self.assertFalse(result["delete_all"])
        result = server.preview_directory_sync(str(self.root), allow_empty=True)
        self.assertTrue(result["ready_to_sync"])
        self.assertTrue(result["delete_all"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_preview_reports_existing_legacy_helper_cleanup_behavior(self) -> None:
        helper = self.write("scripts/main.lua", server.GENERATED_MAIN_CODE)
        result = server.preview_directory_sync(str(self.root))
        self.assertTrue(result["delete_all"])
        self.assertTrue(result["ready_to_sync"])
        self.assertTrue(helper.exists())

    def test_config_ignores_comments_and_strings_that_look_like_assignments(self) -> None:
        self.write("bwconfig.lua", '''-- syncGlob = "wrong/**/*.lua"
--[[ syncGlob = "also-wrong/**/*.lua" ]]
local example = "syncGlob = 'fake/**/*.lua'"
return { syncGlob = -- real configuration
    "custom/**/*.lua" }
''')
        self.write("custom/game.lua")
        self.write("scripts/ignored.lua")
        result = server.preview_directory_sync(str(self.root))
        self.assertEqual(result["glob_pattern"], "custom/**/*.lua")
        self.assertEqual([record["file_name"] for record in result["files"]], ["custom/game.lua"])

    def test_invalid_utf8_is_reported_per_file(self) -> None:
        invalid = self.write("scripts/invalid.lua")
        invalid.write_bytes(b"\xff")
        self.write("scripts/valid.lua")
        result = server.preview_directory_sync(str(self.root))
        self.assertFalse(result["ready_to_sync"])
        self.assertEqual(result["file_count"], 2)
        self.assertEqual(result["validation_error_count"], 1)
        self.assertTrue(result["transport_ready"])

    def test_validation_can_be_skipped_without_loading_docs(self) -> None:
        self.write("scripts/game.lua", "if true then\n")
        with patch.object(server, "_load_docs_cache") as load:
            result = server.preview_directory_sync(str(self.root), validate=False)
        load.assert_not_called()
        self.assertFalse(result["validation_performed"])
        self.assertTrue(result["transport_ready"])
        self.assertNotIn("validation", result["files"][0])

    def test_directory_validation_loads_docs_once_for_all_scripts(self) -> None:
        self.write("scripts/one.lua")
        self.write("scripts/two.lua")
        with patch.object(server, "_load_docs_cache", wraps=server._load_docs_cache) as load:
            result = server.validate_directory_project(str(self.root))
        load.assert_called_once()
        self.assertEqual(result["file_count"], 2)

    def test_external_symlinks_are_excluded_from_validation_and_helper_cleanup(self) -> None:
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        external = Path(outside.name) / "external.lua"
        external.write_text(server.GENERATED_MAIN_CODE, encoding="utf-8")
        scripts = self.root / "scripts"
        scripts.mkdir()
        link = scripts / "main.lua"
        try:
            link.symlink_to(external)
        except OSError as exc:
            self.skipTest(f"Creating symlinks is unavailable: {exc}")
        self.assertEqual(server._remove_generated_sync_helpers(self.root), [])
        self.assertTrue(link.exists())
        self.assertTrue(external.exists())
        self.assertEqual(server.validate_directory_project(str(self.root))["file_count"], 0)
        self.assertEqual(server.preview_directory_sync(str(self.root))["file_count"], 0)


if __name__ == "__main__":
    unittest.main()
