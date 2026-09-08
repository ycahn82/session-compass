"""Shared types and helpers for service-specific session adapters."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class AgentCompatibility:
    agent: str
    resume_min_version: str
    storage_min_version: str
    tested_latest_version: Optional[str] = None


@dataclass(frozen=True)
class ProbeResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CapabilityReport:
    agent: str
    version: Optional[str]
    resume: bool
    dangerous_resume: bool
    detected_flags: tuple[str, ...]


@runtime_checkable
class AgentAdapter(Protocol):
    name: str

    def collect_sessions(self) -> list[dict[str, Any]]:
        ...

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        ...

    def compatibility(self) -> AgentCompatibility:
        ...


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
