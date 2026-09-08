import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli_sessions.agents import claude


class ClaudeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.projects = Path(self.tempdir.name) / "projects" / "project"
        self.projects.mkdir(parents=True)
        self.session_file = self.projects / "summary-session.jsonl"
        self.session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "user",
                            "cwd": "/tmp/workspace",
                            "message": {
                                "content": [
                                    {"type": "text", "text": "Fallback user message"}
                                ]
                            },
                            "timestamp": "2026-09-08T00:00:00Z",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "summary",
                            "summary": "Claude UI session title",
                            "timestamp": "2026-09-08T00:01:00Z",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_prefers_explicit_summary_record_over_user_message(self):
        with patch.object(claude, "CLAUDE_PROJECTS_DIR", self.projects.parent):
            sessions = claude.ClaudeAdapter().collect_sessions()

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["summary"], "Claude UI session title")


if __name__ == "__main__":
    unittest.main()
