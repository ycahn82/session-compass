import unittest

from cli_sessions.agents.base import AgentAdapter
from cli_sessions.agents.registry import get_adapters


class RegistryTests(unittest.TestCase):
    def test_registry_contains_all_supported_agents(self):
        adapters = get_adapters()
        self.assertEqual(
            {adapter.name for adapter in adapters},
            {"claude", "codex", "agy", "copilot"},
        )
        for adapter in adapters:
            self.assertIsInstance(adapter, AgentAdapter)


if __name__ == "__main__":
    unittest.main()
