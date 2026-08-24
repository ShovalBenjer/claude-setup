#!/bin/bash
set -euo pipefail

# Watchdog Verification Hook
# Called before any agent Edit/Write operation to prevent destructive behavior

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('file_path',''))" 2>/dev/null || echo "")
CONTENT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('content',''))" 2>/dev/null || echo "")

CWD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || echo "")

# Only check Edit and Write operations
if [ "$TOOL_NAME" != "Edit" ] && [ "$TOOL_NAME" != "Write" ]; then
  echo '{}'
  exit 0
fi

# Get git status
BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || echo "unknown")
DIRTY=$(git -C "$CWD" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

# Safety checks
BLOCK_REASON=""
WARNING=""

# Check 1: Are we on main branch?
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  if [ "$DIRTY" -eq 0 ]; then
    WARNING="$WARNING|$BRANCH branch is clean and on main - editing directly is risky"
  fi
fi

# Check 2: Is the file in a protected location?
PROTECTED=false
case "$FILE_PATH" in
  *".codex"|*".claude"|*".kilocode"|*"package.json"|*"pyproject.toml"|*"Cargo.toml"|*"go.mod"|*"tsconfig.json"|*"next.config.js"|*"tailwind.config.js"|*"eslintrc"|*"prettierrc")
    PROTECTED=true
    ;;
esac

if [ "$PROTECTED" = true ]; then
  BLOCK_REASON="BLOCKED: Editing protected configuration file ($FILE_PATH)"
fi

# Check 3: Is the operation destructive?
DESTRUCTIVE=false
if [ "$TOOL_NAME" = "Write" ]; then
  # Check if file exists and will be overwritten
  if [ -f "$FILE_PATH" ] && [ -n "$CONTENT" ]; then
    # Check if it's a critical file
    case "$FILE_PATH" in
      *"__main__"*|*"index.js"*|*"index.tsx"*|*"main.py"*|*"app.py"*|*"main.go"*|*"main.rs")
      DESTRUCTIVE=true
      ;;
    esac
  fi
fi

# Check 4: Is this an agent branch being deleted?
if echo "$FILE_PATH" | grep -qE "^.*branch.*agent.*delete" || echo "$CONTENT" | grep -qi "git.*branch.*-D.*agent"; then
  BLOCK_REASON="BLOCKED: Attempting to delete agent branch via Write tool"
fi

# Check 5: Are we in a project directory?
if [ ! -f "$CWD/package.json" ] && [ ! -f "$CWD/pyproject.toml" ] && [ ! -f "$CWD/requirements.txt" ]; then
  WARNING="$WARNING|Not in a project directory - verify scope"
fi

# Check 6: Is the content suspiciously large?
if [ -n "$CONTENT" ]; then
  LINE_COUNT=$(echo "$CONTENT" | wc -l)
  if [ "$LINE_COUNT" -gt 1000 ]; then
    BLOCK_REASON="BLOCKED: Writing $LINE_COUNT lines at once - exceeds safety limit of 1000"
  fi
fi

# Check 7: Is automatic cleanup disabled?
AUTO_CLEANUP_DISABLED=""
if [ -f "$CWD/.kilocode/hooks/post-merge-cleanup.json.disabled" ]; then
  AUTO_CLEANUP_DISABLED="✅ Automatic cleanup is disabled"
fi

# Output decision
if [ -n "$BLOCK_REASON" ]; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "$BLOCK_REASON",
    "additionalContext": "🔒 WATCHDOG BLOCKED destructive operation

Branch: $BRANCH
Dirty files: $DIRTY
Protected file: $PROTECTED

$AUTO_CLEANUP_DISABLED

This action requires human approval. Use /watchdog to review or /approve if you're certain."
  }
}
EOF
else
  # Just pass through with warnings if any
  if [ -n "$WARNING" ]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "$WARNING"
  }
}
EOF
  else
    echo '{}'
  fi
fi

exit 0
