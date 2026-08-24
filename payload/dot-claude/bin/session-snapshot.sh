#!/usr/bin/env bash
# session-snapshot.sh — wrapper for SessionStart / Stop hooks
#
# Usage (invoked by Claude Code hooks):
#   session-snapshot.sh start     # called from SessionStart hook
#   session-snapshot.sh end       # called from Stop hook
#
# Reads hook input JSON from stdin. Computes structural metrics for the cwd
# project, persists to ~/.claude/cache/sessions.db, and writes a JSON snapshot
# to ~/.claude/observability/snapshots/.
#
# Cheap: completes in <2 seconds on Seekapa-sized repos. Skips silently if
# Python or sqlite3 unavailable.

set -euo pipefail

PHASE="${1:-start}"  # 'start' or 'end'
INPUT=$(cat)
SNAP_DIR="$HOME/.claude/observability/snapshots"
LAYER7_DIR="$HOME/.claude/cache/layer7"
DB_PATH="$HOME/.claude/cache/sessions.db"
mkdir -p "$SNAP_DIR" "$(dirname "$DB_PATH")"

SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "unknown")
CWD=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd','$PWD'))" 2>/dev/null || echo "$PWD")
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# HOME-as-repo guard: $HOME doubles as a worktree of axia-seekapa-cs-agents
# (memory: project_home_as_repo). Scanning $HOME walks 86M+ lines of personal
# files; the result is meaningless and freezes the TUI for ~50s. Skip cleanly.
if [ "$CWD" = "$HOME" ] || [ "$CWD" = "/home/shovalbe" ]; then
  if [ "$PHASE" = "start" ]; then
    cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Layer 7: skipped at $HOME (HOME-as-repo anomaly). Snapshot computes for project-scoped sessions only."}}
EOF
  else
    echo '{}'
  fi
  exit 0
fi


# Bail silently if dependencies missing
command -v python3 >/dev/null 2>&1 || { echo '{}'; exit 0; }
[ -f "$LAYER7_DIR/snapshot-metrics.py" ] || { echo '{}'; exit 0; }

# Init DB if missing
if [ ! -f "$DB_PATH" ]; then
  python3 "$LAYER7_DIR/init-db.py" >/dev/null 2>&1 || true
fi

# Compute snapshot (always — small enough that we re-run on each phase)
SNAPSHOT_JSON=$(timeout 3 python3 "$LAYER7_DIR/snapshot-metrics.py" "$CWD" 2>/dev/null || echo '{}')
[ -z "$SNAPSHOT_JSON" ] && { echo '{}'; exit 0; }

# Persist JSON file
SNAP_FILE="$SNAP_DIR/${SESSION_ID}-${STAMP//[:.]/}-${PHASE}.json"
echo "$SNAPSHOT_JSON" > "$SNAP_FILE"

# Persist to sessions.db (insert on start, update on end)
python3 - <<PY 2>/dev/null || true
import json, sqlite3, sys
from pathlib import Path

DB = Path.home() / ".claude" / "cache" / "sessions.db"
phase = "$PHASE"
session_id = "$SESSION_ID"
stamp = "$STAMP"
cwd = "$CWD"

snap = json.loads('''$SNAPSHOT_JSON''')

conn = sqlite3.connect(str(DB))
try:
    if phase == "start":
        conn.execute(
            """INSERT OR IGNORE INTO sessions
            (session_id, started_at, project_path, git_branch, git_head,
             loc_start, files_start, test_count_start, complexity_start, layer_violations_start)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, stamp, cwd,
             snap.get("git_branch"), snap.get("git_head"),
             snap.get("loc"), snap.get("files"),
             snap.get("test_count"), snap.get("complexity_total"),
             snap.get("layer_violations")),
        )
    else:  # end
        conn.execute(
            """UPDATE sessions SET
               ended_at = ?,
               loc_end = ?, files_end = ?, test_count_end = ?,
               complexity_end = ?, layer_violations_end = ?
             WHERE session_id = ?""",
            (stamp,
             snap.get("loc"), snap.get("files"),
             snap.get("test_count"), snap.get("complexity_total"),
             snap.get("layer_violations"),
             session_id),
        )
        # Compute simple quality_signal: combine deltas, normalize to 0-10000.
        row = conn.execute(
            "SELECT loc_start, complexity_start, layer_violations_start, test_count_start "
            "FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row and all(v is not None for v in row):
            d_loc = (snap.get("loc") or 0) - (row[0] or 0)
            d_complexity = (snap.get("complexity_total") or 0) - (row[1] or 0)
            d_violations = (snap.get("layer_violations") or 0) - (row[2] or 0)
            d_tests = (snap.get("test_count") or 0) - (row[3] or 0)
            # Simple signal: 5000 baseline; +500 per new test; -200 per +10 complexity;
            #                -1000 per new violation; +100 per +50 LOC (assumes some growth = good).
            signal = 5000
            signal += 500 * d_tests
            signal -= 20 * d_complexity
            signal -= 1000 * d_violations
            signal += 2 * d_loc  # mild reward for shipping code
            signal = max(0, min(10000, signal))
            conn.execute(
                "UPDATE sessions SET quality_signal_end = ? WHERE session_id = ?",
                (signal, session_id),
            )
    conn.commit()
finally:
    conn.close()
PY

# Emit hook output (additionalContext for SessionStart only — Stop hooks don't inject)
if [ "$PHASE" = "start" ]; then
  PROJECT_NAME=$(basename "$CWD")
  TERM_COLS="${COLUMNS:-unknown}"
  TERM_ROWS="${LINES:-unknown}"
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Layer 7 baseline: project=$PROJECT_NAME loc=$(echo "$SNAPSHOT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('loc',0))") tests=$(echo "$SNAPSHOT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('test_count',0))") complexity=$(echo "$SNAPSHOT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('complexity_total',0))") layer_violations=$(echo "$SNAPSHOT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('layer_violations',0))") terminal=${TERM_COLS}x${TERM_ROWS}. Size tables/diffs/ASCII charts to fit this window. Session quality signal will be computed at Stop. Snapshot at $SNAP_FILE."}}
EOF
else
  echo '{}'
fi
exit 0
