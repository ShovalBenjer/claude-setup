#!/bin/bash
set -euo pipefail

# Protected Infrastructure Files Hook
# Blocks edits to critical infra files unless explicitly approved.
# Fires on PreToolUse for Edit and Write operations.

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('file_path',''))" 2>/dev/null || echo "")

# Only check Edit and Write tools
if [ "$TOOL_NAME" != "Edit" ] && [ "$TOOL_NAME" != "Write" ]; then
  echo '{}'
  exit 0
fi

# Protected file patterns
PROTECTED=false
REASON=""

case "$FILE_PATH" in
  *azure-pipelines.yml|*azure-pipelines.yaml)
    PROTECTED=false
    REASON=""
    ;;
  *Dockerfile*|*docker-compose*)
    PROTECTED=true
    REASON="Container infrastructure. Changes require review and test pass."
    ;;
  *.tf|*.tfvars|*main.bicep|*parameters.json)
    PROTECTED=true
    REASON="Infrastructure-as-Code file. Changes must be proposed as IaC diffs."
    ;;
  *.env|*.env.production|*.env.staging)
    PROTECTED=true
    REASON="Environment configuration. Never edit secrets directly."
    ;;
  *CORS*|*cors*config*)
    PROTECTED=true
    REASON="CORS configuration. Changes require security review."
    ;;
esac

# Check for secret patterns in content
if [ "$TOOL_NAME" = "Write" ]; then
  CONTENT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")
  if echo "$CONTENT" | grep -qiE '(api[_-]?key|secret|password|token)\s*[:=]\s*["\x27][A-Za-z0-9+/=]{16,}'; then
    PROTECTED=true
    REASON="Detected potential hardcoded secret. Use environment variables instead."
  fi
fi

if [ "$PROTECTED" = "true" ]; then
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "PROTECTED INFRA: $REASON",
    "additionalContext": "Reviewer checklist before approving: (1) ticket/spec referenced, (2) tests cover the change, (3) blast-radius understood."
  }
}
EOF
else
  echo '{}'
fi

exit 0
