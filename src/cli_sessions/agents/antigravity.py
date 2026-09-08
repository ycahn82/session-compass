"""Antigravity session discovery and resume integration."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from .base import AgentAdapter, AgentCompatibility, file_mtime, parse_timestamp, read_jsonl_lines


HOME = Path.home()
AGY_DIR = HOME / ".gemini" / "antigravity-cli"
AGY_CONVERSATIONS_DIR = AGY_DIR / "conversations"
AGY_HISTORY_FILE = AGY_DIR / "history.jsonl"
AGY_METADATA_FILE = AGY_DIR / "cache" / "conversation_metadata.json"


def count_steps(db_file: Path) -> int:
    try:
        connection = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT count(*) FROM steps").fetchone()
        finally:
            connection.close()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0


class AntigravityAdapter:
    name = "agy"

    def collect_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        if not AGY_CONVERSATIONS_DIR.is_dir():
            return sessions

        from_history: dict[str, dict[str, Any]] = {}
        for entry in read_jsonl_lines(AGY_HISTORY_FILE):
            conversation_id = entry.get("conversationId")
            if not conversation_id:
                continue
            record = from_history.setdefault(str(conversation_id), {})
            if entry.get("workspace"):
                record["workspace"] = entry["workspace"]
            if entry.get("type") != "slash_command" and str(entry.get("display", "")).strip():
                record["summary"] = entry["display"]
            timestamp = entry.get("timestamp")
            if timestamp and (not record.get("last_active") or timestamp > record["last_active"]):
                record["last_active"] = timestamp

        try:
            metadata = json.loads(AGY_METADATA_FILE.read_text(encoding="utf-8")).get("conversations", {})
        except (OSError, json.JSONDecodeError, AttributeError):
            metadata = {}

        for db_file in AGY_CONVERSATIONS_DIR.glob("*.db"):
            if count_steps(db_file) == 0:
                continue
            session_id = db_file.stem
            history = from_history.get(session_id, {})
            meta = metadata.get(session_id, {}).get("summary", {}) if isinstance(metadata, dict) else {}
            workspace_uris = meta.get("WorkspaceURIs", []) if isinstance(meta, dict) else []
            cwd = history.get("workspace") or (
                workspace_uris[0].removeprefix("file://") if workspace_uris else None
            )
            last_active = parse_timestamp(history.get("last_active") or meta.get("UpdatedAt")) or file_mtime(db_file)
            sessions.append(
                {
                    "tool": self.name,
                    "id": session_id,
                    "cwd": cwd or "(unknown)",
                    "summary": history.get("summary") or meta.get("Preview") or "(no summary available)",
                    "last_active": last_active,
                }
            )
        return sessions

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        command = ["agy"]
        if dangerous:
            command.append("--dangerously-skip-permissions")
        return command + ["--conversation", session_id]

    def compatibility(self) -> AgentCompatibility:
        return AgentCompatibility(self.name, "unknown", "unknown")


ADAPTER: AgentAdapter = AntigravityAdapter()


def collect_sessions() -> list[dict[str, Any]]:
    return ADAPTER.collect_sessions()
