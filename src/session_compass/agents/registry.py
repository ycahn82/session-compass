"""Registry of supported service adapters."""

from .antigravity import ADAPTER as ANTIGRAVITY_ADAPTER
from .base import AgentAdapter
from .claude import ADAPTER as CLAUDE_ADAPTER
from .codex import ADAPTER as CODEX_ADAPTER
from .copilot import ADAPTER as COPILOT_ADAPTER


_ADAPTERS = {
    adapter.name: adapter
    for adapter in (
        CLAUDE_ADAPTER,
        CODEX_ADAPTER,
        ANTIGRAVITY_ADAPTER,
        COPILOT_ADAPTER,
    )
}


def get_adapters() -> list[AgentAdapter]:
    return list(_ADAPTERS.values())


def get_adapter(name: str) -> AgentAdapter:
    return _ADAPTERS[name]
