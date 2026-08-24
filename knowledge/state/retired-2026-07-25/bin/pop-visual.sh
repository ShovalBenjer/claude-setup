#!/usr/bin/env bash
# pop-visual.sh — display a generated visual in a fire-and-forget popup window
#
# Same pattern as play-meme.sh: ffplay window, disowned, no autoexit
# (image persists until user closes it). 5s cooldown between pops.
#
# Usage: pop-visual.sh <png-path> [width] [height]
# Default size: 1000x720 (matches typical 1024x1024 / 1536x1024 generated images,
# leaves room for window chrome).

PNG="${1:-}"
W="${2:-1000}"
H="${3:-720}"

[ -z "$PNG" ] && { echo "usage: pop-visual.sh <png-path> [width] [height]" >&2; exit 1; }
[ -f "$PNG" ] || { echo "no such file: $PNG" >&2; exit 1; }

# Honor session-level visual disable flag (mirror of meme pattern)
[ -f /tmp/.claude-visual-disabled ] && exit 0

# Cooldown 5s between pops (avoid stacking windows on rapid invocations)
COOLDOWN_DIR="/tmp/.claude-visual-cooldown"
mkdir -p "$COOLDOWN_DIR" 2>/dev/null
LAST_FILE="$COOLDOWN_DIR/last"
if [ -f "$LAST_FILE" ]; then
  LAST=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ "$LAST" -gt 0 ] && [ $((NOW - LAST)) -lt 5 ]; then
    exit 0
  fi
fi
date +%s > "$LAST_FILE"

# Counter (status-line integration)
COUNTER_FILE="/tmp/.claude-visual-count"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
[[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
echo $((COUNT + 1)) > "$COUNTER_FILE"

# Log
LOG_FILE="/tmp/.claude-visual-log"
echo "$(date +%s) $PNG" >> "$LOG_FILE"

TITLE="Visual: $(basename "$PNG" .png)"

# ffplay: -loop 0 keeps the still image displayed; user closes with 'q' or window-X.
# WSLg renders as a Windows window via Wayland.
ffplay \
  -loop 0 \
  -window_title "$TITLE" \
  -x "$W" -y "$H" \
  -loglevel quiet \
  "$PNG" </dev/null >/dev/null 2>&1 &

disown 2>/dev/null
exit 0
