"""Claude Code session discovery and resume integration."""

from pathlib import Path
from typing import Any

from .base import (
    AgentAdapter,
    AgentCompatibility,
    ContractReport,
    classify_resumability,
    file_mtime,
    parse_timestamp,
    read_jsonl_lines,
)


HOME = Path.home()
CLAUDE_PROJECTS_DIR = HOME / ".claude" / "projects"


class ClaudeAdapter:
    name = "claude"

    def check_storage_contract(self, path: Path) -> ContractReport:
        records = read_jsonl_lines(path)
        if not records:
            return ContractReport(self.name, False, ("jsonl",))
        missing = () if all("type" in record for record in records) else ("type",)
        return ContractReport(self.name, not missing, missing)

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
                has_conversation_content = False
                has_bridge_record = False
                for entry in lines:
                    has_bridge_record = has_bridge_record or entry.get("type") == "bridge-session"
                    cwd = cwd or entry.get("cwd")
                    message = entry.get("message") or {}
                    content = message.get("content") if isinstance(message, dict) else None
                    if entry.get("type") in {"user", "assistant"} and content:
                        has_conversation_content = True
                    if not summary and entry.get("type") == "user" and isinstance(content, str) and content.strip():
                        summary = content
                    last_timestamp = entry.get("timestamp") or last_timestamp

                fallback_cwd = "/" + project_dir.name.lstrip("-").replace("-", "/")
                session = {
                        "tool": self.name,
                        "id": file.stem,
                        "cwd": cwd or fallback_cwd,
                        "summary": summary or "(no summary available)",
                        "last_active": parse_timestamp(last_timestamp) or file_mtime(file),
                        "record_kind": (
                            "conversation"
                            if has_conversation_content
                            else "bridge_session"
                            if has_bridge_record
                            else "metadata_only"
                        ),
                        "has_conversation_content": has_conversation_content,
                    }
                session["resume_status"] = classify_resumability(session).value
                sessions.append(session)
        return sessions

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        command = ["claude"]
        if dangerous:
            command.append("--dangerously-skip-permissions")
        return command + ["--resume", session_id]

    def compatibility(self) -> AgentCompatibility:
        return AgentCompatibility(self.name, "2.1.263", "2.1.263", "2.1.263")


ADAPTER: AgentAdapter = ClaudeAdapter()


def collect_sessions() -> list[dict[str, Any]]:
    return ADAPTER.collect_sessions()
