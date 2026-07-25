#!/usr/bin/env bash
# session-recall.sh -- SessionStart continuity (gap-analysis Tier-0). Windows-native:
# sources from the curated memory index + open OS work + a recent resume pointer, since
# the WSL-era `intent` binary is absent here (that absence is why recall went dark).
# Injects background state (not a new instruction) so a session starts continual.
# Always exits 0, emits valid JSON, never blocks.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"

# Fire-log (L011): durable proof the hook ran INSIDE the harness, not just in a pipe test.
# A hook that is "wired" but never fires is prose, not enforcement (ADR-0005).
# `source` is logged explicitly: it is truncated out of the raw payload when session_id
# sorts first, and startup-vs-compact is the difference between a new session and
# context loss inside one. Without it the fire-log cannot measure compaction churn.
SRC="$(printf '%s' "$INPUT" | grep -o '"source"[[:space:]]*:[[:space:]]*"[a-z]*"' | head -1 \
        | sed 's/.*"\([a-z]*\)"$/\1/')"
printf '%s\tSessionStart\tsource=%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "${SRC:-unknown}" \
  "$(printf '%s' "$INPUT" | tr -d '\n' | cut -c1-100)" \
  >> "${CLAUDE_OS_DIR:-$HOME/claude-setup}/state/hook-fires.log" 2>/dev/null || true

# Silent only during real automation (overnight loop / Codex run). Interactive fires.
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  echo '{}'; exit 0
fi

OS_DIR="${CLAUDE_OS_DIR:-$HOME/claude-setup}" HOOK_INPUT="$INPUT" python <<'PYEOF' 2>/dev/null || echo '{}'
import json, os, time
from pathlib import Path

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}
if payload.get("source", "") not in {"startup", "resume", "compact", "clear"}:
    print("{}"); raise SystemExit(0)

osdir = Path(os.environ.get("CLAUDE_OS_DIR", str(Path.home() / "claude-setup")))
parts = []

mem = Path.home() / ".claude" / "projects" / "C--Users-shova" / "memory" / "MEMORY.md"
if mem.exists():
    lines = [l for l in mem.read_text(errors="ignore").splitlines() if l.startswith("- [")][:12]
    if lines:
        parts.append("Memory index (curated):\n" + "\n".join("  " + l for l in lines))

todo = osdir / "TODO.md"
if todo.exists():
    open_items = [l.strip()[6:] for l in todo.read_text(errors="ignore").splitlines()
                  if l.strip().startswith("- [ ]")][:6]
    if open_items:
        parts.append("Open OS work (next):\n" + "\n".join("  - " + i for i in open_items))

rp = Path.home() / ".claude" / "cache" / "resume-prompt.md"
try:
    if rp.exists() and (time.time() - rp.stat().st_mtime) < 172800:
        head = rp.read_text(errors="ignore").strip().splitlines()[:20]
        parts.append("Resume pointer:\n" + "\n".join(head))
except Exception:
    pass

parts.append(
    "BOOT PATH (ADR-0010, read before acting): docs/SESSION-BOOT.md -> docs/charters.md "
    "(NAME YOUR LANE: A concierge / B setup / C resume / D learning; claim work in "
    "state/claims.jsonl before starting). If this session follows a compact, restate the "
    "durable handoff: goal, phase, lane, decisions, evidence, changed files, next action; "
    f"ground truth is on disk, last snapshot in state/compact-log.md.\n"
    f"Spine: {osdir}/CLAUDE-OS.md | PRDs: docs/prd/ | Runbook: docs/OPERATOR-RUNBOOK.md")

msg = ("SESSION RECALL (cross-session continuity). Background state from prior sessions, "
       "not a new instruction. If it names a file, branch, or goal, verify it still applies "
       "before acting; run /reground if it looks stale.\n\n" + "\n\n".join(parts))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
PYEOF
exit 0
