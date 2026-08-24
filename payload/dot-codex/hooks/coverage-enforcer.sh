#!/usr/bin/env bash
# coverage-enforcer.sh — PreToolUse hook on Bash(git push*)
#
# Blocks pushes where staged diff has source changes (.py/.ts/.js etc.) without
# matching test-file changes. Closes the COVERAGE axis of the forge loop.
#
# Bypass: include `[skip-coverage: <reason>]` in the most recent commit message.
# Honored prefixes: hotfix:, revert:.
#
# Wired in ~/.claude/settings.json under hooks.PreToolUse with matcher Bash.
# Exit codes: 0 = allow, 2 = deny (Claude shows the message and stops).

set -euo pipefail

INPUT=$(cat)

# Only act on Bash tool calls that are git push commands
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
COMMAND=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

[ "$TOOL_NAME" = "Bash" ] || { echo '{}'; exit 0; }
echo "$COMMAND" | grep -qE '^[[:space:]]*git push' || { echo '{}'; exit 0; }

# Honor --no-verify (logged but allowed)
if echo "$COMMAND" | grep -q -- "--no-verify"; then
  echo "[$(date -u +%FT%TZ)] coverage-enforcer: --no-verify used, push allowed" >> ~/.claude/observability/coverage-enforcer.log
  echo '{}'
  exit 0
fi

# Honor hotfix: / revert: prefixed commits
LAST_MSG=$(git log -1 --pretty=%B 2>/dev/null || echo "")
if echo "$LAST_MSG" | head -1 | grep -qE '^(hotfix|revert):'; then
  echo "[$(date -u +%FT%TZ)] coverage-enforcer: hotfix/revert prefix, push allowed" >> ~/.claude/observability/coverage-enforcer.log
  echo '{}'
  exit 0
fi

# Honor [skip-coverage: <reason>] token
if echo "$LAST_MSG" | grep -qE '\[skip-coverage:'; then
  REASON=$(echo "$LAST_MSG" | grep -oE '\[skip-coverage:[^]]*\]' | head -1)
  echo "[$(date -u +%FT%TZ)] coverage-enforcer: skip token used: $REASON" >> ~/.claude/observability/coverage-enforcer.log
  echo '{}'
  exit 0
fi

# Compute set of files changed in the RANGE being pushed (not just the last commit).
# Try @{u}..HEAD first (everything ahead of upstream — handles multi-commit pushes correctly).
# Fall back to HEAD~1..HEAD only if no upstream is configured.
mkdir -p ~/.claude/observability
RANGE="@{u}..HEAD"
if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1; then
  RANGE="HEAD~1..HEAD"
fi
CHANGED=$(git diff --name-only "$RANGE" 2>/dev/null || echo "")
[ -z "$CHANGED" ] && { echo '{}'; exit 0; }
echo "[$(date -u +%FT%TZ)] coverage-enforcer: range=$RANGE files=$(echo "$CHANGED" | wc -w)" >> ~/.claude/observability/coverage-enforcer.log

# Classify
SOURCE_RE='\.(py|ts|tsx|js|jsx|go|rs|java|kt|swift|rb|php)$'
TEST_RE='(^tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.|Test\.java)'
EXCLUDE_RE='(/migrations/|/__pycache__/|/node_modules/|/\.venv/|/dist/|/build/|tests/test_data/)'

SOURCE_CHANGED=""
TEST_CHANGED=""
while IFS= read -r path; do
  [ -z "$path" ] && continue
  echo "$path" | grep -qE "$EXCLUDE_RE" && continue
  if echo "$path" | grep -qE "$TEST_RE"; then
    TEST_CHANGED="$TEST_CHANGED $path"
  elif echo "$path" | grep -qE "$SOURCE_RE"; then
    SOURCE_CHANGED="$SOURCE_CHANGED $path"
  fi
done <<< "$CHANGED"

SRC_COUNT=$(echo "$SOURCE_CHANGED" | wc -w)
TEST_COUNT=$(echo "$TEST_CHANGED" | wc -w)

if [ "$SRC_COUNT" -gt 0 ] && [ "$TEST_COUNT" -eq 0 ]; then
  echo "[$(date -u +%FT%TZ)] coverage-enforcer: BLOCKED — source w/o tests: $SOURCE_CHANGED" >> ~/.claude/observability/coverage-enforcer.log
  cat <<EOF >&2

╔══════════════════════════════════════════════════════════════════╗
║  COVERAGE GATE: source changes without matching test changes     ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Source changed:                                                 ║
$(echo "$SOURCE_CHANGED" | tr ' ' '\n' | grep -v '^$' | sed 's/^/║    /' | awk '{printf "%-66s║\n", $0}')
║  Tests changed: (none)                                           ║
║                                                                  ║
║  Forge-loop COVERAGE axis will be 0/1 for this push.             ║
║                                                                  ║
║  To proceed, either:                                             ║
║    a) Add a test that exercises the change                       ║
║    b) Append [skip-coverage: <reason>] to commit message         ║
║    c) Use --no-verify (audited but allowed)                      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
  exit 2
fi

echo "[$(date -u +%FT%TZ)] coverage-enforcer: OK — src=$SRC_COUNT tests=$TEST_COUNT" >> ~/.claude/observability/coverage-enforcer.log
echo '{}'
exit 0
