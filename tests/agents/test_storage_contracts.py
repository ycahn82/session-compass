import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from session_compass.agents.antigravity import AntigravityAdapter
from session_compass.agents.base import ContractReport
from session_compass.agents.claude import ClaudeAdapter
from session_compass.agents.codex import CodexAdapter
from session_compass.agents.copilot import CopilotAdapter


class StorageContractTests(unittest.TestCase):
    def test_contract_reports_are_ok_for_minimal_current_shapes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            claude_file = root / "session.jsonl"
            claude_file.write_text(json.dumps({"type": "user", "message": {}}) + "\n", encoding="utf-8")

            codex_file = root / "codex.sqlite"
            with sqlite3.connect(codex_file) as connection:
                connection.execute(
                    "CREATE TABLE threads (id TEXT, cwd TEXT, title TEXT, first_user_message TEXT, "
                    "preview TEXT, updated_at_ms INTEGER, updated_at TEXT, archived INTEGER)"
                )
            connection.close()

            agy_file = root / "agy.db"
            with sqlite3.connect(agy_file) as connection:
                connection.execute("CREATE TABLE steps (idx INTEGER)")
            connection.close()

            copilot_file = root / "copilot.db"
            with sqlite3.connect(copilot_file) as connection:
                connection.execute("CREATE TABLE sessions (id TEXT, cwd TEXT, summary TEXT, updated_at TEXT)")
                connection.execute("CREATE TABLE turns (session_id TEXT, user_message TEXT, turn_index INTEGER)")
            connection.close()

            reports = [
                ClaudeAdapter().check_storage_contract(claude_file),
                CodexAdapter().check_storage_contract(codex_file),
                AntigravityAdapter().check_storage_contract(agy_file),
                CopilotAdapter().check_storage_contract(copilot_file),
            ]

        self.assertTrue(all(report.ok for report in reports))
        self.assertTrue(all(isinstance(report, ContractReport) for report in reports))

    def test_contract_reports_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            claude_file = root / "session.jsonl"
            claude_file.write_text(json.dumps({"message": {}}) + "\n", encoding="utf-8")

            codex_file = root / "codex.sqlite"
            with sqlite3.connect(codex_file) as connection:
                connection.execute("CREATE TABLE threads (id TEXT)")
            connection.close()

            agy_file = root / "agy.db"
            with sqlite3.connect(agy_file) as connection:
                connection.execute("CREATE TABLE other (id INTEGER)")
            connection.close()

            copilot_file = root / "copilot.db"
            with sqlite3.connect(copilot_file) as connection:
                connection.execute("CREATE TABLE sessions (id TEXT)")
            connection.close()

            reports = [
                ClaudeAdapter().check_storage_contract(claude_file),
                CodexAdapter().check_storage_contract(codex_file),
                AntigravityAdapter().check_storage_contract(agy_file),
                CopilotAdapter().check_storage_contract(copilot_file),
            ]

        self.assertTrue(all(not report.ok for report in reports))
        self.assertIn("type", reports[0].missing)
        self.assertIn("threads.cwd", reports[1].missing)
        self.assertIn("steps", reports[2].missing)
        self.assertIn("sessions.cwd", reports[3].missing)


if __name__ == "__main__":
    unittest.main()
