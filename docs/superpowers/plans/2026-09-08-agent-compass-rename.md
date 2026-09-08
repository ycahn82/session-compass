# Agent Compass Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the forked `cli-sessions` project to `agent-compass`, expose the `acompass` CLI, separate the Python import namespace, and document the product purpose in English without providing the legacy `sessions` command.

**Architecture:** Preserve the existing agent adapters and session behavior while moving the source package from `cli_sessions` to `agent_compass`. Update packaging, tests, installer, README, and the master plan as one public-contract change; perform the GitHub repository rename only after local and CI-compatible validation succeeds.

**Tech Stack:** Python 3.9 standard library, Hatchling, `unittest`, wheel build, GitHub Actions, GitHub CLI, Markdown.

## Global Constraints

- The PyPI distribution name is exactly `agent-compass`.
- The Python import package is exactly `agent_compass`.
- The only new public CLI command is exactly `acompass`; do not add `sessions` as an alias.
- Public-facing README, PyPI metadata, CLI help, and user-facing messages are written in English.
- The project remains a fork of upstream `pavbyte/cli-sessions`, and that relationship is documented in README.
- Existing collectors, storage parsing, resumability filtering, and native dangerous-permission mappings must remain behaviorally unchanged.
- Do not modify user session databases or run real resume/model commands during tests.
- The source package must not share the `cli_sessions` import namespace with the upstream distribution.
- The implementation workspace is `/home/ycahn/tools/cli-sessions-agent-compass` on branch `feat/agent-compass-rename`.
- The reference checkout `/home/ycahn/tools/cli-sessions` and unrelated workspaces `/home/ycahn/codes/Quote` and `/home/ycahn/codes/PPLL` are not modified.
- The upstream remote remains `https://github.com/pavbyte/cli-sessions.git`.

---

## File Map

| File or directory | Responsibility after this plan |
| --- | --- |
| `src/agent_compass/` | Renamed runtime package containing CLI and per-agent adapters |
| `tests/` | Regression tests using the new import namespace and public CLI contract |
| `scripts/probe_cli_compatibility.py` | Compatibility probe importing `agent_compass` |
| `pyproject.toml` | Distribution metadata, `acompass` entry point, wheel package list |
| `install.sh` | Optional pipx installer for `agent-compass` and `acompass` |
| `README.md` | English product, installation, usage, fork, compatibility, and roadmap documentation |
| `cli-sessions-customization-master-plan.md` | Internal master plan with Agent Compass product/command naming |
| `docs/superpowers/specs/2026-09-08-agent-compass-rename-design.md` | Approved rename design |
| `docs/superpowers/plans/2026-09-08-agent-compass-rename.md` | This implementation plan |

---

### Task 1: Add the new public-package contract tests

**Files:**
- Create: `tests/test_public_packaging.py`

**Interfaces:**
- Consumes: the future `agent_compass` package and the repository `pyproject.toml` metadata.
- Produces: failing tests that define the required import namespace, entry point, and absence of the legacy command.

- [ ] **Step 1: Write the failing tests**

