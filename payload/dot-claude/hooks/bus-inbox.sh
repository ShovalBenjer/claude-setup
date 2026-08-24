#!/usr/bin/env bash
# A2A inbox injection. Runs on SessionStart and UserPromptSubmit.
#
# Six terminals, no shared context. This pulls anything another lane addressed
# to this one and puts it in front of the model without the operator having to
# copy-paste it. Stdout from these two hook events is appended to context.
#
# Fail-open, always. A hook that errors blocks the prompt, so every failure
# path here exits 0 silently. An A2A bus that can break the session is worse
# than no A2A bus.

set -uo pipefail

BUS_PY="/c/Users/shova/claude-setup/tools/bus/bus.py"
LOG="/c/Users/shova/claude-setup/state/hook-fires.log"

[ -f "$BUS_PY" ] || exit 0

PY=""
for c in python python3 py; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || exit 0

OUT="$("$PY" "$BUS_PY" inbox 2>/dev/null)" || exit 0
[ -n "$OUT" ] || exit 0

printf '%s\n' "$OUT"
printf '%s bus-inbox delivered %s lines\n' "$(date -Iseconds)" "$(printf '%s' "$OUT" | wc -l)" >> "$LOG" 2>/dev/null

exit 0
