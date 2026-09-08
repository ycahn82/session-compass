# Session Compass

[![PyPI](https://img.shields.io/pypi/v/session-compass)](https://pypi.org/project/session-compass/)

Session Compass is a local-first CLI for discovering, identifying, and resuming sessions created by Claude Code, Codex, Antigravity CLI, and Copilot CLI.

This project started as a fork of [cli-sessions](https://github.com/pavbyte/cli-sessions). It keeps the upstream project's practical local-session workflow while adding provider-specific metadata, resumability checks, and compatibility monitoring for independently updated agent CLIs.

## Why Session Compass?

Coding agents store useful session data locally, but each agent exposes that history differently. Session Compass gives you one starting point for answering:

- Which agent created this session?
- Which workspace was it using?
- What was the session about?
- When was it last active?
- Can it be resumed safely?

It is designed for local development machines and remote Linux servers accessed through SSH. It does not require a daemon, a central database, an account, or a web service.

## Install

Using `pipx` is recommended for command-line tools because it keeps Session Compass isolated from other Python applications:

```bash
pipx install session-compass
```

You can also install it with `pip`:

```bash
pip install session-compass
```

The repository includes an optional installer for machines where `pipx` is not already configured:

```bash
curl -fsSL https://raw.githubusercontent.com/ycahn82/session-compass/main/install.sh | bash
```

## Usage

```bash
scompass             # List sessions from all supported agents
scompass --claude    # Show Claude Code sessions
scompass --codex     # Show Codex sessions
scompass --agy       # Show Antigravity sessions
scompass --copilot   # Show Copilot CLI sessions
```

Choose a session number to resume it in its original working directory. Press `q` to exit without resuming.

Use `--include-unverified` when diagnosing records that do not have enough local evidence to be considered resumable:

```bash
scompass --include-unverified
```

### Permission bypass

Use `-d` as the short alias for `--dangerously-skip-permissions` when resuming a session:

```bash
scompass -d
scompass --claude -d
```

Session Compass translates this shared option to each provider's native permission-bypass option. This can reduce or remove safety prompts from the provider, so use it only in environments where you understand the consequences.

## Supported agents

Session Compass currently reads local session metadata from these locations:

```text
Claude Code:  ~/.claude/projects/*/*.jsonl
Codex:        ~/.codex/state_*.sqlite or ~/.codex/session_index.jsonl
Antigravity:  ~/.gemini/antigravity-cli/conversations/*.db and history.jsonl
Copilot CLI:  ~/.copilot/session-store.db
```

An agent that is not installed is skipped. Session databases are opened for metadata discovery only; Session Compass does not migrate, rewrite, or delete them.

The default list focuses on sessions with evidence that they can be resumed. Internal and metadata-only records are hidden from that list. Use `--include-unverified` to inspect diagnostic records without making them normal resume candidates.

## Local-first and privacy

Session Compass reads files already written on your machine. It does not send session content anywhere and does not include telemetry. The current implementation does not use an LLM to generate summaries; it prefers deterministic titles, previews, and user-message metadata already present in local storage.

## Compatibility policy

Agent CLIs can update independently, including their resume arguments and local storage schemas. Each Session Compass provider adapter owns its storage contract, metadata extraction, resumability evidence, and native resume command.

The project maintains separate compatibility floors for the provider CLI's resume command and its session-storage schema. GitHub Actions checks supported provider versions and help contracts weekly and on pull requests. When an upstream change breaks a contract, maintainers review the report and update the affected adapter; normal runtime execution does not probe provider help on every invocation.

## Current capabilities

- Unified session listing across supported coding agents
- Provider and workspace metadata
- Deterministic title and summary extraction from local records
- Resumability filtering for internal, incomplete, or metadata-only records
- Native resume command mapping per provider
- Shared `-d`/`--dangerously-skip-permissions` option
- Read-only compatibility and storage-contract tests

## Roadmap

The master plan is intentionally incremental. Planned work includes:

- Richer text search across agent, project, workspace, title, and branch metadata
- A stable machine-readable JSON output mode
- A read-only `doctor` diagnostic command
- Optional aggregation of session metadata from explicitly selected remote hosts
- Better provenance for workspace and Git context

These roadmap items are not required for the current interactive listing and resume workflow.

## Fork maintenance

The upstream project is [pavbyte/cli-sessions](https://github.com/pavbyte/cli-sessions). Session Compass keeps the upstream remote separate and documents intentional differences in the repository's development plans.

The public package and command are intentionally separate from the upstream project:

```text
Upstream cli-sessions:  pip install cli-sessions   -> sessions
Session Compass:        pip install session-compass -> scompass
```

Session Compass does not provide a `sessions` alias. This prevents a new installation from replacing or shadowing an existing upstream `cli-sessions` command.

## Links

- Source: https://github.com/ycahn82/session-compass
- Upstream: https://github.com/pavbyte/cli-sessions
- PyPI: https://pypi.org/project/session-compass/

## License

MIT
