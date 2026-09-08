"""Copilot session discovery and resume integration."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import AgentAdapter, AgentCompatibility, ContractReport, classify_resumability, parse_timestamp


HOME = Path.home()
COPILOT_DB_FILE = HOME / ".copilot" / "session-store.db"


class CopilotAdapter:
    name = "copilot"

    def check_storage_contract(self, path: Path) -> ContractReport:
        required = {
            "sessions": {"id", "cwd", "summary", "updated_at"},
            "turns": {"session_id", "user_message", "turn_index"},
        }
        try:
            connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
            try:
                missing = []
                for table, columns in required.items():
                    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
                    if not rows:
                        missing.append(table)
                        continue
                    available = {row[1] for row in rows}
                    missing.extend(f"{table}.{column}" for column in sorted(columns - available))
            finally:
                connection.close()
        except (OSError, sqlite3.Error):
            return ContractReport(self.name, False, ("sessions", "turns"))
        missing_tuple = tuple(missing)
        return ContractReport(self.name, not missing_tuple, missing_tuple)

    def collect_sessions(self) -> list[dict[str, Any]]:
        if not COPILOT_DB_FILE.is_file():
            return []

        try:
            connection = sqlite3.connect(f"file:{COPILOT_DB_FILE}?mode=ro", uri=True)
            try:
                sessions_rows = connection.execute(
                    "SELECT id, cwd, summary, updated_at FROM sessions"
                ).fetchall()
                first_messages = dict(
                    connection.execute(
                        """
                        SELECT session_id, user_message FROM turns
                        WHERE turn_index = 0
                        """
                    ).fetchall()
                )
            finally:
                connection.close()
        except (OSError, sqlite3.Error):
            return []

        sessions = []
        for session_id, cwd, summary, updated_at in sessions_rows:
            first_message = first_messages.get(session_id)
            session = {
                    "tool": self.name,
                    "id": str(session_id),
                    "cwd": cwd or "(unknown)",
                    "summary": first_message or summary or "(no summary available)",
                    "last_active": parse_timestamp(updated_at)
                    or datetime.fromtimestamp(0, tz=timezone.utc),
                    "record_kind": "conversation",
                    "has_session_record": True,
                }
            session["resume_status"] = classify_resumability(session).value
            sessions.append(session)
        return sessions

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        return ["copilot", f"--resume={session_id}"]

    def compatibility(self) -> AgentCompatibility:
        return AgentCompatibility(self.name, "1.0.82", "1.0.82", "1.0.82")


ADAPTER: AgentAdapter = CopilotAdapter()


def collect_sessions() -> list[dict[str, Any]]:
    return ADAPTER.collect_sessions()
