#!/usr/bin/env bash
# sync-skills.sh — keep the Codex and Claude skill sets as ONE union, no matter which runner starts.
# Idempotent + additive ONLY: for each real skill dir (has SKILL.md) present on one side but not the
# other, create a symlink to the resolved real dir. Never overwrites an existing entry, never deletes.
# Safe to run from a SessionStart hook on either runner.
set -euo pipefail

CLAUDE="$HOME/.claude/skills"
CODEX="$HOME/.codex/skills"
mkdir -p "$CLAUDE" "$CODEX"

link_union() {  # $1=src root  $2=dst root
  local src="$1" dst="$2" d name target
  [ -d "$src" ] || return 0
  for d in "$src"/*/; do
    [ -d "$d" ] || continue
    [ -f "$d/SKILL.md" ] || continue          # only real skills
    name="$(basename "$d")"
    [ -e "$dst/$name" ] || [ -L "$dst/$name" ] && continue   # never overwrite
    target="$(readlink -f "$d")"
    ln -s "$target" "$dst/$name"
    echo "  + $dst/$name -> $target"
  done
}

echo "[sync-skills] unifying $CODEX <-> $CLAUDE"
link_union "$CODEX" "$CLAUDE"   # Claude gains Codex skills
link_union "$CLAUDE" "$CODEX"   # Codex gains Claude skills
echo "[sync-skills] claude=$(find "$CLAUDE" -maxdepth 1 -mindepth 1 | wc -l) codex=$(find "$CODEX" -maxdepth 1 -mindepth 1 | wc -l)"
