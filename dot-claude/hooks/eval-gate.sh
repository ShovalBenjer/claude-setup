#!/usr/bin/env bash
# eval-gate.sh -- PreToolUse(git push) eval gate (Tier-1 from the gap-analysis).
# If the repo opts in (has promptfooconfig.* or an evals/ dir), run the SOTA runner ON DEMAND
# (bunx promptfoo / uv run deepeval, no persistent install), log the result for the G1
# self-improve loop, and surface failures. Non-blocking by default (injects a note); set
# EVAL_GATE_BLOCK=1 to hard-deny the push on a failing eval. Skips silently when the repo has
# no eval config, so it is harmless everywhere until a repo opts in.
# EVAL_GATE_MOCK=pass|fail simulates a run (for wiring tests, no network/deps).
set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
{ [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; } && { echo '{}'; exit 0; }

# Push gate only. Settings wires this on matcher "Bash" + `if: Bash(git push*)`, but that
# `if` filter FAILS OPEN when the command can't be parsed (rtk-wrapped, piped, etc.), so the
# hook still fired on non-push commands -- the "N failed" noise. The docs recommend a
# redundant in-script check for gate hooks: exit fast unless the command is an actual push.
CMD="$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || true)"
printf '%s' "$CMD" | grep -qE '(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]|$)' || { echo '{}'; exit 0; }

CWD="$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || true)"
[ -n "$CWD" ] || CWD="$PWD"
cd "$CWD" 2>/dev/null || { echo '{}'; exit 0; }
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || { echo '{}'; exit 0; }
[ "$ROOT" = "$HOME" ] && { echo '{}'; exit 0; }
cd "$ROOT" || { echo '{}'; exit 0; }

MOCK="${EVAL_GATE_MOCK:-}"
RUNNER=""; CONF=""; STATUS=""; SUMMARY=""
if [ -n "$MOCK" ]; then
  RUNNER="mock"; STATUS="$MOCK"; SUMMARY="mock run ($MOCK)"
else
  for c in promptfooconfig.yaml promptfooconfig.yml promptfooconfig.json; do
    [ -f "$c" ] && { RUNNER="promptfoo"; CONF="$c"; break; }
  done
  if [ -z "$RUNNER" ]; then
    { [ -d evals ] || [ -d tests/evals ]; } && RUNNER="deepeval"
  fi
  [ -z "$RUNNER" ] && { echo '{}'; exit 0; }   # repo has not opted in
  if [ "$RUNNER" = "promptfoo" ]; then
    OUT="$(timeout 180 bunx promptfoo@latest eval -c "$CONF" --no-cache 2>&1 || true)"
  else
    OUT="$(timeout 180 uv run --no-project deepeval test run 2>&1 || true)"
  fi
  if [ "$RUNNER" = "promptfoo" ]; then
    # promptfoo always prints "N failed" and "N errors"; only fail on a NONZERO count
    if printf '%s' "$OUT" | grep -qE '[1-9][0-9]* (failed|errors)'; then STATUS="fail"; else STATUS="pass"; fi
  elif printf '%s' "$OUT" | grep -qiE "(^|[^a-z])(fail|failed|error)([^a-z]|$)"; then STATUS="fail"; else STATUS="pass"; fi
  SUMMARY="$(printf '%s' "$OUT" | tail -3 | tr '\n' ' ' | head -c 240)"
fi

LOG="$HOME/.claude/cache/self-improve/eval-runs.jsonl"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
python3 -c "import json,sys,time;print(json.dumps({'ts':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'repo':sys.argv[1],'runner':sys.argv[2],'status':sys.argv[3],'summary':sys.argv[4]}))" \
  "$(basename "$ROOT")" "$RUNNER" "$STATUS" "$SUMMARY" >> "$LOG" 2>/dev/null || true

[ "$STATUS" = "pass" ] && { echo '{}'; exit 0; }

NOTE="EVAL GATE ($RUNNER) reported $STATUS on $(basename "$ROOT"): $SUMMARY. Review before this push lands."
if [ -n "${EVAL_GATE_BLOCK:-}" ]; then
  python3 -c "import json,sys;print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':sys.argv[1]}}))" "$NOTE"
else
  python3 -c "import json,sys;print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','additionalContext':sys.argv[1]}}))" "$NOTE"
fi
exit 0
