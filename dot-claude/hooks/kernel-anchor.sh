#!/usr/bin/env bash
# UserPromptSubmit hook: inject only the small, universal evidence contract.
# Domain knowledge belongs in path-scoped rules or skills, not every prompt.
set -uo pipefail

OS_DIR="${CLAUDE_OS_DIR:-$HOME/claude-setup}"

# Fire-log (L011): durable proof the injection actually reached the harness.
printf '%s\tUserPromptSubmit\n' "$(date '+%Y-%m-%dT%H:%M:%S')" \
  >> "$OS_DIR/state/hook-fires.log" 2>/dev/null || true

read -r -d '' CTX <<EOF || true
[Claude OS kernel]
- Convert non-trivial intent into observable acceptance criteria.
- Inspect repository evidence before choosing an implementation.
- Compare viable alternatives when the choice affects correctness, scale, or architecture.
- A completion or quality claim needs an executable oracle; state skipped checks and residual risk.
- Retrieve domain knowledge just in time with skills; do not expand the prompt speculatively.
EOF

# Emit as additionalContext; never block.
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}\n' \
  "$(printf '%s' "$CTX" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')"
exit 0
