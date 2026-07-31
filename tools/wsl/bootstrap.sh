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

# A bare `python` is not cosmetic here. Every command block in CLAUDE.md is written as
# `python tools/...`, that spelling is correct on Windows where this repo is also used,
# and Ubuntu ships no bare `python` at all. Measured 2026-07-31 in a fresh WSL session:
# `python tools/selfimprove/scan.py` died with "command not found" on the first command
# of the boot path. Fixed on the machine side rather than by rewriting the docs to
# `python3`, which would break the same block on the Windows clone.
#
# NOT in APT_WANT above, deliberately: under `set -e` a package this script cannot install
# (pinned image, distro without it, apt lock) would abort the whole run at step one, every
# run, which contradicts the resumability the header promises. Best-effort here, then the
# symlink catches every case where apt did not land it. Putting it in APT_WANT makes the
# fallback unreachable in precisely the situations it exists for.
log "python (CLAUDE.md's command block assumes it; Ubuntu ships only python3)"
if ! have python; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python-is-python3 || true
fi
if ! have python && have python3; then
  # Same idiom as fdfind above, and unprivileged, so it works with no sudo at all.
  echo "    apt did not supply it; linking python3 -> python"
  mkdir -p "$HOME/.local/bin"
  ln -sf "$(command -v python3)" "$HOME/.local/bin/python"
else
  have python && echo "    present: $(python --version 2>&1)"
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

log "browser bridge (WSL has no Linux browser, gh auth needs one)"
# `gh auth login` calls xdg-open, which walks a list of Linux browsers and finds none
# under WSL, so the device-code URL never opens and the flow dead-ends. Bouncing to the
# Windows browser fixes it for gh and for anything else that honours $BROWSER. A URL is
# not a filesystem path, so handing it to a Windows binary is safe; do not extend this
# to files.
for cand in   "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"   "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
do
  if [ -x "$cand" ]; then WINBROWSER="$cand"; break; fi
done
if [ -n "${WINBROWSER:-}" ]; then
  mkdir -p "$HOME/.local/bin"
  {
    echo '#!/usr/bin/env bash'
    echo "exec \"$WINBROWSER\" \"\$@\""
  } > "$HOME/.local/bin/wsl-browser"
  chmod +x "$HOME/.local/bin/wsl-browser"
  echo "    bridged to $(basename "$WINBROWSER")"
else
  echo "    no Windows browser found; enter the gh device code by hand"
fi

log "environment"
# ~/.profile, NOT ~/.bashrc. Ubuntu's stock .bashrc returns at line 8 for any
# non-interactive shell:
#     case $- in *i*) ;; *) return;; esac
# so anything appended to its tail never runs under `bash -lc`, which is exactly how
# the WSL lane shortcuts and every scripted invocation start a shell. Measured
# 2026-07-31: BROWSER was written to .bashrc and came back empty from `bash -lc`,
# while PATH still worked only because .profile:25 adds ~/.local/bin independently.
PROFILE="$HOME/.profile"
add_env() {
  grep -qF "$1" "$PROFILE" 2>/dev/null || { echo "$1" >> "$PROFILE"; echo "    added: $1"; }
}
add_env 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"'
add_env 'export BROWSER="$HOME/.local/bin/wsl-browser"'

log "Verification"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"
fail=0
for t in git python python3 pip3 pytest uv gh rg fd cargo rustc node claude; do
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
log "Done. Open a new shell or run: source ~/.profile"
