"""Build a bounded, sanitized compatibility report for maintainer automation."""

import argparse
import json
import re
from pathlib import Path
from typing import Any


UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
SECRET_RE = re.compile(r"\b(?:sk|ghp|github_pat)[_-][A-Za-z0-9_-]+\b")
PATH_RE = re.compile(r"(?<!\w)(?:/Users|/home|/tmp|[A-Z]:\\)[^\s,;]+")


def sanitize_text(value: str) -> str:
    value = PATH_RE.sub("<path>", value)
    value = UUID_RE.sub("<uuid>", value)
    value = SECRET_RE.sub("<secret>", value)
    return value[:200]


def sanitize_report(results: list[dict[str, Any]], commit_sha: str = "unknown") -> dict[str, Any]:
    allowed = {"agent", "version", "resume", "dangerous_resume", "detected_flags", "missing_flags", "status", "failure"}
    sanitized_results = []
    for result in results:
        item = {key: result[key] for key in allowed if key in result}
        if isinstance(item.get("failure"), str):
            item["failure"] = sanitize_text(item["failure"])
        sanitized_results.append(item)
    return {"commit_sha": commit_sha, "results": sanitized_results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--commit-sha", default="unknown")
    args = parser.parse_args()
    raw = json.loads(args.report.read_text(encoding="utf-8"))
    print(json.dumps(sanitize_report(raw, args.commit_sha), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
