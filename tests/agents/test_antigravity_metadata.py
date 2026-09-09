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
        self._write_conversation("uncatalogued-no-workspace")
        history_lines = [
            {
                "display": "새 대화를 시작합니다.",
                "timestamp": 1,
                "workspace": "/home/first-message-has-no-id",
            },
            {
                "display": "/rename brand new chat",
                "timestamp": 2,
                "workspace": "/tmp/uncatalogued-workspace",
                "conversationId": "uncatalogued-session",
                "type": "slash_command",
            },
            {
                "display": "/exit",
                "timestamp": 3,
                "workspace": "/tmp/uncatalogued-workspace",
                "conversationId": "uncatalogued-session",
                "type": "slash_command",
            },
        ]
        self.history.write_text(
            "\n".join(json.dumps(line) for line in history_lines) + "\n",
            encoding="utf-8",
        )
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

    def test_internal_sessions_are_excluded(self):
        ids = {session["id"] for session in antigravity.AntigravityAdapter().collect_sessions()}

        self.assertNotIn("internal-session", ids)

    def test_uncatalogued_session_falls_back_to_history_workspace(self):
        """Antigravity's UI catalog is populated asynchronously and lags behind brand-new
        sessions. A session must still show up (using history.jsonl as a fallback) instead
        of being silently dropped while the catalog catches up."""
        sessions = antigravity.AntigravityAdapter().collect_sessions()
        by_id = {session["id"]: session for session in sessions}

        self.assertIn("uncatalogued-session", by_id)
        self.assertEqual(by_id["uncatalogued-session"]["cwd"], "/tmp/uncatalogued-workspace")

    def test_opening_turn_without_a_conversation_id_is_attributed_retroactively(self):
        """Antigravity only tags a history.jsonl entry with its conversationId once the id
        has been assigned, so a session's very first turn(s) are logged without one. Once a
        later turn in the same session (e.g. /rename or /exit) carries the id, the earlier,
        untagged turns must be attributed back to it instead of being dropped."""
        sessions = antigravity.AntigravityAdapter().collect_sessions()
        by_id = {session["id"]: session for session in sessions}

        self.assertEqual(by_id["uncatalogued-session"]["summary"], "새 대화를 시작합니다.")

    def test_uncatalogued_session_without_any_workspace_is_excluded(self):
        ids = {session["id"] for session in antigravity.AntigravityAdapter().collect_sessions()}

        self.assertNotIn("uncatalogued-no-workspace", ids)

    def test_visible_sessions_have_summary_and_workspace(self):
        for session in antigravity.AntigravityAdapter().collect_sessions():
            self.assertTrue(session["summary"])
            self.assertTrue(session["cwd"])


if __name__ == "__main__":
    unittest.main()
