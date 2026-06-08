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
    def test_empty_directory_sync_uses_in_memory_delete_payload(self) -> None:
        def fake_post(sync_token: str, *, delivery_attempts: int = 2) -> dict[str, object]:
            return {
                "ok": True,
                "status_code": 201,
                "uploaded_files": [],
                "file_count": 0,
                "delete_all": True,
                "empty_basename_transport": True,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "scripts"
            scripts.mkdir()

            with patch.object(server, "_post_empty_sync", side_effect=fake_post):
                result = server._sync_directory_with_token(
                    "test-token",
                    str(root),
                    "scripts/**/*.lua",
                    allow_empty=True,
                )

            self.assertEqual(list(scripts.iterdir()), [])

        self.assertTrue(result["empty_sync_fallback"])
        self.assertTrue(result["delete_all"])
        self.assertEqual(result["uploaded_files"], [])
        self.assertIsNone(result["placeholder_file"])

    def test_delete_payload_uses_empty_lua_basename(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_post(url: str, **kwargs: object) -> FakeResponse:
            files = kwargs["files"]
            file_part = files[0]
            calls.append(
                {
                    "url": url,
                    "field": file_part[0],
                    "name": file_part[1][0],
                    "content": file_part[1][1].read(),
                    "content_type": file_part[1][2],
                }
            )
            return FakeResponse()

        with (
            patch.object(server.httpx, "post", side_effect=fake_post),
            patch.object(server.time, "sleep") as sleep,
        ):
            result = server._post_empty_sync("test-token")

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["field"], "files")
        self.assertEqual(calls[0]["name"], ".lua")
        self.assertEqual(calls[0]["content"], b"")
        self.assertEqual(calls[0]["content_type"], "text/x-lua")
        self.assertEqual(result["uploaded_files"], [])
        self.assertEqual(result["file_count"], 0)
        self.assertTrue(result["delete_all"])
        self.assertTrue(result["empty_basename_transport"])
        sleep.assert_called_once_with(0.35)

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
