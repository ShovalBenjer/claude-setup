#!/usr/bin/env bash
# Pick a workspace, then start Claude in it with the lane DECLARED.
#
# The Linux counterpart of Start-Claude.ps1, for kitty running under WSLg. It exists rather
# than the PowerShell script being reused because that script launches the Windows claude, and
# a session started from kitty must run the claude inside the distro or it reads a different
# ~/.claude entirely.
#
# WHY A CHOOSER AND NOT A PINNED LANE. The desktop shortcut used to be
#     wt.exe -d "C:\Users\shova\Downloads\new-recruit" pwsh -NoExit -Command claude
# which pinned every session's working directory to one repo. docs/charters.md assigns a lane
# BY working directory, so that shortcut made harness work report the resume lane for hours.
# Whatever is chosen here, CLAUDE_LANE is exported before claude starts, so session-recall.sh
# reads a declared lane instead of inferring one from a path a launcher happened to choose.
#
# LETTERS ARE POST-ADR-0016: A harness, B resume engine, C learning, D content. The old
# concierge lane A was retired 2026-07-29 and the remaining four shifted down. A launcher
# still exporting the old letters is the drift ADR-0016 predicted, and it is silent: the
# session runs fine and is attributed to the wrong charter.
#
# EXT4 FIRST. Each lane names an ext4 path and a /mnt/c fallback. Measured on this machine,
# same 5,763-file repo: `git status` 69 ms on ext4 against 12,018 ms through /mnt/c. Until a
# repo is migrated to ~/work/repos the fallback is used and the session is slow; the moment it
# is migrated this script finds it with no edit.

set -uo pipefail

