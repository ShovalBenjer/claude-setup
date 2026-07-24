#!/usr/bin/env bash
# PreCompact seatbelt (ADR-0010): snapshot ground truth to disk before the summarizer
# runs, and steer the summary toward the durable-handoff schema. Never blocks.
set +e
OS_DIR="$HOME/claude-setup"
LOG="$OS_DIR/state/compact-log.md"
mkdir -p "$OS_DIR/state" 2>/dev/null
# Fire-log (L011): durable proof the hook ran inside the harness.
printf '%s\tPreCompact\n' "$(date '+%Y-%m-%dT%H:%M:%S')" \
  >> "$OS_DIR/state/hook-fires.log" 2>/dev/null || true
{
  echo "## compact $(date '+%Y-%m-%d %H:%M')"
  echo '```'
  git -C "$OS_DIR" status -sb 2>/dev/null | head -5
  git -C "$OS_DIR" log --oneline -3 2>/dev/null
  echo '```'
} >> "$LOG" 2>/dev/null
# NOTE: PreCompact supports no additionalContext (verified vs hooks docs 2026-07-24);
# summarizer steering lives in session-recall.sh (SessionStart source=compact) instead.
# This hook's whole job is the disk snapshot above.
exit 0
