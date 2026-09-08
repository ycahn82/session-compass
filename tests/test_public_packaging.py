import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicPackagingTests(unittest.TestCase):
    def test_session_compass_is_the_runtime_namespace(self):
        self.assertTrue((ROOT / "src" / "session_compass").is_dir())
        self.assertFalse((ROOT / "src" / "cli_sessions").exists())

    def test_module_help_uses_public_session_compass_module(self):
        result = subprocess.run(
            [sys.executable, "-m", "session_compass.cli", "--help"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dangerously-skip-permissions", result.stdout)
        self.assertIn("-d", result.stdout)

    def test_packaging_metadata_exposes_scompass_only(self):
        metadata = (ROOT / "pyproject.toml").read_text()
        self.assertIn('name = "session-compass"', metadata)
        self.assertIn('scompass = "session_compass.cli:main"', metadata)
        self.assertNotIn('sessions = "cli_sessions.cli:main"', metadata)


if __name__ == "__main__":
    unittest.main()
