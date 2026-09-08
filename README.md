# cli-sessions

[![PyPI](https://img.shields.io/pypi/v/cli-sessions)](https://pypi.org/project/cli-sessions/)

List and resume your **Claude Code**, **Codex**, **Antigravity** (`agy`), and **Copilot CLI** sessions from one place.

Each of these tools prints a session ID when you quit, with no built-in way to browse past sessions across tools. `sessions` scans each tool's local session storage and gives you one sorted list — most recent at the bottom, like `ls -ltrh` — so you can pick one and jump straight back in.

```
 1) [codex  ] 12d ago   ~/Developer/junit-framework      Learn Java fundamentals in JUnit
    id: 019f82f2-cbb4-71b2-a9e2-1060c05d8ac5
 2) [claude ] 1h ago    ~/Developer/opensre              Diagnose code issue
    id: 578822f7-3665-42a8-8223-b51c59faf644
 3) [agy    ] 47m ago   ~/Developer/ticket-booking       help me learn java from scratch
    id: d5d954dd-6fe6-4e2d-9325-d9f63fb5abcb
 4) [copilot] 7m ago    ~                                Session Initialization
    id: d8567a02-d999-414a-af89-b02d440ebcf1

Resume which session? (number, or q to quit):
```

## Install

Pick whichever fits how you manage Python tools. All three install the same `sessions` command.

**One-line install (recommended if you don't already use pip/pipx)**

Bootstraps `pipx` if it's missing, then installs `cli-sessions` — no manual setup:

```bash
curl -fsSL https://raw.githubusercontent.com/pavbyte/cli-sessions/main/install.sh | bash
```

**Using pipx** (if you already have it, or prefer installing CLI tools in their own isolated environment):

```bash
pipx install cli-sessions
```

**Using pip:**

```bash
pip install cli-sessions
# or, if `pip` isn't found but `pip3` is:
pip3 install --user cli-sessions
```

> With `pip install --user`, the `sessions` command may land in a directory that isn't on your `PATH` yet (e.g. `~/.local/bin` on Linux, `~/Library/Python/3.x/bin` on macOS). If `sessions` isn't found after installing, add that directory to your `PATH`, or just use `pipx`/the one-line installer instead, which handle this for you.

## Usage

```bash
sessions             # all sessions, oldest first, most recent last
sessions --claude     # only Claude Code
sessions --codex      # only Codex
sessions --agy        # only Antigravity
sessions --copilot    # only Copilot CLI
sessions --include-unverified  # include records without verified resume evidence
sessions -d           # resume with each agent's native dangerous permission bypass
```

`-d` is a short alias for `--dangerously-skip-permissions`. It applies the
corresponding native permission-bypass option for the selected agent.

Pick a number to resume that session — `sessions` runs the right resume command (`claude --resume`, `codex resume`, `agy --conversation`, or `copilot --resume=`) in the session's original working directory.

## How it works

Nothing is sent anywhere, and there's no telemetry. `sessions` only reads local session files each tool already writes to disk:

- Claude Code: `~/.claude/projects/*/*.jsonl`
- Codex: `~/.codex/state_*.sqlite` (or `~/.codex/session_index.jsonl` as a fallback)
- Antigravity: `~/.gemini/antigravity-cli/conversations/*.db` + `history.jsonl`
- Copilot CLI: `~/.copilot/session-store.db`

Any tool you don't have installed is silently skipped — you only see entries for what's actually on your machine.

## Supported CLI compatibility

`cli-sessions` keeps each service integration in its own adapter. The version
floor below is the first version verified in this repository with the current
resume command and storage contract; it is a conservative support floor, not a
claim that every older release is compatible.

| Service | `resume_min_version` | `storage_min_version` | `tested_latest_version` | Official reference |
|---|---:|---:|---:|---|
| Claude Code | `2.1.263` | `2.1.263` | `2.1.263` | [CLI usage](https://docs.anthropic.com/en/docs/claude-code/cli-usage), [npm package](https://www.npmjs.com/package/@anthropic-ai/claude-code) |
| Codex | `0.153.4` | `0.153.4` | `0.153.4` | [Codex CLI](https://developers.openai.com/codex/cli/), [npm package](https://www.npmjs.com/package/@openai/codex) |
| Antigravity (`agy`) | `1.1.27` | `1.1.27` | `1.1.27` | [Using AGY CLI](https://antigravity.google/docs/cli/using/), [headless flags](https://antigravity.google/docs/cli/headless/) |
| Copilot CLI | `1.0.82` | `1.0.82` | `1.0.82` | [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference), [npm package](https://www.npmjs.com/package/@github/copilot) |

`tested_latest_version` is diagnostic only and will be refreshed by the weekly
compatibility workflow. Newer service versions are not rejected by a maximum
version allowlist. The workflow checks the required resume and native
permission flags instead. If a service changes its CLI arguments or storage
schema, maintainers update only that service's adapter and add a regression
fixture; the workflow then reports the change without modifying user data.

Users should update each service CLI independently when they choose. Updating a
service does not update `cli-sessions` at runtime. The weekly maintainer check
will detect supported capability changes and open or update a GitHub Issue when
the adapter needs attention. Runtime never runs a service's `--help` probe or
writes to its session database.

## Links

- Source: https://github.com/pavbyte/cli-sessions
- PyPI: https://pypi.org/project/cli-sessions/

## License

MIT
