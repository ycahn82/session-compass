import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cli_sessions import cli


class SessionCollectorCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

        self.claude_dir = self.root / "claude" / "project"
        self.claude_dir.mkdir(parents=True)
        (self.claude_dir / "claude-id.jsonl").write_text(
            json.dumps(
                {
                    "type": "user",
                    "cwd": str(self.root / "workspace"),
                    "timestamp": "2026-09-08T01:02:03Z",
                    "message": {"content": "Investigate the session issue"},
                }
            )
            + "\n",
            encoding="utf-8",
        )

        self.codex_dir = self.root / "codex"
        self.codex_dir.mkdir()
        self.codex_db = self.codex_dir / "state_1.sqlite"
        with sqlite3.connect(self.codex_db) as connection:
            connection.execute(
                """
                CREATE TABLE threads (
                    id TEXT PRIMARY KEY,
                    cwd TEXT,
                    title TEXT,
                    first_user_message TEXT,
                    preview TEXT,
                    updated_at_ms INTEGER,
                    updated_at TEXT,
                    archived INTEGER
                )
                """
            )
            connection.execute(
                """
                INSERT INTO threads
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "codex-id",
                    str(self.root / "workspace"),
                    "Codex task",
                    "First Codex message",
                    "Codex preview",
                    1788829323000,
                    None,
                    0,
                ),
            )

        self.agy_dir = self.root / "agy"
        self.agy_conversations = self.agy_dir / "conversations"
        self.agy_conversations.mkdir(parents=True)
        self.agy_db = self.agy_conversations / "agy-id.db"
        with sqlite3.connect(self.agy_db) as connection:
            connection.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO steps VALUES (1)")
        (self.agy_dir / "history.jsonl").write_text(
            json.dumps(
                {
                    "conversationId": "agy-id",
                    "workspace": str(self.root / "workspace"),
                    "display": "Antigravity task",
                    "timestamp": "2026-09-08T01:02:03Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        agy_cache = self.agy_dir / "cache"
        agy_cache.mkdir()
        (agy_cache / "conversation_metadata.json").write_text(
            json.dumps({"conversations": {"agy-id": {"summary": {}}}}),
            encoding="utf-8",
        )

        self.copilot_db = self.root / "copilot.db"
        with sqlite3.connect(self.copilot_db) as connection:
            connection.execute(
                "CREATE TABLE sessions (id TEXT, cwd TEXT, summary TEXT, updated_at TEXT)"
            )
            connection.execute(
                "CREATE TABLE turns (session_id TEXT, user_message TEXT, turn_index INTEGER)"
            )
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                (
                    "copilot-id",
                    str(self.root / "workspace"),
                    "Copilot session",
                    "2026-09-08T01:02:03Z",
                ),
            )
            connection.execute(
                "INSERT INTO turns VALUES (?, ?, ?)",
                ("copilot-id", "First Copilot message", 0),
            )

        self.patches = [
            patch.object(cli, "CLAUDE_PROJECTS_DIR", self.root / "claude"),
            patch.object(cli, "CODEX_SESSIONS_DIR", self.codex_dir),
            patch.object(cli, "CODEX_INDEX_FILE", self.codex_dir / "session_index.jsonl"),
            patch.object(cli, "AGY_DIR", self.agy_dir),
            patch.object(cli, "AGY_CONVERSATIONS_DIR", self.agy_conversations),
            patch.object(cli, "AGY_HISTORY_FILE", self.agy_dir / "history.jsonl"),
            patch.object(cli, "AGY_METADATA_FILE", agy_cache / "conversation_metadata.json"),
            patch.object(cli, "COPILOT_DB_FILE", self.copilot_db),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.tempdir.cleanup()

    def test_collectors_return_common_session_fields(self):
        collectors = (
            cli.collect_claude_sessions(),
            cli.collect_codex_sessions(),
            cli.collect_antigravity_sessions(),
            cli.collect_copilot_sessions(),
        )
        sessions = [session for group in collectors for session in group]
        self.assertEqual({session["tool"] for session in sessions}, {"claude", "codex", "agy", "copilot"})
        for session in sessions:
            self.assertTrue(
                {"tool", "id", "cwd", "summary", "last_active"}.issubset(session)
            )
            self.assertIsInstance(session["last_active"], datetime)
            self.assertIsNotNone(session["last_active"].tzinfo)


class ResumeCommandCharacterizationTests(unittest.TestCase):
    def test_current_resume_commands_are_forwarded_unchanged(self):
        expected = {
            "claude": ["claude", "--resume", "claude-id"],
            "codex": ["codex", "resume", "codex-id"],
            "agy": ["agy", "--conversation", "agy-id"],
            "copilot": ["copilot", "--resume=copilot-id"],
        }
        for tool, command in expected.items():
            with self.subTest(tool=tool), patch.object(cli.shutil, "which", return_value="/bin/tool"), patch.object(
                cli.subprocess, "run"
            ) as run:
                cli.resume_session(
                    {"tool": tool, "id": command[-1].split("=")[-1], "cwd": "/tmp"}
                )
                self.assertEqual(run.call_args.args[0], command)


if __name__ == "__main__":
    unittest.main()
