#!/usr/bin/env bash
# docs-sync.sh -- keep the ~/docs corpus fresh. If any doc changed since the last index,
# rebuild it (local-only: offline + fast) in the BACKGROUND so SessionStart never blocks.
# The router + reground query source_id='local-shoval-docs', so URL sources are skipped here.
set -euo pipefail

DB="$HOME/.claude/corpus/best_practices.sqlite3"
DOCS="$HOME/docs"
BUILD="$HOME/.claude/corpus/build_best_practices_corpus.py"

# Stay silent during real automation runs.
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  exit 0
fi
[ -d "$DOCS" ] || exit 0
[ -f "$BUILD" ] || exit 0

rebuild() { ( python3 "$BUILD" build --local-only >/dev/null 2>&1 || true ) & }

if [ ! -f "$DB" ]; then
  rebuild
  exit 0
fi

# First doc newer than the index means the corpus is stale.
newest="$(find "$DOCS" -type f \( -name '*.md' -o -name '*.txt' \) -newer "$DB" -print -quit 2>/dev/null || true)"
[ -z "$newest" ] && exit 0
rebuild
exit 0
