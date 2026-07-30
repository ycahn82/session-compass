"""List and resume Claude Code, Codex, Antigravity, and Copilot CLI sessions."""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


HOME = Path.home()
CLAUDE_PROJECTS_DIR = HOME / ".claude" / "projects"
CODEX_SESSIONS_DIR = HOME / ".codex" / "sessions"
CODEX_INDEX_FILE = HOME / ".codex" / "session_index.jsonl"
AGY_DIR = HOME / ".gemini" / "antigravity-cli"
AGY_CONVERSATIONS_DIR = AGY_DIR / "conversations"
AGY_HISTORY_FILE = AGY_DIR / "history.jsonl"
AGY_METADATA_FILE = AGY_DIR / "cache" / "conversation_metadata.json"
COPILOT_DB_FILE = HOME / ".copilot" / "session-store.db"


def read_jsonl_lines(file: Path) -> list[dict[str, Any]]:
    """Return valid JSON object records from a JSON Lines file."""
    try:
        raw = file.read_text(encoding="utf-8")
    except OSError:
        return []

    records = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def truncate(value: Any, length: int) -> str:
    if not value:
        return ""
    clean = re.sub(r"\s+", " ", str(value)).strip()
    return clean[: length - 1] + "…" if len(clean) > length else clean


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    try:
        text = str(value).replace("Z", "+00:00")
        date = datetime.fromisoformat(text)
        return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
    except (TypeError, ValueError):
        return None


def file_mtime(file: Path) -> datetime:
    return datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc)


def collect_claude_sessions() -> list[dict[str, Any]]:
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
                    "tool": "claude",
                    "id": file.stem,
                    "cwd": cwd or fallback_cwd,
                    "summary": summary or "(no summary available)",
                    "last_active": parse_timestamp(last_timestamp) or file_mtime(file),
                }
            )
    return sessions


def find_codex_rollout_file(session_id: str) -> Optional[Path]:
    if not CODEX_SESSIONS_DIR.is_dir():
        return None
    for path in CODEX_SESSIONS_DIR.rglob("*"):
        if path.is_file() and session_id in path.name:
            return path
    return None


def find_codex_state_db() -> Optional[Path]:
    """Return the newest versioned Codex state database, if available."""
    state_dbs = list((HOME / ".codex").glob("state_*.sqlite"))
    return max(state_dbs, key=lambda path: path.stat().st_mtime, default=None)


def collect_codex_state_sessions() -> list[dict[str, Any]]:
    """Read current Codex interactive sessions from its SQLite thread inventory."""
    state_db = find_codex_state_db()
    if not state_db:
        return []

    try:
        with sqlite3.connect(f"{state_db.resolve().as_uri()}?mode=ro", uri=True) as connection:
            rows = connection.execute(
                """
                SELECT id, cwd, title, first_user_message, preview, updated_at_ms, updated_at
                FROM threads
                WHERE archived = 0 AND preview <> ''
                """
            ).fetchall()
    except (OSError, sqlite3.Error):
        return []

    sessions = []
    for session_id, cwd, title, first_message, preview, updated_at_ms, updated_at in rows:
        sessions.append(
            {
                "tool": "codex",
                "id": str(session_id),
                "cwd": cwd or "(unknown)",
                "summary": title or first_message or preview or "(no summary available)",
                "last_active": parse_timestamp(updated_at_ms) or parse_timestamp(updated_at) or datetime.fromtimestamp(0, tz=timezone.utc),
            }
        )
    return sessions


def collect_codex_sessions() -> list[dict[str, Any]]:
    sessions = collect_codex_state_sessions()
    known_ids = {session["id"] for session in sessions}

    # Older Codex versions used this JSONL index. Keep it as a fallback so the
    # script can still list sessions from installations without state_*.sqlite.
    for entry in read_jsonl_lines(CODEX_INDEX_FILE):
        session_id = entry.get("id")
        if not session_id or str(session_id) in known_ids:
            continue
        cwd = None
        rollout_file = find_codex_rollout_file(str(session_id))
        if rollout_file:
            meta_line = next((line for line in read_jsonl_lines(rollout_file) if line.get("type") == "session_meta"), None)
            payload = meta_line.get("payload", {}) if meta_line else {}
            if isinstance(payload, dict):
                cwd = payload.get("cwd")

        sessions.append(
            {
                "tool": "codex",
                "id": str(session_id),
                "cwd": cwd or "(unknown)",
                "summary": entry.get("thread_name") or "(no summary available)",
                "last_active": parse_timestamp(entry.get("updated_at")) or datetime.fromtimestamp(0, tz=timezone.utc),
            }
        )
    return sessions


def count_agy_steps(db_file: Path) -> int:
    try:
        with sqlite3.connect(f"file:{db_file}?mode=ro", uri=True) as connection:
            row = connection.execute("SELECT count(*) FROM steps").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0


