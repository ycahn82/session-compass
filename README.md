# cli-sessions

List and resume your **Claude Code**, **Codex**, **Antigravity** (`agy`), and **Copilot CLI** sessions from one place.

Each of these tools prints a session ID when you quit, with no built-in way to browse past sessions across tools. `sessions` scans each tool's local session storage and gives you one sorted, searchable list.

## Install

```bash
pip install cli-sessions
```

## Usage

```bash
sessions            # all sessions, oldest first, most recent last
sessions --claude    # only Claude Code
sessions --codex     # only Codex
sessions --agy       # only Antigravity
sessions --copilot   # only Copilot CLI
```

Pick a number to resume that session — `sessions` runs the right resume command (`claude --resume`, `codex resume`, `agy --conversation`, or `copilot --resume=`) in the session's original working directory.

## How it works

Nothing is sent anywhere. `sessions` only reads local session files each tool already writes:

- Claude Code: `~/.claude/projects/*/*.jsonl`
- Codex: `~/.codex/state_*.sqlite` (or `~/.codex/session_index.jsonl` as a fallback)
- Antigravity: `~/.gemini/antigravity-cli/conversations/*.db` + `history.jsonl`
- Copilot CLI: `~/.copilot/session-store.db`

## License

MIT
