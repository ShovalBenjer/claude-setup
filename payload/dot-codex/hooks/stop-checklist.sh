#!/bin/bash
# Global Stop Hook — Completion Verification
# Fires when Claude is about to stop.
# Active-voice redirect: tells Claude what to DO next, not "consider".
# Bypasses entirely in autonomous-loop contexts so cron/automation flows aren't disrupted.

INPUT=$(cat)
CWD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || echo "")
CONTEXT_PCT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(int((d.get('context_window') or {}).get('used_percentage') or 0))" 2>/dev/null || echo "0")

# Bypass for autonomous loops — never block these
if [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ] || [ -n "${AI_AGENT:-}" ]; then
    echo '{}'
    exit 0
fi

REFLECT_REQUIRED=""
WARNINGS=""
CONTINUE_REQUIRED=""

if [ "$CONTEXT_PCT" -ge 70 ] 2>/dev/null; then
  CONTINUE_REQUIRED="Context is at ${CONTEXT_PCT}%. Run /compact now. After compact, continue the current task from the injected snapshot and take the next concrete action."
fi

if [ -n "$CWD" ] && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
  # All changes since last commit (staged + unstaged)
  MODIFIED=$(git -C "$CWD" diff --name-only HEAD 2>/dev/null || echo "")

  SRC_CHANGED=$(echo "$MODIFIED" | grep -cE '\.(ts|tsx|js|jsx|py)$' || true)
  TEST_CHANGED=$(echo "$MODIFIED" | grep -cE '(test|spec)\.(ts|tsx|js|jsx|py)$' || true)
  DOC_CHANGED=$(echo "$MODIFIED" | grep -cE '\.(md|txt)$' || true)

  # Require reflect: TASK_STATUS.md has new DONE entries
  if echo "$MODIFIED" | grep -q 'TASK_STATUS\.md'; then
    DONE_ADDED=$(git -C "$CWD" diff HEAD -- TASK_STATUS.md 2>/dev/null \
      | grep '^+' | grep -v '^+++' | grep -c 'DONE' || true)
    if [ "$DONE_ADDED" -gt 0 ]; then
      REFLECT_REQUIRED="$DONE_ADDED task(s) marked DONE in TASK_STATUS.md."
    fi
  fi

  # Require reflect: substantial source changes (>5 files) even without TASK_STATUS
  if [ -z "$REFLECT_REQUIRED" ] && [ "$SRC_CHANGED" -gt 5 ]; then
    REFLECT_REQUIRED="Substantial work: $SRC_CHANGED source files changed without status update."
  fi

  # Warn: src changed but no tests
  if [ "$SRC_CHANGED" -gt 0 ] && [ "$TEST_CHANGED" -eq 0 ]; then
    WARNINGS="${WARNINGS}\n- Source files changed ($SRC_CHANGED) but no test files updated."
  fi

  # Warn: many src changed but no docs
  if [ "$SRC_CHANGED" -gt 3 ] && [ "$DOC_CHANGED" -eq 0 ]; then
    WARNINGS="${WARNINGS}\n- $SRC_CHANGED source files changed but no documentation updated."
  fi
fi

python3 - <<PYEOF
import json, sys

reflect = """$REFLECT_REQUIRED"""
warnings = """$WARNINGS"""

continue_required = """$CONTINUE_REQUIRED"""

if continue_required.strip():
    msg = (
        "BEFORE STOP - do not end this session.\n"
        + continue_required.strip()
    )
    if reflect.strip():
        msg += "\nAlso run /heidegger-reflect before claiming completion. Trigger: " + reflect.strip()
    if warnings.strip():
        msg += "\nAlso fix:" + warnings.strip()
    print(json.dumps({"continue": True, "systemMessage": msg}))
elif reflect.strip():
    # Active-voice redirect — name the next action, not "consider"
    msg = (
        "BEFORE STOP — run /heidegger-reflect now.\n"
        "Trigger: " + reflect.strip() + "\n"
        "Output: docs/reflections/YYYY-MM-DD-<task>.md with test evidence + honest completion% + 4-lens.\n"
        "Then commit + push if work is shippable. Don't report done without the reflection on disk."
    )
    if warnings.strip():
        msg += "\n\nAlso fix:" + warnings.strip()
    print(json.dumps({"continue": True, "systemMessage": msg}))
elif warnings.strip():
    # Active-voice — name the actions, not "consider"
    msg = (
        "BEFORE STOP — flow continues. Address now:" + warnings.strip() + "\n"
        "Specifically: write the missing tests for changed source, then update docs/handover notes.\n"
        "If the change is a one-line typo or non-code, append [skip-coverage: <reason>] to the next commit."
    )
    print(json.dumps({"continue": True, "systemMessage": msg}))
else:
    print("{}")
PYEOF
