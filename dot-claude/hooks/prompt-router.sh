#!/usr/bin/env bash
# prompt-router.sh -- thin shim. The decision logic (routes, personas, confidence check)
# is the golden-tested module intent_control_plane.harness.router
# (~/projects/intent-control-plane/src/intent_control_plane/harness/router.py), not
# embedded python-in-bash. Same contract: read the prompt on stdin, emit the
# UserPromptSubmit additionalContext JSON, always exit 0, fail safe to '{}'.
INPUT="$(cat)"
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  echo '{}'; exit 0
fi
HOOK_INPUT="$INPUT" PYTHONPATH="$HOME/projects/intent-control-plane/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -m intent_control_plane.harness.router 2>/dev/null || echo '{}'
exit 0
