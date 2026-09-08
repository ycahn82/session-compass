#!/usr/bin/env bash
# Installs the `scompass` CLI (session-compass on PyPI).
# Usage: curl -fsSL <raw-url-to-this-file> | bash

set -euo pipefail

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
fail()  { printf '\033[1;31mError:\033[0m %s\n' "$1" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 is required but not found. Install Python 3.9+ first (e.g. 'brew install python' on macOS), then re-run this script."

if ! python3 -m pipx --version >/dev/null 2>&1; then
  info "Installing pipx..."
  python3 -m pip install --user --quiet pipx
  python3 -m pipx ensurepath
  PIPX_JUST_INSTALLED=1
else
  PIPX_JUST_INSTALLED=0
fi

info "Installing session-compass via pipx..."
python3 -m pipx install --force session-compass

if command -v scompass >/dev/null 2>&1; then
  info "Done. Run 'scompass' to get started."
elif [ "$PIPX_JUST_INSTALLED" = "1" ]; then
  warn "pipx was just installed and updated your shell's PATH config, but this terminal session hasn't picked it up yet."
  warn "Restart your terminal (or run 'exec \$SHELL -l'), then run: scompass"
else
  warn "Installed, but 'scompass' isn't on PATH yet. Restart your terminal, or run: python3 -m pipx ensurepath && exec \$SHELL -l"
fi
