#!/usr/bin/env bash
# snapshot-state.sh — PreCompact hook
#
# Fires before /compact or auto-compact runs. Captures a small state file
# so post-compaction memory recovery has a baseline to re-inject from.
#
# Wired in ~/.claude/settings.json under hooks.PreCompact (matcher *).
# Pairs with ~/.codex/hooks/post-compact-reinject.sh which fires on SessionStart
# after compact and reads the latest snapshot to re-inject context.

set -euo pipefail

INPUT=$(cat)
SNAP_DIR="$HOME/.claude/observability/snapshots"
mkdir -p "$SNAP_DIR"

SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")
COMPACT_TYPE=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('matcher','manual'))" 2>/dev/null || echo "manual")
CWD=$(printf '%s' "$INPUT" | python3 -c "import sys,json,os; print(json.load(sys.stdin).get('cwd') or os.getcwd())" 2>/dev/null || pwd)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SNAP="$SNAP_DIR/${SESSION_ID}-${STAMP}-pre-compact.json"

# Capture current state cheaply (no LLM, no MCP, just shell + python)
python3 <<PY > "$SNAP" 2>/dev/null || true
import json, os, subprocess
from pathlib import Path

def safe(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
    except Exception:
        return ""

snapshot = {
    "session_id": "$SESSION_ID",
    "stamp_utc": "$STAMP",
    "compact_type": "$COMPACT_TYPE",
    "cwd": "$CWD",
    "git_branch": safe("git -C '$CWD' branch --show-current 2>/dev/null"),
    "git_head": safe("git -C '$CWD' rev-parse --short HEAD 2>/dev/null"),
    "uncommitted_files": safe("git -C '$CWD' diff --name-only HEAD 2>/dev/null").splitlines(),
    "task_list_path": str(Path.home() / ".claude" / "tasks" / "current-tasks.md"),
    "memory_index": str(Path.home() / ".claude" / "projects" / "-home-shovalbe" / "memory" / "MEMORY.md"),
    "open_loops": [],
}
print(json.dumps(snapshot, indent=2))
PY

# Inject a marker into the agent context so the post-compact-reinject hook
# can find this snapshot's path on next SessionStart.
echo "$SNAP" > "$SNAP_DIR/.latest-pre-compact"

# NOTE: PreCompact does NOT support hookSpecificOutput.additionalContext — only
# UserPromptSubmit / PostToolUse / PostToolBatch / Stop do. Emitting it here fails
# the hook JSON-schema validation ("Invalid input") on every /compact. The paired
# post-compact-reinject.sh (SessionStart) re-injects state from $SNAP + the
# .latest-pre-compact marker, so no stdout context is needed. Emit a schema-valid no-op.
echo '{"suppressOutput": true}'
exit 0
