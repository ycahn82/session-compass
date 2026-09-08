"""Probe installed agent CLIs using version and help commands only."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from cli_sessions.agents.base import AgentAdapter
from cli_sessions.agents.registry import get_adapters


VERSION_RE = re.compile(r"(?<!\d)(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)")


def _run_read_only_command(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)


def _extract_version(output: str) -> Optional[str]:
    match = VERSION_RE.search(output)
    return match.group(1) if match else None


def probe_agent(
    adapter: AgentAdapter, executable_dir: Optional[Path] = None, timeout: float = 10.0
) -> dict[str, Any]:
    executable = shutil.which(adapter.executable, path=str(executable_dir) if executable_dir else None)
    result: dict[str, Any] = {
        "agent": adapter.name,
        "version": None,
        "resume": False,
        "dangerous_resume": False,
        "detected_flags": [],
        "missing_flags": list(adapter.required_help_flags),
        "status": "fail",
    }
    if executable is None:
        result["failure"] = "executable_not_found"
        return result

    try:
        version_result = _run_read_only_command([executable, "--version"], timeout)
        help_result = _run_read_only_command([executable, "--help"], timeout)
    except subprocess.TimeoutExpired:
        result["failure"] = "timeout"
        return result
    except OSError:
        result["failure"] = "execution_error"
        return result

    version_output = f"{version_result.stdout}\n{version_result.stderr}"
    help_output = f"{help_result.stdout}\n{help_result.stderr}"
    result["version"] = _extract_version(version_output)
    detected = [flag for flag in adapter.required_help_flags if flag in help_output]
    result["detected_flags"] = detected
    result["missing_flags"] = [flag for flag in adapter.required_help_flags if flag not in detected]
    result["resume"] = adapter.required_help_flags[0] in detected
    result["dangerous_resume"] = adapter.required_help_flags[1] in detected
    if version_result.returncode != 0:
        result["failure"] = "version_command_failed"
    elif help_result.returncode != 0:
        result["failure"] = "help_command_failed"
    elif result["version"] is None:
        result["failure"] = "version_not_detected"
    elif result["missing_flags"]:
        result["failure"] = "required_flag_missing"
    else:
        result["status"] = "pass"
        result.pop("failure", None)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = [probe_agent(adapter, args.executable_dir, args.timeout) for adapter in get_adapters()]
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    sys.exit(0 if all(result["status"] == "pass" for result in report) else 1)


if __name__ == "__main__":
    main()
