"""Codex session discovery and resume integration."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .base import AgentAdapter, AgentCompatibility, file_mtime, parse_timestamp, read_jsonl_lines


HOME = Path.home()
CODEX_SESSIONS_DIR = HOME / ".codex" / "sessions"
CODEX_INDEX_FILE = HOME / ".codex" / "session_index.jsonl"


def find_codex_rollout_file(session_id: str) -> Optional[Path]:
    if not CODEX_SESSIONS_DIR.is_dir():
        return None
    for path in CODEX_SESSIONS_DIR.rglob("*"):
        if path.is_file() and session_id in path.name:
            return path
    return None


def find_codex_state_db() -> Optional[Path]:
    state_dbs = list((HOME / ".codex").glob("state_*.sqlite"))
    return max(state_dbs, key=lambda path: path.stat().st_mtime, default=None)


class CodexAdapter:
    name = "codex"

    def collect_state_sessions(self) -> list[dict[str, Any]]:
        state_db = find_codex_state_db()
        if not state_db:
            return []

        try:
            connection = sqlite3.connect(f"{state_db.resolve().as_uri()}?mode=ro", uri=True)
            try:
                rows = connection.execute(
                    """
                    SELECT id, cwd, title, first_user_message, preview, updated_at_ms, updated_at
                    FROM threads
                    WHERE archived = 0 AND preview <> ''
                    """
                ).fetchall()
            finally:
                connection.close()
        except (OSError, sqlite3.Error):
            return []

        return [
            {
                "tool": self.name,
                "id": str(session_id),
                "cwd": cwd or "(unknown)",
                "summary": title or first_message or preview or "(no summary available)",
                "last_active": parse_timestamp(updated_at_ms)
                or parse_timestamp(updated_at)
                or datetime.fromtimestamp(0, tz=timezone.utc),
            }
            for session_id, cwd, title, first_message, preview, updated_at_ms, updated_at in rows
        ]

    def collect_sessions(self) -> list[dict[str, Any]]:
        sessions = self.collect_state_sessions()
        known_ids = {session["id"] for session in sessions}

        for entry in read_jsonl_lines(CODEX_INDEX_FILE):
            session_id = entry.get("id")
            if not session_id or str(session_id) in known_ids:
                continue
            cwd = None
            rollout_file = find_codex_rollout_file(str(session_id))
            if rollout_file:
                meta_line = next(
                    (line for line in read_jsonl_lines(rollout_file) if line.get("type") == "session_meta"),
                    None,
                )
                payload = meta_line.get("payload", {}) if meta_line else {}
                if isinstance(payload, dict):
                    cwd = payload.get("cwd")

            sessions.append(
                {
                    "tool": self.name,
                    "id": str(session_id),
                    "cwd": cwd or "(unknown)",
                    "summary": entry.get("thread_name") or "(no summary available)",
                    "last_active": parse_timestamp(entry.get("updated_at"))
                    or datetime.fromtimestamp(0, tz=timezone.utc),
                }
            )
        return sessions

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        return ["codex", "resume", session_id]

    def compatibility(self) -> AgentCompatibility:
        return AgentCompatibility(self.name, "unknown", "unknown")


ADAPTER: AgentAdapter = CodexAdapter()


def collect_sessions() -> list[dict[str, Any]]:
    return ADAPTER.collect_sessions()
