#!/usr/bin/env bash
# pop-sfx.sh — soft "Claude finished" chime for the Stop hook.
#
# Same fire-and-forget pattern as pop-voice.sh: ffplay -nodisp -autoexit plays
# the sound with no window and exits when done; we background + disown so the
# Stop hook returns immediately and never blocks the turn.
#
# Mute it for the session:  touch /tmp/.claude-sfx-disabled
# Un-mute:                   rm   /tmp/.claude-sfx-disabled
#
# Usage: pop-sfx.sh [wav-path]   (defaults to the bundled done.wav)

SFX="${1:-$HOME/.claude/assets/sfx/done.wav}"
[ -f "$SFX" ] || exit 0

# Session-level mute flag
[ -f /tmp/.claude-sfx-disabled ] && exit 0

# 2s cooldown so back-to-back stops (or several parallel sessions finishing at
# once) don't stack into an echo.
COOLDOWN="/tmp/.claude-sfx-cooldown"
if [ -f "$COOLDOWN" ]; then
  LAST=$(cat "$COOLDOWN" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  [ "$LAST" -gt 0 ] && [ $((NOW - LAST)) -lt 2 ] && exit 0
fi
date +%s > "$COOLDOWN"

ffplay -nodisp -autoexit -loglevel quiet "$SFX" </dev/null >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