def collect_antigravity_sessions() -> list[dict[str, Any]]:
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
        if count_agy_steps(db_file) == 0:
            continue
        session_id = db_file.stem
        history = from_history.get(session_id, {})
        meta = metadata.get(session_id, {}).get("summary", {}) if isinstance(metadata, dict) else {}
        workspace_uris = meta.get("WorkspaceURIs", []) if isinstance(meta, dict) else []
        cwd = history.get("workspace") or (workspace_uris[0].removeprefix("file://") if workspace_uris else None)
        last_active = parse_timestamp(history.get("last_active") or meta.get("UpdatedAt")) or file_mtime(db_file)
        sessions.append(
            {
                "tool": "agy",
                "id": session_id,
                "cwd": cwd or "(unknown)",
                "summary": history.get("summary") or meta.get("Preview") or "(no summary available)",
                "last_active": last_active,
            }
        )
    return sessions


def collect_copilot_sessions() -> list[dict[str, Any]]:
    if not COPILOT_DB_FILE.is_file():
        return []

    try:
        with sqlite3.connect(f"file:{COPILOT_DB_FILE}?mode=ro", uri=True) as connection:
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
    except (OSError, sqlite3.Error):
        return []

    sessions = []
    for session_id, cwd, summary, updated_at in sessions_rows:
        first_message = first_messages.get(session_id)
        best_summary = first_message or summary
        sessions.append(
            {
                "tool": "copilot",
                "id": str(session_id),
                "cwd": cwd or "(unknown)",
                "summary": best_summary or "(no summary available)",
                "last_active": parse_timestamp(updated_at) or datetime.fromtimestamp(0, tz=timezone.utc),
            }
        )
    return sessions


def format_relative_time(date: datetime) -> str:
    diff_minutes = round((datetime.now(timezone.utc) - date).total_seconds() / 60)
    if diff_minutes < 1:
        return "just now"
    if diff_minutes < 60:
        return f"{diff_minutes}m ago"
    diff_hours = round(diff_minutes / 60)
    if diff_hours < 24:
        return f"{diff_hours}h ago"
    diff_days = round(diff_hours / 24)
    return f"{diff_days}d ago" if diff_days < 30 else date.date().isoformat()


def shorten_home(path: str) -> str:
    home = str(HOME)
    return "~" + path[len(home) :] if path.startswith(home) else path


def resume_session(session: dict[str, Any]) -> None:
    cwd = session["cwd"] if Path(session["cwd"]).exists() else os.getcwd()
    command_args = {
        "claude": ["claude", "--resume", session["id"]],
        "codex": ["codex", "resume", session["id"]],
        "agy": ["agy", "--conversation", session["id"]],
        "copilot": ["copilot", f"--resume={session['id']}"],
    }[session["tool"]]
    print(f"\n> cd {shorten_home(cwd)} && {' '.join(command_args)}\n")
    if not shutil.which(command_args[0]):
        print(f"Command not found: {command_args[0]}", file=sys.stderr)
        return
    subprocess.run(command_args, cwd=cwd, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    filters = parser.add_mutually_exclusive_group()
    filters.add_argument("--claude", action="store_const", const="claude", dest="tool")
    filters.add_argument("--codex", action="store_const", const="codex", dest="tool")
    filters.add_argument("--agy", action="store_const", const="agy", dest="tool")
    filters.add_argument("--copilot", action="store_const", const="copilot", dest="tool")
    args = parser.parse_args()

    sessions = (
        collect_claude_sessions()
        + collect_codex_sessions()
        + collect_antigravity_sessions()
        + collect_copilot_sessions()
    )
    if args.tool:
        sessions = [session for session in sessions if session["tool"] == args.tool]
    sessions.sort(key=lambda session: session["last_active"])  # oldest first, latest last (like ls -ltrh)
    if not sessions:
        print("No sessions found.")
        return

    index_width = len(str(len(sessions)))
    print()
    for index, session in enumerate(sessions, start=1):
        project = truncate(shorten_home(session["cwd"]), 32)
        print(
            f"{index:>{index_width}}) [{session['tool']:<7}] {format_relative_time(session['last_active']):<9} "
            f"{project:<32} {truncate(session['summary'], 70)}"
        )
        print(f"{' ' * (index_width + 2)}id: {session['id']}")
    print()

    answer = input("Resume which session? (number, or q to quit): ").strip().lower()
    if not answer or answer == "q":
        return
    try:
        choice = int(answer)
    except ValueError:
        choice = 0
    if not 1 <= choice <= len(sessions):
        print("Invalid selection.")
        return
    resume_session(sessions[choice - 1])


if __name__ == "__main__":
    main()
