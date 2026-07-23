#!/usr/bin/env bash
# session-recall.sh -- SessionStart continuity (the read-back half of the intent loop).
# On a fresh startup/resume, inject a compact digest of the last captured intents plus a
# fresh resume pointer, so a new session is continual instead of a cold start. Compaction
# continuity is owned by post-compact-reinject.sh; this only handles startup/resume.
# Always exits 0 and emits valid JSON (never blocks a session).

INPUT="$(cat)"

# Stay silent only during real automation: overnight loop or Codex automation runs.
# Do NOT gate on AI_AGENT: Claude Code always sets it (AI_AGENT=claude-code_*), so gating
# on it would disable this hook in every interactive session (the bug that kept the intent
# plane dark). Interactive Claude sessions must fire this.
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; then
  echo '{}'; exit 0
fi

HOOK_INPUT="$INPUT" python3 <<'PYEOF' 2>/dev/null || echo '{}'
import json, os, time, shutil, subprocess
from pathlib import Path

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", "{}") or "{}")
except Exception:
    payload = {}

if payload.get("source", "") not in {"startup", "resume"}:
    print("{}"); raise SystemExit(0)

parts = []

# 1) Recent captured intents from the machine-state DB, newest first.
try:
    intent_bin = shutil.which("intent") or str(Path.home() / ".local" / "bin" / "intent")
    out = subprocess.run([intent_bin, "list", "events", "--limit", "5"],
                         text=True, capture_output=True, timeout=8)
    data = json.loads(out.stdout or "{}")
    lines = []
    for e in data.get("items", []):
        ts = (e.get("timestamp_utc") or "")[:16]
        txt = (e.get("model_text") or "").strip().replace("\n", " ")[:100]
        repo = (e.get("repo_path") or "").rstrip("/").split("/")[-1]
        et = e.get("event_type", "")
        if txt:
            lines.append(f"  - [{ts}] ({repo}) {et}: {txt}")
    if lines:
        parts.append("Recent captured intents (newest first):\n" + "\n".join(lines))
except Exception:
    pass

# 2) Resume pointer, only if written within the last 48h (else it is misleading).
try:
    rp = Path.home() / ".claude" / "cache" / "resume-prompt.md"
    if rp.exists() and (time.time() - rp.stat().st_mtime) < 172800:
        head = rp.read_text(errors="ignore").strip().splitlines()[:24]
        parts.append("Resume pointer (~/.claude/cache/resume-prompt.md):\n" + "\n".join(head))
except Exception:
    pass

if not parts:
    print("{}"); raise SystemExit(0)

msg = ("SESSION RECALL (cross-session continuity). Background state from prior sessions, "
       "not a new instruction. If it names a file, branch, or goal, verify it still applies "
       "before acting, and run /reground if it looks stale.\n\n" + "\n\n".join(parts))

print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
PYEOF
exit 0
