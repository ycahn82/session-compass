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


@dataclass(frozen=True)
class ContractReport:
    agent: str
    ok: bool
    missing: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ResumeStatus(Enum):
    RESUMABLE = "resumable"
    LIKELY_RESUMABLE = "likely_resumable"
    METADATA_ONLY = "metadata_only"
    INVALID = "invalid"


@runtime_checkable
class AgentAdapter(Protocol):
    name: str

    def collect_sessions(self) -> list[dict[str, Any]]:
        ...

    def build_resume_command(self, session_id: str, dangerous: bool = False) -> list[str]:
        ...

    def compatibility(self) -> AgentCompatibility:
        ...

    def check_storage_contract(self, path: Path) -> ContractReport:
        ...


def classify_resumability(session: dict[str, Any]) -> ResumeStatus:
    """Classify resume evidence without treating a summary as resume evidence."""
    if session.get("record_kind") in {"bridge_session", "metadata_only"}:
        return ResumeStatus.METADATA_ONLY
    if session.get("has_conversation_content") is False:
        return ResumeStatus.METADATA_ONLY
    if session.get("has_rollout") is False:
        return ResumeStatus.INVALID
    if any(
        session.get(field) is True
        for field in ("has_conversation_content", "has_rollout", "has_session_record")
    ):
        return ResumeStatus.RESUMABLE
    if session.get("record_kind") == "conversation":
        return ResumeStatus.LIKELY_RESUMABLE
    return ResumeStatus.INVALID


def filter_resume_candidates(
    sessions: list[dict[str, Any]], include_unverified: bool = False
) -> list[dict[str, Any]]:
    """Return verified candidates by default, retaining original record objects."""
    if include_unverified:
        return list(sessions)
    return [
        session
        for session in sessions
        if classify_resumability(session)
        in {ResumeStatus.RESUMABLE, ResumeStatus.LIKELY_RESUMABLE}
    ]


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
