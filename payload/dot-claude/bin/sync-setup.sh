#!/usr/bin/env bash
# sync-setup.sh -- keep the Codex and Claude SETUP as ONE union: skills, hooks, rules.
# Generalizes sync-skills.sh. Idempotent + additive ONLY: for each shared asset present on
# one side but not the other, symlink it to the resolved real file/dir. Never overwrites,
# never deletes. Safe to run from a SessionStart hook on either runner.
#
# Intentionally NOT unified (tool-specific, would break a runner if merged):
#   config: ~/.claude/settings.json  vs  ~/.codex/config.toml
#   memory: ~/.claude/CLAUDE.md      vs  ~/.codex/AGENTS.md
#   state : sessions, *.sqlite, auth.json, secrets, logs, caches
set -euo pipefail

HOOK_MODE=0
if [ ! -t 0 ]; then
  cat >/dev/null || true
  HOOK_MODE=1
fi

CL="$HOME/.claude" CX="$HOME/.codex"

link_dir_union() {   # $1=src root $2=dst root : union of subdirs containing SKILL.md
  local src="$1" dst="$2" d name target
  [ -d "$src" ] || return 0
  mkdir -p "$dst"
  for d in "$src"/*/; do
    [ -d "$d" ] || continue
    [ -f "$d/SKILL.md" ] || continue
    name="$(basename "$d")"
    { [ -e "$dst/$name" ] || [ -L "$dst/$name" ]; } && continue
    target="$(readlink -f "$d")"
    ln -s "$target" "$dst/$name" 2>/dev/null && echo "  + $dst/$name -> $target" || true
  done
}

link_file_union() {  # $1=src root $2=dst root $3=glob : union of matching files
  local src="$1" dst="$2" glob="$3" f name target
  [ -d "$src" ] || return 0
  mkdir -p "$dst"
  shopt -s nullglob
  for f in "$src"/$glob; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    { [ -e "$dst/$name" ] || [ -L "$dst/$name" ]; } && continue
    target="$(readlink -f "$f")"
    ln -s "$target" "$dst/$name" 2>/dev/null && echo "  + $dst/$name -> $target" || true
  done
  shopt -u nullglob
}

LOG=$(
  echo "[sync-setup] unifying codex <-> claude (skills, hooks, rules)"
  link_dir_union  "$CX/skills" "$CL/skills";           link_dir_union  "$CL/skills" "$CX/skills"
  link_file_union "$CX/hooks"  "$CL/hooks"  "*.sh";    link_file_union "$CL/hooks"  "$CX/hooks"  "*.sh"
  link_file_union "$CX/rules"  "$CL/rules"  "*.md";    link_file_union "$CL/rules"  "$CX/rules"  "*.md"
  echo "[sync-setup] skills: claude=$(find "$CL/skills" -maxdepth 1 -mindepth 1 2>/dev/null | wc -l) codex=$(find "$CX/skills" -maxdepth 1 -mindepth 1 2>/dev/null | wc -l)"
  echo "[sync-setup] hooks:  claude=$(find "$CL/hooks" -maxdepth 1 -name '*.sh' 2>/dev/null | wc -l) codex=$(find "$CX/hooks" -maxdepth 1 -name '*.sh' 2>/dev/null | wc -l)"
  echo "[sync-setup] rules:  claude=$(find "$CL/rules" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l) codex=$(find "$CX/rules" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l)"
)

if [ "$HOOK_MODE" -eq 1 ]; then
  python3 - "$LOG" <<'PY'
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": sys.argv[1],
    }
}))
PY
else
  printf '%s\n' "$LOG"
fi
