#!/bin/bash
set -euo pipefail

# Session Start Context Hook
# Fires on every session startup (not compact/clear).
# Injects current project state: branch, last commit, env context.

INPUT=$(cat)
SOURCE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source',''))" 2>/dev/null || echo "")
CWD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); w=d.get('workspace') or {}; print(w.get('current_dir') or d.get('cwd',''))" 2>/dev/null || echo "")
PROJECT_DIR=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); w=d.get('workspace') or {}; print(w.get('project_dir') or w.get('current_dir') or d.get('cwd',''))" 2>/dev/null || echo "")
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$PROJECT_DIR" ] || PROJECT_DIR="$CWD"

# Emit on fresh startup and resumed sessions. Claude Code fires SessionStart for
# both, and resumed sessions are where missing context is most confusing.
if [ "$SOURCE" != "startup" ] && [ "$SOURCE" != "resume" ]; then
  echo '{}'
  exit 0
fi

CONTEXT=""

# Check if we're in a git repo
if [ -d "$PROJECT_DIR/.git" ] || git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || echo "unknown")
  LAST_COMMIT=$(git -C "$PROJECT_DIR" log -1 --oneline 2>/dev/null || echo "no commits")
  DIRTY=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  
  CONTEXT="SESSION CONTEXT:
- Branch: $BRANCH
- Last commit: $LAST_COMMIT
- Uncommitted changes: $DIRTY files
- Project dir: $PROJECT_DIR"
fi

# Detect project-specific context
case "$CWD" in
  */social-intelligence-unit*)
    CONTEXT="$CONTEXT
- Project: SIU (Competitive Intelligence)
- Phase: 1 - Local POC (ROI >15% target)
- Stack: FastAPI+SQLite | Next.js 14 | GPT-5 Nano/Mini
- Env: LOCAL (not staging/prod)"
    ;;
  */figma-4-all*)
    CONTEXT="$CONTEXT
- Project: Figma4All (Banner Generator Plugin)
- Runtime: ES2017 (NO modern JS features)
- Stack: Bun + esbuild | Playwright | Vitest"
    ;;
  */el-vadt*)
    CONTEXT="$CONTEXT
- Project: el-vadt
- Note: Check CLAUDE.md for project-specific constraints"
    ;;
esac

if [ -n "$CONTEXT" ]; then
  # Escape for JSON
  ESCAPED=$(echo "$CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null | sed 's/^"//;s/"$//')
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$ESCAPED"
  }
}
EOF
else
  echo '{}'
fi

exit 0
