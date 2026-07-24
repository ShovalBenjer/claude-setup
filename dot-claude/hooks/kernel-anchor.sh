#!/usr/bin/env bash
# UserPromptSubmit hook — enforces the SDLC kernel (ADR-0005: enforcement over prose).
# Injects, on every prompt, a compact reminder of the deep-work discipline plus the
# active goal line from the OS TODO. Fail-open: any error => no injection, exit 0.
set -uo pipefail

OS_DIR="${CLAUDE_OS_DIR:-$HOME/claude-setup}"
todo="$OS_DIR/TODO.md"

active=""
if [ -f "$todo" ]; then
  # first unchecked item under the first "## P" (priority) section
  active=$(grep -m1 -E '^\s*- \[ \]' "$todo" 2>/dev/null | sed 's/^\s*- \[ \] //')
fi

read -r -d '' CTX <<EOF || true
[Claude OS kernel] Deep-work discipline is in force:
- Substantive task => first extract an acceptance checklist from the user's intent (task bus). Judge output against THAT, not "made progress".
- Loop until intent covered; use full budget. Small-patch-and-report-done is only for explicit quick fixes.
- "Done" = verification evidence (command + output) + an intent-coverage statement (covered / uncovered + why).
- Depth is enforced by external checks (tests, postconditions, fresh-eyes review), never by "think harder".
- CALIBRATED CLAIMS (rules/calibrated-claims.md): tag every claim VERIFIED (command+output shown) / STAGED (exists, unproven) / ASSUMED. Lead with what is broken, unknown, or blocked BEFORE what works. No triumph register ("all done", "everything landed", "fully"). The longer the session, the STRICTER the evidence bar — pressure inflates claims; counter it. A claim later downgraded = calibration loss, logged in state/lessons.jsonl.
${active:+Active OS goal: ${active}}
EOF

# Emit as additionalContext; never block.
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}\n' \
  "$(printf '%s' "$CTX" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')"
exit 0
