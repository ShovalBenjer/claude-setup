#!/usr/bin/env bash
# pop-voice.sh — fire-and-forget audio playback for generated voice files
#
# ffplay -nodisp -autoexit plays the audio with no window and exits when
# done, so the caller never blocks on playback.
#
# Usage: pop-voice.sh <mp3-path>

MP3="${1:-}"
[ -z "$MP3" ] && { echo "usage: pop-voice.sh <mp3-path>" >&2; exit 1; }
[ -f "$MP3" ] || { echo "no such file: $MP3" >&2; exit 1; }

# Honor session-level voice disable flag
[ -f /tmp/.claude-voice-disabled ] && exit 0

# Cooldown 3s between pops to avoid overlapping playback
COOLDOWN_DIR="/tmp/.claude-voice-cooldown"
mkdir -p "$COOLDOWN_DIR" 2>/dev/null
LAST_FILE="$COOLDOWN_DIR/last"
if [ -f "$LAST_FILE" ]; then
  LAST=$(cat "$LAST_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ "$LAST" -gt 0 ] && [ $((NOW - LAST)) -lt 3 ]; then
    exit 0
  fi
fi
date +%s > "$LAST_FILE"

# Counter
COUNTER_FILE="/tmp/.claude-voice-count"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
[[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
echo $((COUNT + 1)) > "$COUNTER_FILE"

# Log
echo "$(date +%s) $MP3" >> /tmp/.claude-voice-log

# Audio playback: no display, autoexit when done
ffplay \
  -nodisp \
  -autoexit \
  -loglevel quiet \
  "$MP3" </dev/null >/dev/null 2>&1 &

disown 2>/dev/null
exit 0
