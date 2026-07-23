#!/usr/bin/env bash
# budget: 50ms
# Claude compatibility hook: nudge RTK at the Bash boundary without stopping autonomy.
#
# Claude hooks cannot safely rewrite tool_input in place. This guard injects
# corrective context for the next command instead of blocking the current run.

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
COMMAND=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

[ "$TOOL_NAME" = "Bash" ] || { echo '{}'; exit 0; }
[ -n "$COMMAND" ] || { echo '{}'; exit 0; }

trimmed="$(printf '%s' "$COMMAND" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"

# Allow commands that are already routed through RTK or are shell/session-local
# operations where RTK wrapping adds no value or can change behavior.
case "$trimmed" in
  rtk\ *|rtk)
    echo '{}'
    exit 0
    ;;
  # Read-only shell inspection commands do not need RTK routing.
  ls\ *|ls|dir\ *|dir|tree\ *|pwd|stat\ *|file\ *)
    echo '{}'
    exit 0
    ;;
  cd\ *|exit|logout|source\ *|alias\ *|unalias\ *|export\ *|unset\ *|type\ *|command\ *|hash\ *|jobs|fg\ *|bg\ *)
    echo '{}'
    exit 0
    ;;
  true|false|:)
    echo '{}'
    exit 0
    ;;
esac

python3 - "$trimmed" <<'PY'
import json
import sys

cmd = sys.argv[1]
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "additionalContext": (
            "RTK AUTOCORRECT: Bash was allowed to preserve autonomous flow, "
            f"but future shell commands must be routed as `rtk {cmd}` when practical."
        )
    }
}))
PY
