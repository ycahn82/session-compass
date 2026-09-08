import json
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "update_compatibility_issue.js"


def call_node(expression):
    result = subprocess.run(
        ["node", "-e", f"const mod = require({json.dumps(str(SCRIPT))}); {expression}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class IssuePayloadTests(unittest.TestCase):
    def test_issue_title_and_labels_are_stable(self):
        result = call_node(
            "console.log(JSON.stringify({title: mod.issueTitle('codex', 'resume capability mismatch'), labels: mod.issueLabels('codex')}));"
        )

        self.assertEqual(result["title"], "[compat] codex resume capability mismatch")
        self.assertEqual(
            result["labels"],
            ["compatibility", "automated-detection", "agent:codex"],
        )

    def test_failure_body_is_sanitized_and_bounded(self):
        result = call_node(
            "console.log(JSON.stringify(mod.failureBody({agent:'codex', version:'0.153.4', status:'fail', failure:'prompt /home/user/project 123e4567-e89b-12d3-a456-426614174000 sk-secret-value'}, 'https://artifact', 'https://run')));"
        )

        self.assertNotIn("/home/user", result)
        self.assertNotIn("123e4567-e89b-12d3-a456-426614174000", result)
        self.assertNotIn("sk-secret-value", result)
        self.assertIn("https://artifact", result)
        self.assertIn("https://run", result)

    def test_recovery_comment_does_not_close_issue(self):
        result = call_node(
            "console.log(JSON.stringify(mod.recoveryComment('codex', 'https://run')));"
        )

        self.assertIn("codex", result)
        self.assertIn("recovered", result.lower())
        self.assertNotIn("close", result.lower())


if __name__ == "__main__":
    unittest.main()
