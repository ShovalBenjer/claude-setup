#!/usr/bin/env bash
# verification-before-completion.sh -- PreToolUse gate on TaskUpdate(status=completed).
# G2 contract enforcement: reads the intent-control-plane contract (the latest intent's
# proof_required) and checks whether passing evidence is attached. Turns the contract from a
# comment into a specific, named check at the completion boundary. Non-denying (injects context,
# does not hard-block), degrades to a generic reflection nudge if the intent CLI is unavailable.
set -uo pipefail

INPUT=$(cat 2>/dev/null || true)
# Field names differ between the Claude harness (tool_name/tool_input) and Codex (tool/parameters).
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // .tool // "unknown"' 2>/dev/null || echo unknown)
NEW_STATUS=$(printf '%s' "$INPUT" | jq -r '.tool_input.status // .parameters.status // ""' 2>/dev/null || echo "")
TASK_ID=$(printf '%s' "$INPUT" | jq -r '.tool_input.taskId // .parameters.taskId // ""' 2>/dev/null || echo "")

if [ "$TOOL" != "TaskUpdate" ] || [ "$NEW_STATUS" != "completed" ]; then
  echo '{}'; exit 0
fi

CONTRACT=""
if command -v intent >/dev/null 2>&1; then
  CONTRACT=$(python3 - <<'PY' 2>/dev/null || true
import json, subprocess, shutil
b = shutil.which("intent")
def q(*a):
    try:
        r = subprocess.run([b, *a], capture_output=True, text=True, timeout=8)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}
intents = q("list", "intents", "--limit", "1").get("items", [])
if not intents:
    raise SystemExit
it = intents[0]
iid = it.get("intent_id")
proof = [p.get("type") for p in (it.get("proof_required") or []) if p.get("type")]
if not proof:
    raise SystemExit
goal = (it.get("goal") or "").strip()[:80]
ev = q("list", "evidence", "--limit", "50").get("items", [])
has = any(e.get("intent_id") == iid and e.get("status") == "pass" for e in ev)
if has:
    print(f"CONTRACT OK: intent {iid} ({goal}) has passing evidence for proof {proof}. Safe to complete.")
else:
    print(f"CONTRACT UNMET for this completion: intent {iid} ({goal}) requires proof {proof}, "
          f"but no passing evidence is attached. Attach it with `intent evidence attach` or clearly "
          f"state the blocker BEFORE marking task {iid} complete. Do not report done on assumptions.")
PY
)
fi

# Fallback when the intent plane is unavailable: the original generic reflection nudge.
if [ -z "$CONTRACT" ]; then
  CONTRACT="Before completing task ${TASK_ID}: give concrete verification evidence (command + real output), name what was NOT verified, and only then mark complete."
fi

python3 -c "import json,sys;print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','additionalContext':sys.argv[1]}}))" "$CONTRACT"
exit 0
