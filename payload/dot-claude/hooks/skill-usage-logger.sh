#!/usr/bin/env bash
# PostToolUse hook: record Skill tool invocations into sessions.db session_events, so skill
# usage becomes measured data (feeds the router's usage-ranked skill ordering, Tier 1e).
# Thin adapter per ADR-0001: the decision logic (is this a Skill event, extract the name)
# lives in the tested intent_control_plane.cli.parse_skill_event; bash is glue only.
# Inert until wired under hooks.PostToolUse in ~/.claude/settings.json.
INPUT="$(cat)"
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then echo '{}'; exit 0; fi
HOOK_INPUT="$INPUT" PYTHONPATH="$HOME/projects/intent-control-plane/src${PYTHONPATH:+:$PYTHONPATH}" \
  python3 - <<'PYEOF' 2>/dev/null || echo '{}'
import json
import os
from types import SimpleNamespace

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}
try:
    from intent_control_plane.cli import log_skill, parse_skill_event

    event = parse_skill_event(payload)
    if event:
        log_skill(SimpleNamespace(skill=event["skill"], session=event["session"], db=None))
except Exception:
    pass
print("{}")
PYEOF
exit 0