# Resolve claude: explicit override, then PATH, then the native install, then bun.
# The old default was ONLY $HOME/.bun/bin/claude; when the install moved to the
# native launcher (~/.local/bin/claude) the chooser died at the -x check and the
# kitty window closed before the message could be read. Measured 2026-08-13: the
# bun path does not exist on this machine, the native one does (v2.1.229).
if [ -z "${CLAUDE_BIN:-}" ]; then
  CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
  [ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$HOME/.local/bin/claude"
  [ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$HOME/.bun/bin/claude"
fi
WORK="$HOME/work/repos"
WIN="/mnt/c/Users/shova"

# lane|description|ext4 dir|fallback dir
#
# Fallbacks corrected 2026-07-31. All three pointed under $WIN/Downloads, which a
# declutter sweep emptied that morning; the repos now sit directly under $WIN. So
# every fallback was dead while the table still looked complete. Same class as the
# LANE_MAP defect in tools/bus/bus.py, fixed the same day: a lookup table whose
# entries stopped resolving and whose failure mode is silence.
# Verified with `[ -d ]`: $WIN/new-recruit and $WIN/daily-deep-learning exist,
# $WIN/Downloads/daily-deep-learning does not.
LANES=(
  "A|harness: rules, hooks, skills, schedulers, review fabric|$WORK/claude-setup|$WIN/claude-setup"
  "B|resume engine: hiring machine, arms, applications|$WORK/new-recruit|$WIN/new-recruit"
  "C|learning: the PWA, learning cards, study loops|$WORK/daily-deep-learning|$WIN/daily-deep-learning"
  "D|content and publishing: case ledgers, syndication; operator posts|$WORK/daily-deep-learning|$WIN/daily-deep-learning"
)

# Where a project may live. Bounded on purpose: an unbounded scan of the home tree takes
# seconds and surfaces node_modules clones nobody wants.
#
# $WIN added 2026-08-23. audit-boundary and oren-roast-hq live directly at
# C:\Users\shova, not under Downloads or PycharmProjects, so they were invisible to
# every prior root. Found by diffing this list against a live `Get-ChildItem -Depth 0`
# on the Windows home dir.
PROJECT_ROOTS=("$WORK" "$WIN" "$WIN/Downloads" "$WIN/PycharmProjects" "$HOME/work")

# A repo with no commit in this many days is excluded from the picker (still reachable
# by typing its path directly to `claude`). Cutoff is 180 days: wide enough that any
# lane repo (all committed within the last two weeks, measured 2026-08-23) clears it
# by a wide margin, tight enough to drop Web_Scraping (2024-08-25) and
# deep_learning_neural_networks (2024-12-20), both over a year stale, which were
# showing in the picker with no way to tell they were dead.
STALE_DAYS=180

c_reset=$'\033[0m'; c_cyan=$'\033[36m'; c_dim=$'\033[2m'
c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_red=$'\033[31m'

# die holds the window open. This script is a desktop button's payload: when it
# exits, kitty closes with it, so an unread error is indistinguishable from a
# crash. The 2026-08-13 failure was exactly that: die("claude not executable")
# fired and the window vanished before the line could be read.
die() {
  printf '%s%s%s\n' "$c_red" "$1" "$c_reset" >&2
  printf '\n  press Enter to close ' >&2
  read -r _ || true
  exit 1
}

# Prefer ext4, fall back to the Windows mount, and say which was used so the speed penalty is
# visible rather than mysterious.
resolve_dir() {
  local ext4="$1" fallback="$2"
  if [ -d "$ext4" ]; then printf '%s' "$ext4"; return 0; fi
  if [ -d "$fallback" ]; then printf '%s' "$fallback"; return 1; fi
  return 2
}

read_choice() {
  local prompt="$1" max="$2" raw
  while true; do
    printf '\n%s [1-%s, q to quit]: ' "$prompt" "$max" >&2
    read -r raw || return 1
    [ "$raw" = "q" ] && return 1
    if [[ "$raw" =~ ^[0-9]+$ ]] && [ "$raw" -ge 1 ] && [ "$raw" -le "$max" ]; then
      printf '%s' "$raw"; return 0
    fi
    printf '  %spick 1 to %s, or q%s\n' "$c_yellow" "$max" "$c_reset" >&2
  done
}

# Seconds since the repo's last commit, or empty if it has none (an empty/broken
# .git counts as stale rather than crashing the sort below).
last_commit_age_days() {
  local dir="$1" ts now
  ts="$(git -C "$dir" log -1 --format=%ct 2>/dev/null)" || return 1
  [ -z "$ts" ] && return 1
  now="$(date +%s)"
  printf '%s' $(( (now - ts) / 86400 ))
}

discover_projects() {
  local root d age
  for root in "${PROJECT_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    for d in "$root"/*; do
      [ -d "$d/.git" ] || continue
      age="$(last_commit_age_days "$d")" || continue
      [ "$age" -le "$STALE_DAYS" ] && printf '%s\n' "$d"
    done
  done | awk '!seen[$0]++'
}

new_project() {
  local name dir gate
  printf '\nnew project name (letters, digits, dot, dash, underscore): ' >&2
  read -r name || return 1
  [ -z "$name" ] && return 1
  if ! [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    printf '  %srejected: use letters, digits, dot, dash, underscore%s\n' "$c_red" "$c_reset" >&2
    return 1
  fi
  # New projects go to ext4. There is no reason to create anything new on the slow side.
  dir="$WORK/$name"
  [ -e "$dir" ] && { printf '  %salready exists: %s%s\n' "$c_red" "$dir" "$c_reset" >&2; return 1; }
  mkdir -p "$dir" || return 1
  ( cd "$dir" && git init -q 2>/dev/null
    # gate.py init writes a starter quality-contract.json that deliberately FAILS a project
    # with no tests, so a new repo starts red rather than starting unmeasured.
    # Self-relative first: this script's own deployed location is the one path shape
    # that survives a repo restructure with no edit here (same fix class as
    # ship_gate_stop.py's load_gate(), 2026-08-24). The WORK/WIN candidates stay as a
    # fallback for the case this script runs from somewhere other than its usual home.
    gate="$(cd "$(dirname "${BASH_SOURCE[0]}")/../gate" 2>/dev/null && pwd)/gate.py"
    [ -f "$gate" ] || gate="$WORK/claude-setup/engine/tools/gate/gate.py"
    [ -f "$gate" ] || gate="$WIN/claude-setup/engine/tools/gate/gate.py"
    [ -f "$gate" ] && python3 "$gate" init --project . >/dev/null 2>&1 )
  printf '  %screated %s%s\n' "$c_green" "$dir" "$c_reset" >&2
  printf '%s' "$dir"
}

# ------------------------------------------------------------------ resolve
LANE=""
DIR=""

if [ "${1:-}" = "--lane" ] && [ -n "${2:-}" ]; then
  LANE="$2"
  for row in "${LANES[@]}"; do
    IFS='|' read -r l _d e f <<< "$row"
    [ "$l" = "$LANE" ] && { DIR="$(resolve_dir "$e" "$f")" || true; }
  done
  [ -z "$DIR" ] && die "unknown lane: $LANE"
else
  printf '\n  %sCLAUDE WORKSPACE%s\n' "$c_cyan" "$c_reset"
  printf '  ----------------\n'
  printf '  1  global   a charter lane\n'
  printf '  2  project  an existing repo\n'
  printf '  3  new      scaffold a repo on ext4, then open it\n'
  top="$(read_choice 'choose' 3)" || exit 0

  case "$top" in
    1)
      printf '\n'
      i=0
      for row in "${LANES[@]}"; do
        i=$((i + 1))
        IFS='|' read -r l d e f <<< "$row"
        if [ -d "$e" ]; then where="${c_green}ext4${c_reset}"; else where="${c_yellow}/mnt/c slow${c_reset}"; fi
        printf '  %s  lane %s  %s  [%s]\n' "$i" "$l" "$d" "$where"
      done
      pick="$(read_choice 'lane' "$i")" || exit 0
      IFS='|' read -r LANE _d e f <<< "${LANES[$((pick - 1))]}"
      DIR="$(resolve_dir "$e" "$f")" || true
      [ -z "$DIR" ] && die "neither path exists for lane $LANE"
      ;;
    2)
      mapfile -t projects < <(discover_projects)
      [ "${#projects[@]}" -eq 0 ] && die "no git repos found under: ${PROJECT_ROOTS[*]}"
      printf '\n'
      i=0
      for p in "${projects[@]}"; do
        i=$((i + 1))
        case "$p" in
          "$WORK"/*) where="${c_green}ext4${c_reset}" ;;
          *)         where="${c_yellow}/mnt/c slow${c_reset}" ;;
        esac
        printf '  %2s  %-38s %s%s%s [%s]\n' "$i" "$(basename "$p")" "$c_dim" "$(dirname "$p")" "$c_reset" "$where"
      done
      pick="$(read_choice 'project' "$i")" || exit 0
      DIR="${projects[$((pick - 1))]}"
      # A project is not a charter lane. Leaving CLAUDE_LANE empty is the honest state, and
      # session-recall.sh says so out loud rather than guessing, which is the whole point.
      LANE=""
      ;;
    3)
      DIR="$(new_project)" || exit 0
      LANE=""
      ;;
  esac
fi

# ------------------------------------------------------------------ launch
[ -d "$DIR" ] || die "resolved directory does not exist: $DIR"
[ -x "$CLAUDE_BIN" ] || die "claude not executable at $CLAUDE_BIN (install: bun add -g @anthropic-ai/claude-code)"

cd "$DIR" || die "cannot cd to $DIR"

case "$DIR" in
  /mnt/*) printf '\n  %sNOTE: this repo is on the Windows mount. git and file operations here\n'\
'  cross the 9P boundary and are roughly 100x slower than ext4. Migrate it to\n'\
'  %s to fix that.%s\n' "$c_yellow" "$WORK" "$c_reset" ;;
esac

if [ -n "$LANE" ]; then
  printf '\n  %slane %s%s  %s\n\n' "$c_cyan" "$LANE" "$c_reset" "$DIR"
  export CLAUDE_LANE="$LANE"
else
  printf '\n  %sno lane declared%s  %s\n\n' "$c_dim" "$c_reset" "$DIR"
  unset CLAUDE_LANE
fi

exec "$CLAUDE_BIN" "$@"
