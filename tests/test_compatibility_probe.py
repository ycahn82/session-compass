import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from cli_sessions.agents.registry import get_adapter
from scripts.build_compatibility_report import sanitize_report
from scripts.probe_cli_compatibility import probe_agent


class CompatibilityProbeTests(unittest.TestCase):
    def make_executable(self, directory, name, body):
        path = Path(directory) / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def test_probe_reads_version_and_help_without_resume(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.make_executable(
                tempdir,
                "codex",
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then echo 'codex-cli 0.153.4'; exit 0; fi\n"
                "if [ \"$1\" = \"--help\" ]; then echo 'resume --dangerously-bypass-approvals-and-sandbox'; exit 0; fi\n"
                "exit 2\n",
            )

            result = probe_agent(get_adapter("codex"), Path(tempdir))

        self.assertEqual(result["version"], "0.153.4")
        self.assertTrue(result["resume"])
        self.assertTrue(result["dangerous_resume"])
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("session_id", json.dumps(result))

    def test_probe_reports_missing_capability_without_stopping(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.make_executable(
                tempdir,
                "claude",
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then echo '2.1.263'; exit 0; fi\n"
                "if [ \"$1\" = \"--help\" ]; then echo '--resume'; exit 0; fi\n",
            )

            result = probe_agent(get_adapter("claude"), Path(tempdir))

        self.assertTrue(result["resume"])
        self.assertFalse(result["dangerous_resume"])
        self.assertEqual(result["status"], "fail")
        self.assertIn("--dangerously-skip-permissions", result["missing_flags"])

    def test_probe_reports_timeout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.make_executable(
                tempdir,
                "agy",
                "#!/bin/sh\nsleep 2\n",
            )

            result = probe_agent(get_adapter("agy"), Path(tempdir), timeout=0.01)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["failure"], "timeout")

    def test_report_sanitizer_removes_sensitive_values(self):
        report = {
            "agent": "claude",
            "version": "2.1.263",
            "status": "fail",
            "failure": "prompt /home/user/project 123e4567-e89b-12d3-a456-426614174000 sk-secret-value",
            "detected_flags": ["--resume"],
        }

        sanitized = sanitize_report([report], commit_sha="abc123")
        serialized = json.dumps(sanitized)

        self.assertNotIn("/home/user", serialized)
        self.assertNotIn("123e4567-e89b-12d3-a456-426614174000", serialized)
        self.assertNotIn("sk-secret-value", serialized)
        self.assertEqual(sanitized["commit_sha"], "abc123")
        self.assertEqual(sanitized["results"][0]["failure"], "prompt <path> <uuid> <secret>")


if __name__ == "__main__":
    unittest.main()
