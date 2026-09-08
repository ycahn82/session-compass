"""List and resume Claude Code, Codex, Antigravity, and Copilot CLI sessions."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agents.base import ResumeStatus, classify_resumability, filter_resume_candidates
from .agents.registry import get_adapter, get_adapters


HOME = Path.home()


def truncate(value: Any, length: int) -> str:
    if not value:
        return ""
    clean = re.sub(r"\s+", " ", str(value)).strip()
    return clean[: length - 1] + "…" if len(clean) > length else clean


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


def collect_claude_sessions() -> list[dict[str, Any]]:
    return get_adapter("claude").collect_sessions()


def collect_codex_sessions() -> list[dict[str, Any]]:
    return get_adapter("codex").collect_sessions()


def collect_antigravity_sessions() -> list[dict[str, Any]]:
    return get_adapter("agy").collect_sessions()


def collect_copilot_sessions() -> list[dict[str, Any]]:
    return get_adapter("copilot").collect_sessions()


def resume_session(session: dict[str, Any], dangerous: bool = False) -> None:
    cwd = session["cwd"] if Path(session["cwd"]).exists() else os.getcwd()
    adapter = get_adapter(session["tool"])
    command_args = adapter.build_resume_command(session["id"], dangerous=dangerous)
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
    parser.add_argument(
        "--include-unverified",
        action="store_true",
        help="Include sessions without verified resume evidence",
    )
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Use each agent's native permission-bypass option when resuming",
    )
    args = parser.parse_args()

    sessions = [session for adapter in get_adapters() for session in adapter.collect_sessions()]
    if args.tool:
        sessions = [session for session in sessions if session["tool"] == args.tool]
    visible_sessions = filter_resume_candidates(sessions, include_unverified=args.include_unverified)
    hidden_count = len(sessions) - len(visible_sessions)
    sessions = visible_sessions
    if hidden_count and not args.include_unverified:
        print(f"{hidden_count} unverified sessions hidden. Use --include-unverified to inspect them.")
    sessions.sort(key=lambda session: session["last_active"])
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
        if args.include_unverified:
            status = classify_resumability(session)
            if status not in {ResumeStatus.RESUMABLE, ResumeStatus.LIKELY_RESUMABLE}:
                print(f"{' ' * (index_width + 2)}status: {status.value}")
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
    selected = sessions[choice - 1]
    status = classify_resumability(selected)
    if status not in {ResumeStatus.RESUMABLE, ResumeStatus.LIKELY_RESUMABLE}:
        print(f"Session is not resumable ({status.value}).")
        return
    resume_session(selected, dangerous=args.dangerously_skip_permissions)


if __name__ == "__main__":
    main()
