#!/usr/bin/env bash
# contract-proof-stop.sh -- Stop-boundary proof guard (implements the G1 self-improve loop's own
# Codex proposal). At turn end, if the latest intent has proof_required and no passing evidence
# attached, surface a VISIBLE systemMessage so the contract gap does not pass silently. Catches
# turns that never call TaskUpdate (which the G2 PreToolUse gate misses). Non-blocking (no
# continue:false, no loop risk); also appends the gap to a log the self-improve loop reads.
set -uo pipefail

[ -n "${CLAUDE_LOOP_MODE:-}" ] && { echo '{}'; exit 0; }
[ -n "${CODEX_AUTOMATION_ID:-}" ] && { echo '{}'; exit 0; }
command -v intent >/dev/null 2>&1 || { echo '{}'; exit 0; }

MSG=$(python3 - <<'PY' 2>/dev/null || true
import json, subprocess, shutil
b = shutil.which("intent")
def q(*a):
    try:
        return json.loads(subprocess.run([b, *a], capture_output=True, text=True, timeout=8).stdout or "{}")
    except Exception:
        return {}
its = q("list", "intents", "--limit", "1").get("items", [])
if not its:
    raise SystemExit
it = its[0]
iid = it.get("intent_id")
proof = [p.get("type") for p in (it.get("proof_required") or []) if p.get("type")]
if not proof:
    raise SystemExit
ev = q("list", "evidence", "--limit", "50").get("items", [])
if any(e.get("intent_id") == iid and e.get("status") == "pass" for e in ev):
    raise SystemExit
print(f"Contract note: last intent {iid} requires proof {proof} and none is attached. "
      f"If you verified, run `intent evidence attach`; if not, this gap is now visible.")
PY
)

[ -z "$MSG" ] && { echo '{}'; exit 0; }

LOG="$HOME/.claude/cache/self-improve/unmet-contracts.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
printf '%s\n' "$MSG" >> "$LOG" 2>/dev/null || true

python3 -c "import json,sys;print(json.dumps({'systemMessage': sys.argv[1]}))" "$MSG"
exit 0
