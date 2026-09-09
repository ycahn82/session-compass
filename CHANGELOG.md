# Changelog

All notable changes to Session Compass are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.1] - 2026-09-09

### Fixed

- **`agy` sessions no longer disappear while Antigravity's UI catalog catches up.** Antigravity
  records a brand-new conversation's raw data (its `.db` file and `history.jsonl` entries)
  immediately, but only writes a matching row into its own `conversation_summaries.db` catalog
  asynchronously, sometimes hours later. `scompass` required that catalog row to list a session
  at all, so freshly created `agy` sessions were silently invisible until the catalog caught up.
  `agy` sessions now fall back to `history.jsonl` for their working directory and summary when
  the catalog entry isn't there yet.
- **`agy` session summaries no longer show "(no summary available)" for freshly created
  sessions.** Antigravity only tags a `history.jsonl` entry with its `conversationId` once the id
  has been assigned, so a session's opening message(s) were logged without one and dropped from
  summary lookup entirely. Untagged opening entries are now attributed retroactively once a later
  entry in the same session (e.g. `/rename` or `/exit`) carries the id.
