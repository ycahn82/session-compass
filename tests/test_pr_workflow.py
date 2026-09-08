import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "cli-compatibility-pr.yml"


class PullRequestWorkflowTests(unittest.TestCase):
    def test_pr_workflow_is_read_only_and_has_no_issue_reporter(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("pull_request:", text)
        self.assertIn("branches:", text)
        self.assertIn("- main", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("issues: write", text)
        self.assertNotIn("github-script", text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("scripts/probe_cli_compatibility.py", text)


if __name__ == "__main__":
    unittest.main()
