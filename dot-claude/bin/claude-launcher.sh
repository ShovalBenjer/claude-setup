#!/usr/bin/env bash
set -euo pipefail

# Lightweight startup screen for Claude Code. This intentionally does not
# mutate MCP config, shell startup, hooks, or Claude settings.
show_startup() {
  [ -t 1 ] || return 0

  local cols rows i line
  cols="$(tput cols 2>/dev/null || printf '80')"
  rows="$(tput lines 2>/dev/null || printf '24')"

  printf '\033[?25l'
  printf '\033[2J\033[H'
  printf '\033[38;5;45m'
  printf '%*s\n' "$(( (cols + 21) / 2 ))" 'SHOVAL AGENT RAIN'
  printf '\033[38;5;244m'
  printf '%*s\n\n' "$(( (cols + 31) / 2 ))" 'Claude Code stable launcher'

  for i in 1 2 3 4 5 6; do
    line="$(printf '%*s' "$cols" '' | tr ' ' '.')"
    case "$i" in
      1|4) printf '\033[38;5;24m%s\n' "$line" ;;
      2|5) printf '\033[38;5;30m%s\n' "$line" ;;
      *) printf '\033[38;5;37m%s\n' "$line" ;;
    esac
    sleep 0.035
  done

  printf '\033[38;5;250m\n'
  printf '  renderer: no-flicker | mouse: disabled | scroll: stable\n'
  printf '  command : claude %s\n' "$*"
  printf '\033[0m'
  sleep 0.12

  # Leave Claude a clean screen, but the startup flash is visible.
  if [ "${CLAUDE_STARTUP_KEEP_SCREEN:-0}" != "1" ]; then
    printf '\033[2J\033[H'
  fi
  printf '\033[?25h'
}

export CLAUDE_CODE_NO_FLICKER="${CLAUDE_CODE_NO_FLICKER:-1}"
export CLAUDE_CODE_DISABLE_MOUSE="${CLAUDE_CODE_DISABLE_MOUSE:-1}"
export CLAUDE_CODE_SCROLL_SPEED="${CLAUDE_CODE_SCROLL_SPEED:-3}"
export CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=0
export CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING="${CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING:-1}"

COLUMNS="$(tput cols 2>/dev/null || printf '220')"
LINES="$(tput lines 2>/dev/null || printf '60')"
export COLUMNS LINES

ARGS=("$@")
HAS_EFFORT=0
for arg in "${ARGS[@]}"; do
  case "$arg" in
    --effort|--effort=*) HAS_EFFORT=1 ;;
  esac
done
if [ "$HAS_EFFORT" = "0" ]; then
  ARGS=(--effort max "${ARGS[@]}")
fi

show_startup "${ARGS[@]}"

# Pick the newest installed version dynamically so a version cleanup never breaks the launcher.
CLAUDE_BIN="$(ls -1 /home/shovalbe/.local/share/claude/versions/* 2>/dev/null | sort -V | tail -1)"
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
  CLAUDE_BIN="$(command -v claude)"
fi
exec "$CLAUDE_BIN" "${ARGS[@]}"
