#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"

if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ] || [ -n "${AI_AGENT:-}" ]; then
  echo '{}'
  exit 0
fi

HOOK_INPUT="$INPUT" PYTHONPATH="$HOME/projects/intent-control-plane/src${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PYEOF'
import json
import os
import sys
from pathlib import Path

from intent_control_plane.cli import session_brief

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}

source = payload.get("source", "")
if source not in {"startup", "resume"}:
    print("{}")
    raise SystemExit(0)

workspace = payload.get("workspace") or {}
cwd = (
    workspace.get("current_dir")
    or workspace.get("project_dir")
    or payload.get("cwd")
    or os.environ.get("PWD")
    or str(Path.home())
)

try:
    text = session_brief(
        type(
            "Args",
            (),
            {
                "base_dir": Path.home() / ".intent",
                "cwd": cwd,
                "session": payload.get("session_id") or payload.get("sessionId"),
                "task": cwd,
                "format": "markdown",
                "limit": 5,
                "jira_digest": str(Path.home() / ".claude" / "jira" / "reminders.json"),
                "jira_pointer": str(Path.home() / ".claude" / "jira" / "current-ticket"),
            },
        )()
    )
except Exception as exc:
    text = f"INTENT SESSION BRIEF unavailable: {type(exc).__name__}: {exc}"

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": text,
    }
}))
PYEOF
