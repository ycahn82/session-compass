import unittest
import sys
from unittest.mock import patch

from session_compass import cli
from session_compass.agents.registry import get_adapters


class ResumeCommandTests(unittest.TestCase):
    def test_dangerous_resume_uses_each_service_native_flag(self):
        expected = {
            "claude": ["claude", "--dangerously-skip-permissions", "--resume", "id"],
            "codex": ["codex", "--dangerously-bypass-approvals-and-sandbox", "resume", "id"],
            "agy": ["agy", "--dangerously-skip-permissions", "--conversation", "id"],
            "copilot": ["copilot", "--allow-all", "--resume=id"],
        }

        for adapter in get_adapters():
            with self.subTest(agent=adapter.name):
                self.assertEqual(adapter.build_resume_command("id", dangerous=True), expected[adapter.name])

    def test_normal_resume_keeps_the_existing_command(self):
        expected = {
            "claude": ["claude", "--resume", "id"],
            "codex": ["codex", "resume", "id"],
            "agy": ["agy", "--conversation", "id"],
            "copilot": ["copilot", "--resume=id"],
        }

        for adapter in get_adapters():
            with self.subTest(agent=adapter.name):
                self.assertEqual(adapter.build_resume_command("id"), expected[adapter.name])

    def test_cli_forwards_dangerous_option_to_selected_adapter(self):
        calls = []

        class FakeAdapter:
            name = "claude"

            def collect_sessions(self):
                return [{
                    "tool": "claude",
                    "id": "id",
                    "cwd": "/tmp",
                    "summary": "summary",
                    "last_active": cli.datetime.now(cli.timezone.utc),
                    "has_session_record": True,
                }]

            def build_resume_command(self, session_id, dangerous=False):
                calls.append((session_id, dangerous))
                return ["fake-agent", session_id]

        with patch.object(sys, "argv", ["sessions", "--dangerously-skip-permissions"]), \
                patch.object(cli, "get_adapters", return_value=[FakeAdapter()]), \
                patch.object(cli, "get_adapter", return_value=FakeAdapter()), \
                patch.object(cli, "shutil") as shutil, \
                patch.object(cli, "subprocess") as subprocess, \
                patch("builtins.input", return_value="1"):
            shutil.which.return_value = "/bin/fake-agent"
            cli.main()

        self.assertEqual(calls, [("id", True)])
        subprocess.run.assert_called_once_with(["fake-agent", "id"], cwd="/tmp", check=False)

    def test_cli_accepts_short_dangerous_option(self):
        calls = []

        class FakeAdapter:
            name = "claude"

            def collect_sessions(self):
                return [{
                    "tool": "claude",
                    "id": "id",
                    "cwd": "/tmp",
                    "summary": "summary",
                    "last_active": cli.datetime.now(cli.timezone.utc),
                    "has_session_record": True,
                }]

            def build_resume_command(self, session_id, dangerous=False):
                calls.append((session_id, dangerous))
                return ["fake-agent", session_id]

        with patch.object(sys, "argv", ["sessions", "-d"]), \
                patch.object(cli, "get_adapters", return_value=[FakeAdapter()]), \
                patch.object(cli, "get_adapter", return_value=FakeAdapter()), \
                patch.object(cli, "shutil") as shutil, \
                patch.object(cli, "subprocess") as subprocess, \
                patch("builtins.input", return_value="1"):
            shutil.which.return_value = "/bin/fake-agent"
            cli.main()

        self.assertEqual(calls, [("id", True)])
        subprocess.run.assert_called_once_with(["fake-agent", "id"], cwd="/tmp", check=False)

    def test_cli_does_not_resume_non_resumable_diagnostic_record(self):
        class FakeAdapter:
            name = "agy"

            def collect_sessions(self):
                return [{
                    "tool": "agy",
                    "id": "internal-id",
                    "cwd": "/tmp",
                    "summary": "internal task",
                    "last_active": cli.datetime.now(cli.timezone.utc),
                    "record_kind": "internal_session",
                    "has_conversation_content": False,
                }]

            def build_resume_command(self, session_id, dangerous=False):
                raise AssertionError("internal sessions must not be resumed")

        with patch.object(sys, "argv", ["sessions", "--agy", "--include-unverified"]), \
                patch.object(cli, "get_adapters", return_value=[FakeAdapter()]), \
                patch.object(cli, "get_adapter", return_value=FakeAdapter()), \
                patch.object(cli, "resume_session") as resume, \
                patch("builtins.input", return_value="1"):
            cli.main()

        resume.assert_not_called()


if __name__ == "__main__":
    unittest.main()
