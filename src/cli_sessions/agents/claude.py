"""Claude Code session discovery and resume integration."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import AgentAdapter, AgentCompatibility, file_mtime, parse_timestamp, read_jsonl_lines


HOME = Path.home()
CLAUDE_PROJECTS_DIR = HOME / ".claude" / "projects"


class ClaudeAdapter:
    name = "claude"

    def collect_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        if not CLAUDE_PROJECTS_DIR.is_dir():
            return sessions

        for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            for file in project_dir.glob("*.jsonl"):
                lines = read_jsonl_lines(file)
                if not lines:
                    continue

                cwd = summary = None
                last_timestamp = None
                for entry in lines:
                    cwd = cwd or entry.get("cwd")
                    message = entry.get("message") or {}
                    content = message.get("content") if isinstance(message, dict) else None
                    if not summary and entry.get("type") == "user" and isinstance(content, str) and content.strip():
                        summary = content
                    last_timestamp = entry.get("timestamp") or last_timestamp

                fallback_cwd = "/" + project_dir.name.lstrip("-").replace("-", "/")
                sessions.append(
                    {
                        "tool": self.name,
                        "id": file.stem,
                        "cwd": cwd or fallback_cwd,
                        "summary": summary or "(no summary available)",
                        "last_active": parse_timestamp(last_timestamp) or file_mtime(file),
                    }
                )
        return sessions

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        return ["claude", "--resume", session_id]

    def compatibility(self) -> AgentCompatibility:
        return AgentCompatibility(self.name, "unknown", "unknown")


ADAPTER: AgentAdapter = ClaudeAdapter()


def collect_sessions() -> list[dict[str, Any]]:
    return ADAPTER.collect_sessions()
