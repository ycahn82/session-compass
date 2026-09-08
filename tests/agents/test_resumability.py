import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from session_compass.agents.base import ResumeStatus, classify_resumability, filter_resume_candidates
from session_compass.agents.claude import ClaudeAdapter


class ResumabilityTests(unittest.TestCase):
    def test_claude_bridge_session_is_marked_metadata_only(self):
        with tempfile.TemporaryDirectory() as tempdir:
            project_dir = Path(tempdir) / "project"
            project_dir.mkdir()
            (project_dir / "bridge-id.jsonl").write_text(
                json.dumps({"type": "bridge-session", "sessionId": "bridge-id"}) + "\n",
                encoding="utf-8",
            )
            with patch("session_compass.agents.claude.CLAUDE_PROJECTS_DIR", Path(tempdir)):
                session = ClaudeAdapter().collect_sessions()[0]

        self.assertEqual(session["record_kind"], "bridge_session")
        self.assertEqual(session["resume_status"], ResumeStatus.METADATA_ONLY.value)

    def test_metadata_only_bridge_record_is_not_a_resume_candidate(self):
        session = {"tool": "claude", "record_kind": "bridge_session"}

        self.assertEqual(classify_resumability(session), ResumeStatus.METADATA_ONLY)
        self.assertEqual(filter_resume_candidates([session]), [])

    def test_missing_conversation_content_is_not_a_resume_candidate(self):
        session = {
            "tool": "claude",
            "id": "id",
            "has_conversation_content": False,
        }

        self.assertEqual(classify_resumability(session), ResumeStatus.METADATA_ONLY)

    def test_codex_without_rollout_is_invalid(self):
        session = {"tool": "codex", "id": "id", "has_rollout": False}

        self.assertEqual(classify_resumability(session), ResumeStatus.INVALID)

    def test_valid_evidence_remains_visible_even_without_summary(self):
        session = {
            "tool": "agy",
            "id": "id",
            "has_conversation_content": True,
            "summary": "(no summary available)",
        }

        self.assertEqual(classify_resumability(session), ResumeStatus.RESUMABLE)
        self.assertEqual(filter_resume_candidates([session]), [session])

    def test_unverified_records_can_be_included_for_diagnostics(self):
        session = {"tool": "claude", "record_kind": "bridge_session"}

        self.assertEqual(filter_resume_candidates([session], include_unverified=True), [session])


if __name__ == "__main__":
    unittest.main()
