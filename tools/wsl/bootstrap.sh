#!/usr/bin/env bash
# WSL bootstrap for the claude-setup harness. ONE password prompt, then unattended.
#
# Why a script and not a Makefile target that shells out per package: every `sudo apt
# install` is its own password prompt unless the credential is cached first. `sudo -v`
# caches it once and the keepalive below holds it for the length of the run, so the
# operator types the password a single time and walks away. A Makefile is still the
# right ENTRY POINT (see tools/wsl/Makefile) but it must call one script, not ten
# privileged commands.
#
# Idempotent by construction: every step checks before it acts, so re-running after a
# partial failure resumes instead of restarting. Run it as the normal user, not as root.
#
#   bash tools/wsl/bootstrap.sh
#
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Run as your normal user, not root. It will ask for sudo once." >&2
  exit 2
fi

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

log "Caching sudo credentials (one prompt for the whole run)"
sudo -v
# Keepalive: refresh the timestamp until this script exits, so a long apt run does not
# hit the 15 minute default timeout and re-prompt halfway through.
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &
SUDO_KEEPALIVE=$!
trap 'kill "$SUDO_KEEPALIVE" 2>/dev/null || true' EXIT

log "apt packages"
APT_WANT=(python3-pip python3-venv ripgrep fd-find build-essential pkg-config libssl-dev)
APT_MISSING=()
for p in "${APT_WANT[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || APT_MISSING+=("$p")
done
if [ ${#APT_MISSING[@]} -gt 0 ]; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_MISSING[@]}"
else
  echo "    all present, nothing to install"
fi

# Ubuntu ships fd as fdfind because the name fd was taken. Every doc and every muscle
# memory says fd, so alias it rather than teaching the difference.
if have fdfind && ! have fd; then
  log "linking fdfind -> fd"
  mkdir -p "$HOME/.local/bin"
  ln -sf "$(command -v fdfind)" "$HOME/.local/bin/fd"
fi

log "gh (GitHub CLI, not in the default Ubuntu archive)"
if ! have gh; then
  sudo mkdir -p -m 755 /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y gh
else
  echo "    present: $(gh --version | head -1)"
fi

log "uv (the repo's Python package manager per CLAUDE.md)"
if ! have uv && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
else
  echo "    present"
fi

log "pytest, for the gate's unit domain"
if ! python3 -c "import pytest" >/dev/null 2>&1; then
  python3 -m pip install --user --break-system-packages pytest
else
  echo "    present"
fi

log "PATH"
BASHRC="$HOME/.bashrc"
add_path() {
  grep -qF "$1" "$BASHRC" 2>/dev/null || { echo "$1" >> "$BASHRC"; echo "    added: $1"; }
}
add_path 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"'

log "Verification"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"
fail=0
for t in git python3 pip3 pytest uv gh rg fd cargo rustc node claude; do
  if have "$t"; then
    printf '  %-8s ok   %s\n' "$t" "$($t --version 2>&1 | head -1 | cut -c1-46)"
  else
    printf '  %-8s MISSING\n' "$t"
    fail=1
  fi
done

log "Harness self-check in the cloned repo"
REPO="${CLAUDE_SETUP:-$HOME/claude-setup}"
if [ -d "$REPO" ]; then
  cd "$REPO"
  python3 tools/map/codemap.py check 2>&1 | tail -1
  python3 tools/gate/gate.py status 2>&1 | tail -1
else
  echo "    $REPO not found; clone it first"
fi

if [ "$fail" -ne 0 ]; then
  echo
  echo "Some tools are still missing. Re-run this script; it resumes." >&2
  exit 1
fi
log "Done. Open a new shell or run: source ~/.bashrc"
