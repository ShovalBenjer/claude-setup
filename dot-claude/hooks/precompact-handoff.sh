#!/usr/bin/env bash
# PreCompact seatbelt (ADR-0010): snapshot ground truth to disk before the summarizer
# runs, and steer the summary toward the durable-handoff schema. Never blocks.
set +e
OS_DIR="$HOME/claude-setup"
LOG="$OS_DIR/state/compact-log.md"
mkdir -p "$OS_DIR/state" 2>/dev/null
{
  echo "## compact $(date '+%Y-%m-%d %H:%M')"
  echo '```'
  git -C "$OS_DIR" status -sb 2>/dev/null | head -5
  git -C "$OS_DIR" log --oneline -3 2>/dev/null
  echo '```'
} >> "$LOG" 2>/dev/null
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"COMPACT INTO A DURABLE HANDOFF (hive-mind rule): preserve verbatim - current goal, phase, lane (docs/charters.md), key decisions made this session, verification evidence (commands+output), changed files, blockers, and the exact next action. State that ground truth lives on disk: ~/claude-setup SESSION-BOOT.md, TODO.md, prd/autonomy-ecosystem.md, state/compact-log.md."}}
EOF
exit 0
