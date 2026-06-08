from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creative_scripting_mcp import server


class FakeResponse:
    status_code = 201
    text = "6"

    def json(self) -> int:
        return 6


class SyncTransportTests(unittest.TestCase):
    def test_empty_directory_sync_uses_comment_only_placeholder(self) -> None:
        captured_paths: list[Path] = []

        def fake_post(
            sync_token: str,
            paths: list[Path],
            *,
            upload_root: Path,
            allow_empty: bool = False,
            delivery_attempts: int = 2,
        ) -> dict[str, object]:
            captured_paths.extend(paths)
            return {
                "ok": True,
                "status_code": 201,
                "uploaded_files": [path.name for path in paths],
                "file_count": len(paths),
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scripts").mkdir()

            with patch.object(server, "_post_sync_files", side_effect=fake_post):
                result = server._sync_directory_with_token(
                    "test-token",
                    str(root),
                    "scripts/**/*.lua",
                    allow_empty=True,
                )

            placeholder = root / "scripts" / "main.lua"
            self.assertTrue(placeholder.exists())
            self.assertEqual(placeholder.read_text(encoding="utf-8"), server.EMPTY_SYNC_PLACEHOLDER_CODE)

        self.assertEqual([path.name for path in captured_paths], ["main.lua"])
        self.assertTrue(result["empty_sync_fallback"])
        self.assertEqual(result["placeholder_file"], "scripts/main.lua")

    def test_real_script_removes_generated_empty_placeholder(self) -> None:
        captured_names: list[str] = []

        def fake_post(
            sync_token: str,
            paths: list[Path],
            *,
            upload_root: Path,
            allow_empty: bool = False,
            delivery_attempts: int = 2,
        ) -> dict[str, object]:
            captured_names.extend(path.name for path in paths)
            return {
                "ok": True,
                "status_code": 201,
                "uploaded_files": [path.name for path in paths],
                "file_count": len(paths),
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()
            placeholder = scripts / "main.lua"
            placeholder.write_text(server.EMPTY_SYNC_PLACEHOLDER_CODE, encoding="utf-8")
            (scripts / "game.lua").write_text('print("active")\n', encoding="utf-8")

            with patch.object(server, "_post_sync_files", side_effect=fake_post):
                result = server._sync_directory_with_token(
                    "test-token",
                    str(root),
                    "scripts/**/*.lua",
                )

            self.assertFalse(placeholder.exists())

        self.assertEqual(captured_names, ["game.lua"])
        self.assertFalse(result["empty_sync_fallback"])

    def test_upload_matches_extension_metadata_and_confirms_delivery(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, **kwargs: object) -> FakeResponse:
            calls.append({"url": url, **kwargs})
            return FakeResponse()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "main.lua"
            script.write_text('print("ok")\n', encoding="utf-8")

            with (
                patch.object(server.httpx, "post", side_effect=fake_post),
                patch.object(server.time, "sleep") as sleep,
            ):
                result = server._post_sync_files(
                    "test-token",
                    [script],
                    upload_root=root,
                )

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["attempt_status_codes"], [201, 201])
        self.assertEqual(result["server_response"], 6)
        self.assertTrue(result["extension_compatible_transport"])
        sleep.assert_called_once_with(0.35)

        files = calls[0]["files"]
        self.assertIsInstance(files, list)
        file_part = files[0]
        self.assertEqual(file_part[0], "files")
        self.assertEqual(file_part[1][0], "main.lua")
        self.assertEqual(file_part[1][2], "text/x-lua")
        self.assertEqual(
            calls[0]["headers"],
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, compress, deflate, br",
                "User-Agent": "axios/1.5.0",
            },
        )

    def test_duplicate_basenames_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "one" / "main.lua"
            second = root / "two" / "main.lua"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_text("-- one\n", encoding="utf-8")
            second.write_text("-- two\n", encoding="utf-8")

            with self.assertRaisesRegex(server.BedWarsMcpError, "duplicate files"):
                server._post_sync_files(
                    "test-token",
                    [first, second],
                    upload_root=root,
                )


if __name__ == "__main__":
    unittest.main()
