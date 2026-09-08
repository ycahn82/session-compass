import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from session_compass.agents import antigravity


class AntigravityMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.conversations = self.root / "conversations"
        self.conversations.mkdir()
        self.history = self.root / "history.jsonl"
        self.metadata = self.root / "cache" / "conversation_metadata.json"
        self.metadata.parent.mkdir()
        self.summaries = self.root / "conversation_summaries.db"
        with sqlite3.connect(self.summaries) as connection:
            connection.execute(
                """
                CREATE TABLE conversation_summaries (
                    conversation_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    preview TEXT NOT NULL DEFAULT '',
                    step_count INTEGER NOT NULL DEFAULT 0,
                    last_modified_time TEXT NOT NULL,
                    workspace_uris TEXT NOT NULL
                )
                """
            )
            connection.executemany(
                "INSERT INTO conversation_summaries VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        "user-with-title",
                        "UI chat title",
                        "A less useful preview",
                        1,
                        "2026-09-08T00:00:00Z",
                        json.dumps(["file:///tmp/title-workspace"]),
                    ),
                    (
                        "user-with-preview",
                        "",
                        "Preview fallback",
                        1,
                        "2026-09-08T00:00:00Z",
                        json.dumps(["file:///tmp/preview-workspace"]),
                    ),
                    (
                        "internal-session",
                        "Internal task",
                        "Internal preview",
                        1,
                        "2026-09-08T00:00:00Z",
                        json.dumps(["file:///tmp/internal-workspace"]),
                    ),
                ],
            )
        connection.close()
        self._write_conversation("user-with-title")
        self._write_conversation("user-with-preview")
        self._write_conversation("internal-session")
        self._write_conversation("uncatalogued-session")
        self.history.write_text("", encoding="utf-8")
        self.metadata.write_text(
            json.dumps(
                {
                    "conversations": {
                        "user-with-title": {"is_internal": False},
                        "user-with-preview": {"is_internal": False},
                        "internal-session": {"is_internal": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        self.patches = [
            patch.object(antigravity, "AGY_CONVERSATIONS_DIR", self.conversations),
            patch.object(antigravity, "AGY_HISTORY_FILE", self.history),
            patch.object(antigravity, "AGY_METADATA_FILE", self.metadata),
            patch.object(antigravity, "AGY_SUMMARIES_DB", self.summaries, create=True),
        ]
        for context in self.patches:
            context.start()

    def tearDown(self):
        for context in reversed(self.patches):
            context.stop()
        self.tempdir.cleanup()

    def _write_conversation(self, conversation_id):
        path = self.conversations / f"{conversation_id}.db"
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO steps VALUES (1)")
        connection.close()

    def test_uses_ui_title_then_preview_for_user_sessions(self):
        sessions = antigravity.AntigravityAdapter().collect_sessions()
        by_id = {session["id"]: session for session in sessions}

        self.assertEqual(by_id["user-with-title"]["summary"], "UI chat title")
        self.assertEqual(by_id["user-with-preview"]["summary"], "Preview fallback")

    def test_internal_and_uncatalogued_sessions_are_excluded(self):
        ids = {session["id"] for session in antigravity.AntigravityAdapter().collect_sessions()}

        self.assertNotIn("internal-session", ids)
        self.assertNotIn("uncatalogued-session", ids)

    def test_visible_sessions_have_summary_and_workspace(self):
        for session in antigravity.AntigravityAdapter().collect_sessions():
            self.assertTrue(session["summary"])
            self.assertTrue(session["cwd"])


if __name__ == "__main__":
    unittest.main()
