from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from creative_scripting_mcp import server


class FileOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.script = self.root / "scripts" / "game.lua"
        self.script.parent.mkdir()
        self.original = b'print("before")\r\n'
        self.script.write_bytes(self.original)
        self.backup = self.script.with_name("game.lua.bak")
        self.backup.write_bytes(b"-- previous backup\n")

    def test_atomic_create_keeps_original_visible_until_replacement(self) -> None:
        replace = os.replace

        def inspect_replace(source, destination):
            self.assertEqual(self.script.read_bytes(), self.original)
            self.assertEqual(Path(source).read_bytes(), b'print("after")\n')
            _, sync_files = server._directory_sync_file_paths(str(self.root), "scripts/**/*.lua")
            self.assertEqual(sync_files, [self.script.resolve()])
            replace(source, destination)

        with patch.object(server.os, "replace", side_effect=inspect_replace):
            server.create_directory_script(str(self.root), "game.lua", 'print("after")')
        self.assertEqual(self.script.read_bytes(), b'print("after")\n')
        self.assertEqual(list(self.script.parent.glob("*.tmp")), [])

    def test_failed_replace_preserves_original_and_cleans_temporary_file(self) -> None:
        with patch.object(server.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaisesRegex(OSError, "disk error"):
                server.create_directory_script(str(self.root), "game.lua", "-- after")
        self.assertEqual(self.script.read_bytes(), self.original)
        self.assertEqual(list(self.script.parent.glob("*.tmp")), [])

    def test_rejected_edits_leave_script_and_backup_unchanged(self) -> None:
        for instructions in ("make it faster", "replace `missing` with `new`", "replace `` with `x`", "replace: => x"):
            with self.subTest(instructions=instructions):
                with self.assertRaises(server.BedWarsMcpError):
                    server.edit_directory_script(str(self.root), "game.lua", instructions)
                self.assertEqual(self.script.read_bytes(), self.original)
                self.assertEqual(self.backup.read_bytes(), b"-- previous backup\n")

    def test_failed_replace_cleans_readonly_temporary_file(self) -> None:
        self.script.chmod(stat.S_IREAD)
        try:
            with patch.object(server.os, "replace", side_effect=PermissionError("read-only destination")):
                with self.assertRaisesRegex(PermissionError, "read-only destination"):
                    server.create_directory_script(str(self.root), "game.lua", "-- after")
            self.assertEqual(self.script.read_bytes(), self.original)
            self.assertEqual(list(self.script.parent.glob("*.tmp")), [])
        finally:
            self.script.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_noop_edit_preserves_backup_and_file_timestamp(self) -> None:
        before = self.script.stat().st_mtime_ns
        result = server.edit_directory_script(str(self.root), "game.lua", "replace `before` with `before`")
        self.assertFalse(result["changed"])
        self.assertIsNone(result["backup"])
        self.assertEqual(result["diff"], "")
        self.assertEqual(self.script.stat().st_mtime_ns, before)
        self.assertEqual(self.backup.read_bytes(), b"-- previous backup\n")

    def test_successful_edit_backs_up_original_bytes(self) -> None:
        result = server.edit_directory_script(str(self.root), "game.lua", "  replace `before` with `after`  ")
        self.assertTrue(result["changed"])
        self.assertEqual(self.backup.read_bytes(), self.original)
        self.assertEqual(self.script.read_bytes(), b'print("after")\n')


if __name__ == "__main__":
    unittest.main()
