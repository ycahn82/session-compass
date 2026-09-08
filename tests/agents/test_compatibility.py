import unittest
from pathlib import Path

from cli_sessions.agents.base import validate_help_contract
from cli_sessions.agents.registry import get_adapters


class CompatibilityManifestTests(unittest.TestCase):
    def test_each_adapter_exposes_verified_compatibility_floors(self):
        expected = {
            "claude": ("2.1.263", "2.1.263"),
            "codex": ("0.153.4", "0.153.4"),
            "agy": ("1.1.27", "1.1.27"),
            "copilot": ("1.0.82", "1.0.82"),
        }

        for adapter in get_adapters():
            with self.subTest(agent=adapter.name):
                compatibility = adapter.compatibility()
                self.assertEqual(
                    (compatibility.resume_min_version, compatibility.storage_min_version),
                    expected[adapter.name],
                )
                self.assertEqual(
                    compatibility.tested_latest_version,
                    expected[adapter.name][0],
                )

    def test_help_fixtures_contain_resume_contracts(self):
        fixture_root = Path(__file__).parents[1] / "fixtures" / "cli_help"
        required_flags = {
            "claude": ("--resume", "--dangerously-skip-permissions"),
            "codex": ("resume", "--dangerously-bypass-approvals-and-sandbox"),
            "agy": ("--conversation", "--dangerously-skip-permissions"),
            "copilot": ("--resume", "--allow-all"),
        }

        for agent, flags in required_flags.items():
            with self.subTest(agent=agent):
                help_text = (fixture_root / f"{agent}-minimum.txt").read_text(encoding="utf-8")
                self.assertTrue(validate_help_contract(help_text, flags))

    def test_missing_help_capability_fails_contract(self):
        self.assertFalse(validate_help_contract("resume\n", ("resume", "--native-dangerous-flag")))


if __name__ == "__main__":
    unittest.main()
