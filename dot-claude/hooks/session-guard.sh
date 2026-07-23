#!/usr/bin/env bash
# session-guard.sh -- PreToolUse(Bash) hook shim for the concurrent-session guard.
#
# HOME doubles as a git worktree of a shared codebase with several live Claude/Codex
# sessions at once. A destructive git-hygiene command (worktree prune, branch -D,
# clean -f, reset --hard, force-push, rm/mv on .git) run by one session can silently
# break another session's in-flight work. This shim delegates the decision to the
# tested, standalone module at intent-control-plane (its own repo, its own tests):
# non-destructive commands and non-Bash tool calls pass straight through, and a
# destructive command is denied only when other live sessions are detected and
# SESSION_GUARD_OVERRIDE=1 is not set.
#
# Not wired into settings.json yet; this file is additive only.
set -uo pipefail

GUARD_SRC="$HOME/projects/intent-control-plane/src"

INPUT="$(cat 2>/dev/null || true)"
TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")"

# Only Bash tool calls are in scope; everything else passes through.
[ "$TOOL_NAME" = "Bash" ] || { echo '{}'; exit 0; }

COMMAND="$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")"
[ -n "$COMMAND" ] || { echo '{}'; exit 0; }

OUT="$(PYTHONPATH="$GUARD_SRC" python3 -m intent_control_plane.session_guard --command "$COMMAND" 2>/dev/null)"
STATUS=$?

# Guard module missing/broken: fail open (allow) rather than block all Bash calls.
if [ "$STATUS" -ne 0 ] && [ "$STATUS" -ne 2 ]; then
  echo '{}'
  exit 0
fi

if [ "$STATUS" -eq 0 ]; then
  echo '{}'
  exit 0
fi

REASON="$(printf '%s' "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason','blocked by session guard'))" 2>/dev/null || echo "blocked by session guard")"
python3 -c "import json,sys;print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':sys.argv[1]}}))" "$REASON"
exit 0
