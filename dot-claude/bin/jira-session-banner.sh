#!/usr/bin/env bash
# SessionStart hook: print a concise Jira reminder banner from the local cache.
# Self-refreshes the cache if it's older than STALE_HOURS (catch-up for when the
# cron didn't run because the machine was off). Never blocks session start —
# all work is best-effort with a hard timeout and silent failure.
set -uo pipefail

HOOK_MODE=0
if [ ! -t 0 ]; then
  cat >/dev/null || true
  HOOK_MODE=1
fi

STATE_DIR="$HOME/.claude/jira"
DIGEST="$STATE_DIR/reminders.json"
POINTER="$STATE_DIR/current-ticket"
REFRESH="$HOME/.claude/bin/jira-reminder-refresh.py"
INTENT_ROOT="$HOME/projects/intent-control-plane"
STALE_HOURS=6

# Refresh in the background (no email) if cache is missing or stale, so it never
# delays the prompt. The banner below shows whatever cache currently exists.
needs_refresh=1
if [ -f "$DIGEST" ]; then
  age=$(( ($(date +%s) - $(stat -c %Y "$DIGEST")) / 3600 ))
  [ "$age" -lt "$STALE_HOURS" ] && needs_refresh=0
fi
if [ "$needs_refresh" -eq 1 ] && command -v python3 >/dev/null 2>&1; then
  ( timeout 25 python3 "$REFRESH" --no-email >/dev/null 2>&1 & ) 2>/dev/null
fi

[ -f "$DIGEST" ] || {
  [ "$HOOK_MODE" -eq 1 ] && echo '{}'
  exit 0
}

BANNER=$(PYTHONPATH="$INTENT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DIGEST" "$POINTER" "$STATE_DIR/az-auth-needed.flag" "$PWD" <<'PY'
import json, os, subprocess, sys
from datetime import datetime, timezone

digest_path, pointer_path, auth_flag, cwd = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

# Loudest signal first: az session dead → cron can't refresh or email.
if os.path.exists(auth_flag):
    try:
        a = json.load(open(auth_flag))
        since = a.get("since", "")[:16].replace("T", " ")
    except Exception:
        since = ""
    print(f"!! JIRA REFRESH BLOCKED — az login expired (since {since} UTC). "
          f"Reminders are STALE. Run:  ! az login")

try:
    d = json.load(open(digest_path))
except Exception:
    sys.exit(0)

pointer = ""
if os.path.exists(pointer_path):
    pointer = open(pointer_path).read().strip()

flagged = d.get("flagged", [])
gen = d.get("generated_at", "")[:16].replace("T", " ")
try:
    age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(d["generated_at"])).total_seconds() / 3600
    fresh = f"{age_h:.0f}h ago" if age_h >= 1 else "just now"
except Exception:
    fresh = gen

ptr = f"  |  time pointer: {pointer}" if pointer else "  |  time pointer: (unset — say 'work on DEV-####')"
assessment = None
try:
    env = os.environ.copy()
    root = os.path.expanduser("~/projects/intent-control-plane/src")
    env["PYTHONPATH"] = root if not env.get("PYTHONPATH") else f"{root}:{env['PYTHONPATH']}"
    proc = subprocess.run(
        [
            "python3",
            "-m",
            "intent_control_plane.cli",
            "jira",
            "assess",
            "--digest",
            digest_path,
            "--pointer",
            pointer_path,
            "--cwd",
            cwd,
            "--task",
            cwd,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=2.5,
        env=env,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        assessment = json.loads(proc.stdout)
except Exception:
    assessment = None

if assessment:
    related = assessment.get("related_tickets", [])
    unrelated_count = assessment.get("unrelated_count", 0)
    relation = assessment.get("current_ticket_relation") or {}
    marker = "related" if relation.get("related") else "unverified"
    print(
        f"JIRA SESSION CHECK: {len(related)} related / {unrelated_count} unrelated flagged "
        f"(refreshed {fresh}){ptr}  |  pointer: {marker}"
    )
    for t in related[:6]:
        summ = str(t.get("summary", ""))[:52]
        print(f"  {t['key']} [{t.get('status','')}] {summ} — {t.get('reason','related')}")
    if unrelated_count:
        print("  Unrelated Jira tickets are hidden from session context unless you name the key.")
    if related:
        print("  Jira writes/time attribution require the ticket to be related or explicitly named.")
else:
    print(f"JIRA REMINDERS: {len(flagged)} of {d.get('open_total','?')} open need action  (refreshed {fresh}){ptr}")
    for t in flagged[:6]:
        reason = t["reasons"][0] if t.get("reasons") else ""
        summ = t["summary"][:52]
        print(f"  {t['key']} [{t['status']}] {summ} — {reason}")
    if len(flagged) > 6:
        print(f"  ...and {len(flagged)-6} more")
    if flagged:
        print("  Say \"move <KEY>\" or \"comment <KEY>\" — I confirm before any Jira write.")
PY
)

if [ "$HOOK_MODE" -eq 1 ]; then
  if [ -n "$BANNER" ]; then
    python3 - "$BANNER" <<'PY'
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": sys.argv[1],
    }
}))
PY
  else
    echo '{}'
  fi
else
  printf '%s\n' "$BANNER"
fi
