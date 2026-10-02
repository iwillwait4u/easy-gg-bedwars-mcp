from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from creative_scripting_mcp import server


class SyncWatchTests(unittest.TestCase):
    def setUp(self) -> None:
        server.disconnect_sync()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "scripts").mkdir()
        self.script = self.root / "scripts" / "game.lua"
        self.script.write_text('-- initial\n', encoding="utf-8")
        transport = patch.object(server, "_post_sync_files", side_effect=self.accept_upload)
        self.post = transport.start()
        self.addCleanup(transport.stop)
        self.addCleanup(server.disconnect_sync)

    @staticmethod
    def accept_upload(token: str, paths: list[Path], **kwargs: object) -> dict[str, object]:
        return {
            "ok": True, "status_code": 201,
            "uploaded_files": [path.name for path in paths], "file_count": len(paths),
        }

    def connect(self, *, watch: bool = False) -> dict[str, object]:
        return server.connect_sync("test-token", str(self.root), watch=watch)

    def wait_until(self, condition, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while not condition():
            if time.monotonic() >= deadline:
                self.fail("Timed out waiting for watcher state.")
            threading.Event().wait(0.005)

    def test_edit_before_first_poll_is_uploaded(self) -> None:
        self.connect()
        self.script.write_text('-- edited before the first poll\n', encoding="utf-8")
        server._start_sync_watcher(poll_seconds=0.01, debounce_seconds=0.02)
        self.wait_until(lambda: server.sync_status()["last_auto_sync_at"] is not None)
        self.assertEqual(self.post.call_count, 2)

    def test_http_failure_retries_unchanged_files_and_preserves_error(self) -> None:
        self.connect()
        retry_started = threading.Event()
        release_retry = threading.Event()
        self.addCleanup(release_retry.set)
        attempts = 0

        def upload(token, paths, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return {"ok": False, "status_code": 503, "warning": "Service unavailable"}
            retry_started.set()
            if not release_retry.wait(2.0):
                raise RuntimeError("Test retry was not released.")
            return self.accept_upload(token, paths, **kwargs)

        self.post.side_effect = upload
        server._start_sync_watcher(poll_seconds=0.01, debounce_seconds=0.02)
        self.script.write_text('-- retry this change\n', encoding="utf-8")
        self.assertTrue(retry_started.wait(2.0))
        status = server.sync_status()
        self.assertEqual(status["last_status_code"], 503)
        self.assertEqual(status["last_error"], "Service unavailable")
        self.assertIsNone(status["last_auto_sync_at"])
        release_retry.set()
        self.wait_until(lambda: server.sync_status()["last_auto_sync_at"] is not None)
        self.assertIsNone(server.sync_status()["last_error"])

    def test_disconnect_during_upload_does_not_restore_session(self) -> None:
        self.connect()
        started = threading.Event()
        release = threading.Event()
        results = []

        def upload(token, paths, **kwargs):
            started.set()
            if not release.wait(2.0):
                raise RuntimeError("Test upload was not released.")
            return self.accept_upload(token, paths, **kwargs)

        self.post.side_effect = upload
        worker = threading.Thread(target=lambda: results.append(server.sync_connected()))
        worker.start()
        try:
            self.assertTrue(started.wait(2.0))
            server.disconnect_sync()
        finally:
            release.set()
            worker.join(2.0)
        self.assertFalse(worker.is_alive())
        self.assertFalse(server.sync_status()["connected"])
        self.assertFalse(server.sync_status()["token_stored_in_memory_only"])
        self.assertTrue(results[0]["ok"])
        self.assertFalse(results[0]["connected"])

    def test_disconnect_invalidates_pending_initial_connection(self) -> None:
        started = threading.Event()
        release = threading.Event()
        results = []

        def upload(token, paths, **kwargs):
            started.set()
            if not release.wait(2.0):
                raise RuntimeError("Test upload was not released.")
            return self.accept_upload(token, paths, **kwargs)

        self.post.side_effect = upload
        worker = threading.Thread(target=lambda: results.append(self.connect(watch=True)))
        worker.start()
        try:
            self.assertTrue(started.wait(2.0))
            server.disconnect_sync()
        finally:
            release.set()
            worker.join(2.0)
        self.assertFalse(worker.is_alive())
        self.assertFalse(results[0]["connected"])
        self.assertFalse(server.sync_status()["watcher_running"])

    def test_reconnect_with_watch_false_stops_existing_watcher(self) -> None:
        self.connect(watch=True)
        old_thread = server.SYNC_WATCHER_THREAD
        result = self.connect(watch=False)
        self.assertTrue(result["connected"])
        self.assertFalse(result["watcher_running"])
        self.assertFalse(old_thread.is_alive())

    def test_restarted_watcher_keeps_its_own_stop_event(self) -> None:
        self.connect()
        server._start_sync_watcher(poll_seconds=0.01, debounce_seconds=0.02)
        old_thread = server.SYNC_WATCHER_THREAD
        old_stop = server.SYNC_WATCHER_STOP
        old_stop.set()
        server._start_sync_watcher(poll_seconds=0.01, debounce_seconds=0.02)
        new_thread = server.SYNC_WATCHER_THREAD
        self.assertIsNot(new_thread, old_thread)
        old_thread.join(2.0)
        self.assertFalse(old_thread.is_alive())
        self.assertTrue(new_thread.is_alive())
        self.assertTrue(server.sync_status()["watcher_running"])

    def test_repeated_saves_wait_for_quiet_period(self) -> None:
        self.connect()
        uploaded = threading.Event()

        def upload(token, paths, **kwargs):
            uploaded.set()
            return self.accept_upload(token, paths, **kwargs)

        self.post.side_effect = upload
        server._start_sync_watcher(poll_seconds=0.01, debounce_seconds=0.10)
        for count in range(5):
            self.script.write_text(f'-- edit {count}\n', encoding="utf-8")
            self.assertFalse(uploaded.wait(0.03))
        self.assertFalse(uploaded.wait(0.03))
        self.assertTrue(uploaded.wait(2.0))

    def test_manual_transport_error_is_visible_without_exposing_token(self) -> None:
        self.connect()
        self.post.side_effect = server.BedWarsMcpError("Could not reach /test-token/sync-files")
        with self.assertRaises(server.BedWarsMcpError):
            server.sync_connected()
        self.assertNotIn("test-token", server.sync_status()["last_error"])
        self.assertTrue(server.sync_status()["connected"])


if __name__ == "__main__":
    unittest.main()