```python
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicPackagingTests(unittest.TestCase):
    def test_agent_compass_is_the_runtime_namespace(self):
        self.assertTrue((ROOT / "src" / "agent_compass").is_dir())
        self.assertFalse((ROOT / "src" / "cli_sessions").exists())

    def test_module_help_uses_public_agent_compass_module(self):
        result = subprocess.run(
            [sys.executable, "-m", "agent_compass.cli", "--help"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dangerously-skip-permissions", result.stdout)
        self.assertIn("-d", result.stdout)

    def test_packaging_metadata_exposes_acompass_only(self):
        metadata = (ROOT / "pyproject.toml").read_text()
        self.assertIn('name = "agent-compass"', metadata)
        self.assertIn('acompass = "agent_compass.cli:main"', metadata)
        self.assertNotIn('sessions = "cli_sessions.cli:main"', metadata)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify the expected failure**

Run:

```bash
cd /home/ycahn/tools/cli-sessions-agent-compass
PYTHONPATH=src python -m unittest tests.test_public_packaging -v
```

Expected: FAIL because the current checkout still exposes `cli_sessions` and `sessions`.

- [ ] **Step 3: Commit the contract tests**

```bash
git add tests/test_public_packaging.py
git commit -m "test: define agent-compass public package contract"
```

### Task 2: Move the runtime package and update all Python imports

**Files:**
- Rename: `src/cli_sessions/` -> `src/agent_compass/`
- Modify: `src/agent_compass/__init__.py`
- Modify: `src/agent_compass/cli.py`
- Modify: `src/agent_compass/agents/*.py`
- Modify: `scripts/probe_cli_compatibility.py`
- Modify: every test file importing `cli_sessions`

**Interfaces:**
- Consumes: existing module APIs and adapter behavior.
- Produces: the same functions/classes under `agent_compass`, including `agent_compass.cli.main`, `agent_compass.agents.registry.get_adapters`, and all existing adapter classes.

- [ ] **Step 1: Move the package without changing implementation logic**

```bash
git mv src/cli_sessions src/agent_compass
```

- [ ] **Step 2: Replace only namespace references**

Replace these exact import forms throughout `tests/` and `scripts/probe_cli_compatibility.py`:

```text
from cli_sessions                 -> from agent_compass
from cli_sessions.                -> from agent_compass.
import cli_sessions                -> import agent_compass
cli_sessions.                     -> agent_compass.
```

Do not change adapter function names, SQL queries, storage paths, resume arguments, fixtures, or test semantics.

- [ ] **Step 3: Update package docstrings**

Use English docstrings:

```python
"""List and resume local sessions from supported coding agents."""
```

and in `src/agent_compass/cli.py`:

```python
"""List and resume Claude Code, Codex, Antigravity, and Copilot CLI sessions."""
```

- [ ] **Step 4: Run import and regression tests**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected: the new public packaging tests may still fail until Task 3 updates metadata; all existing adapter tests must import successfully.

- [ ] **Step 5: Commit the namespace move**

```bash
git add src tests scripts/probe_cli_compatibility.py
git commit -m "refactor: move runtime namespace to agent_compass"
```

### Task 3: Update packaging metadata, installer, and CLI entry point

**Files:**
- Modify: `pyproject.toml`
- Modify: `install.sh`
- Test: `tests/test_public_packaging.py`

**Interfaces:**
- Consumes: `agent_compass.cli:main` from Task 2.
- Produces: a wheel that installs `agent_compass` and creates only the `acompass` executable.

- [ ] **Step 1: Update `pyproject.toml`**

The relevant sections must become:

```toml
[project]
name = "agent-compass"
description = "Discover and resume local sessions from Claude Code, Codex, Antigravity, and Copilot CLI"
readme = "README.md"
keywords = ["cli", "coding-agents", "claude-code", "codex", "copilot", "antigravity", "sessions", "resume"]

[project.scripts]
acompass = "agent_compass.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_compass"]
```

Preserve the current version, Python requirement, license, authors, and classifiers unless a later release decision explicitly changes them.

- [ ] **Step 2: Update `install.sh`**

Change all user-facing and installation references as follows:

```bash
# Installs the `acompass` CLI (agent-compass on PyPI).
python3 -m pipx install --force agent-compass
if command -v acompass >/dev/null 2>&1; then
  info "Done. Run 'acompass' to get started."
fi
```

The PATH warning must also instruct the user to run `acompass`, never `sessions`.

- [ ] **Step 3: Run the public contract tests**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_public_packaging -v
```

Expected: all public packaging tests PASS.

- [ ] **Step 4: Build the wheel and inspect its contents**

Run:

```bash
rm -rf /tmp/agent-compass-wheel
python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/agent-compass-wheel
python3 -m zipfile -l /tmp/agent-compass-wheel/agent_compass-*.whl
```

Expected: the wheel contains `agent_compass/` and does not contain `cli_sessions/`.

- [ ] **Step 5: Commit packaging changes**

```bash
git add pyproject.toml install.sh tests/test_public_packaging.py
git commit -m "feat: publish agent-compass as acompass"
```

### Task 4: Rewrite the public README in English

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the public names and behavior from Tasks 2 and 3, plus the compatibility design and master plan.
- Produces: an English README that users can follow without knowing the upstream implementation.

- [ ] **Step 1: Replace the title and badges**

The beginning must identify the project as:

```markdown
# Agent Compass

[![PyPI](https://img.shields.io/pypi/v/agent-compass)](https://pypi.org/project/agent-compass/)
```

- [ ] **Step 2: Add the English product purpose and fork statement**

Include prose with these facts:

```markdown
Agent Compass is a local-first CLI for discovering, identifying, and resuming sessions created by Claude Code, Codex, Antigravity CLI, and Copilot CLI.

This project started as a fork of [cli-sessions](https://github.com/pavbyte/cli-sessions). It keeps the upstream project's practical local-session workflow while adding provider-specific metadata, resumability checks, and compatibility monitoring for independently updated agent CLIs.
```

- [ ] **Step 3: Document installation and usage with only `acompass`**

Use these command forms:

```bash
pipx install agent-compass
pip install agent-compass

acompass
acompass --claude
acompass --codex
acompass --agy
acompass --copilot
acompass -d
```

Explain that `-d` is the short alias for `--dangerously-skip-permissions`, and that the option is translated to each provider's native flag only when resuming. Include a concise warning that it reduces the provider's permission safeguards.

- [ ] **Step 4: Document local-first behavior and current storage sources**

Explain in English that Agent Compass reads local metadata only, does not send data or use telemetry, and does not modify session databases. Document the current storage locations:

```text
Claude Code:       ~/.claude/projects/*/*.jsonl
Codex:             ~/.codex/state_*.sqlite or ~/.codex/session_index.jsonl
Antigravity:       ~/.gemini/antigravity-cli/conversations/*.db and history.jsonl
Copilot CLI:       ~/.copilot/session-store.db
```

State that internal and metadata-only records are hidden from the default resume list, while diagnostic records can be inspected with `--include-unverified`.

- [ ] **Step 5: Add compatibility policy and roadmap**

Include English sections named `Compatibility policy`, `Current capabilities`, `Roadmap`, and `Fork maintenance`. State that:

1. Each provider adapter owns its storage contract and resume command.
2. Minimum supported provider CLI versions are documented separately from storage-schema floors.
3. GitHub Actions checks public provider CLI versions and help contracts weekly and on pull requests.
4. Failures are reviewed and fixed by maintainers; runtime does not probe provider help on every invocation.
5. Planned work includes richer search, stable JSON output, doctor diagnostics, and optional remote aggregation.

- [ ] **Step 6: Validate README naming and links**

Run:

```bash
rg -n 'agent-compass|agent_compass|acompass|pavbyte/cli-sessions' README.md
```

Expected: all install and usage examples use `agent-compass`/`acompass`; `cli-sessions` appears only in the upstream fork explanation/link.

- [ ] **Step 7: Commit the README**

```bash
git add README.md
git commit -m "docs: introduce Agent Compass product README"
```

### Task 5: Update the master plan and internal naming references

**Files:**
- Modify: `cli-sessions-customization-master-plan.md`
- Do not rewrite historical compatibility spec/plan files unless they contain current user-facing instructions that would mislead a new user.

**Interfaces:**
- Consumes: the approved rename design and the English README terminology.
- Produces: a master plan whose product name is Agent Compass and whose current/future command examples use `acompass`.

- [ ] **Step 1: Update the master-plan title and product references**

Change the title to:

```markdown
# Agent Compass 커스텀 마스터 플랜
```

In Korean internal prose, use `Agent Compass` for the product and reserve `cli-sessions` for the upstream project.

- [ ] **Step 2: Update command examples**

Replace current product command examples such as:

```text
sessions
sessions --claude
sessions doctor
ais
```

with:

```text
acompass
acompass --claude
acompass doctor
```

Do not claim that `doctor`, JSON output, remote aggregation, or other future phases are already implemented. Mark them as roadmap phases where appropriate.

- [ ] **Step 3: Preserve upstream references accurately**

Keep `cli-sessions` in sections that describe the upstream repository, fork relationship, or original source history. Do not replace those references with `Agent Compass`.

- [ ] **Step 4: Validate and commit the master plan**

Run:

```bash
git diff --check
rg -n 'Agent Compass|acompass|cli-sessions' cli-sessions-customization-master-plan.md | head -80
```

Expected: product-facing examples use `acompass`, while upstream references remain `cli-sessions`.

```bash
git add cli-sessions-customization-master-plan.md
git commit -m "docs: align master plan with Agent Compass"
```

### Task 6: Run isolated installation and complete local verification

**Files:**
- No source changes expected.
- Inspect: all changed files and generated wheel contents.

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: evidence that the rename preserves runtime behavior and changes only the public names/documentation.

- [ ] **Step 1: Run all unit tests with warnings enabled**

```bash
cd /home/ycahn/tools/cli-sessions-agent-compass
PYTHONWARNINGS=error::ResourceWarning PYTHONPATH=src:. python -m unittest discover -s tests -v
```

Expected: all tests pass, including the original adapter/compatibility tests and the new packaging tests.

- [ ] **Step 2: Build and install the wheel in a temporary virtual environment**

```bash
temp_venv=$(mktemp -d)
python3 -m venv "$temp_venv"
python3 -m pip wheel --no-deps --no-build-isolation . -w /tmp/agent-compass-wheel
"$temp_venv/bin/python" -m pip install --no-deps /tmp/agent-compass-wheel/agent_compass-*.whl
"$temp_venv/bin/acompass" --help
test ! -e "$temp_venv/bin/sessions"
"$temp_venv/bin/python" -c 'import agent_compass'
if "$temp_venv/bin/python" -c 'import cli_sessions' 2>/dev/null; then exit 1; fi
python3 -m zipfile -l /tmp/agent-compass-wheel/agent_compass-*.whl | rg 'agent_compass/|cli_sessions/'
rm -rf "$temp_venv"
```

Expected: `acompass --help` succeeds, `sessions` is not installed, `agent_compass` imports successfully, `cli_sessions` does not import, and the wheel contains `agent_compass/` but not `cli_sessions/`.

- [ ] **Step 3: Verify no stale public references remain**

```bash
rg -n 'cli_sessions|sessions = "|pipx install cli-sessions|pip install cli-sessions|Run .sessions.|github.com/ycahn82/cli-sessions|pypi.org/project/cli-sessions' \
  pyproject.toml install.sh README.md src tests scripts .github cli-sessions-customization-master-plan.md
```

Expected: no stale runtime/package references. Intentional upstream references in README/master plan and the `upstream` remote are allowed and must be reviewed manually.

- [ ] **Step 4: Commit any final verification-only fixes**

```bash
git status --short
git diff --check
git add pyproject.toml install.sh README.md src tests scripts cli-sessions-customization-master-plan.md
git commit -m "chore: finalize Agent Compass rename"  # only if the previous checks required a fix
```

### Task 7: Push the branch and perform the GitHub repository rename

**Files/remote state:**
- Remote repository: `ycahn82/cli-sessions` -> `ycahn82/agent-compass`
- Local Git config: update `origin`; preserve `upstream`

**Interfaces:**
- Consumes: a clean, fully tested `feat/agent-compass-rename` branch from Task 7.
- Produces: the renamed GitHub repository and remotes that point to the correct fork/upstream boundary.

- [ ] **Step 1: Confirm authentication and clean state before the external rename**

```bash
cd /home/ycahn/tools/cli-sessions-agent-compass
git status --short --branch
gh auth status
git remote -v
```

Expected: the worktree is clean, GitHub authentication is valid, `origin` is the current fork, and `upstream` is `pavbyte/cli-sessions`.

- [ ] **Step 2: Push the implementation branch before renaming**

```bash
git push -u origin feat/agent-compass-rename
```

Expected: the branch is visible on the current fork before the repository operation.

- [ ] **Step 3: Rename the GitHub repository**

```bash
gh repo rename agent-compass --repo ycahn82/cli-sessions --yes
```

Expected: GitHub reports the repository as `ycahn82/agent-compass` and retains the existing history.

- [ ] **Step 4: Update and verify local remotes**

```bash
git remote set-url origin git@github.com:ycahn82/agent-compass.git
git remote set-url upstream https://github.com/pavbyte/cli-sessions.git
git remote -v
git ls-remote --heads origin feat/agent-compass-rename
git ls-remote --heads upstream main
gh repo view ycahn82/agent-compass --json nameWithOwner,url,defaultBranchRef
```

Expected: `origin` resolves to `ycahn82/agent-compass`, `upstream` resolves to `pavbyte/cli-sessions`, and both remote checks succeed.

- [ ] **Step 5: Do not commit local remote configuration**

`.git/config` is repository-local state and is not committed. Record the verified remote URLs in the final handoff instead.

### Task 8: Final handoff and integration readiness

**Files:**
- Inspect: all commits on `feat/agent-compass-rename`
- Optional: GitHub pull request description

**Interfaces:**
- Consumes: local test evidence and verified GitHub remotes.
- Produces: a review-ready branch with an explicit migration story and no `sessions` alias.

- [ ] **Step 1: Produce the final evidence summary**

Record:

```text
branch: feat/agent-compass-rename
distribution: agent-compass
import: agent_compass
command: acompass
legacy command supplied: no
full unit tests: passed
wheel namespace: agent_compass only
origin: git@github.com:ycahn82/agent-compass.git
upstream: https://github.com/pavbyte/cli-sessions.git
```

- [ ] **Step 2: Open a pull request only after the local evidence is complete**

Use a PR title such as:

```text
Rename fork to Agent Compass and publish acompass CLI
```

The PR body must state that the change preserves session collection/resume behavior, changes the public package/import/CLI names, intentionally does not provide `sessions`, and keeps the upstream fork relationship documented.

- [ ] **Step 3: Stop for review before merging or publishing to PyPI**

Do not merge the PR or publish `agent-compass` to PyPI in this plan execution without a separate explicit release decision.

---

## Plan Self-Review

- The design requirement for English public documentation is covered by Tasks 4 and 5 and the global constraints.
- The no-`sessions` decision is covered by Tasks 1, 3, 4, 6, and 8.
- Package namespace separation is covered by Tasks 1, 2, 3, and 6.
- GitHub repository rename and remote separation are covered by Task 7.
- Existing provider behavior is protected by the full test suite in Task 6.
- No automatic migration, PyPI publish, or unrelated feature work is required.
