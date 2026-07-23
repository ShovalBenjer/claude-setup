#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
SOURCE="$(
  printf '%s' "$INPUT" |
    python3 -c "import json,sys; print(json.load(sys.stdin).get('source',''))" 2>/dev/null ||
    true
)"

if [ "$SOURCE" != "startup" ] && [ "$SOURCE" != "resume" ]; then
  echo '{}'
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "RTK TERMINAL CONTRACT: Route Bash through rtk by default. Use commands like `rtk git status`, `rtk rg ...`, `rtk uv run pytest ...`, `rtk bun test`, and `rtk az ...`. Use `rtk proxy <cmd>` only for exact host/GNU behavior such as process snapshots, Docker/systemd, or GNU find flags. Do not use bare shell commands when an rtk-prefixed equivalent works."
  }
}
EOF
