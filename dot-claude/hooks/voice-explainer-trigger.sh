#!/usr/bin/env bash
# voice-explainer-trigger.sh — UserPromptSubmit hook
#
# Detects user phrases that signal "i'm out of focus / read it to me / narrate"
# in English, Hebrew, and a few common Arabic phrases. On match, injects
# additional context nudging Claude to invoke the /voice-explainer skill.
#
# Registered in ~/.claude/settings.json under hooks.UserPromptSubmit.
#
# Cooldown: 1 hit per 90 seconds (audio nudges are louder than visual; cooldown longer).

set -euo pipefail

INPUT=$(cat)
COOLDOWN_FILE="/tmp/.claude-voice-explainer-cooldown"
COOLDOWN_SECS=90

PROMPT=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "")

if [ -z "$PROMPT" ]; then
  echo '{}'
  exit 0
fi

# Trigger phrases — out-of-focus + narration requests, en + he + ar
TRIGGER_RE="i'?m tired|im tired|i'?m out of focus|im out of focus|out of focus|tell me what you'?re doing|narrate this|narrate it|say it out loud|say it aloud|read it to me|read this to me|im zoning out|i'?m zoning out|audio it|audio mode|tldr audio|אני עייף|אני לא מתרכז|תקריא לי|תקרא לי|תגיד בקול|תספר לי|באודיו|אודיו|أنا متعب|اقرأ لي"

if ! printf '%s' "$PROMPT" | grep -qiE "$TRIGGER_RE"; then
  echo '{}'
  exit 0
fi

# Cooldown check
if [ -f "$COOLDOWN_FILE" ]; then
  LAST=$(stat -c %Y "$COOLDOWN_FILE" 2>/dev/null || echo 0)
  NOW=$(date +%s)
  if [ $((NOW - LAST)) -lt "$COOLDOWN_SECS" ]; then
    echo '{}'
    exit 0
  fi
fi
touch "$COOLDOWN_FILE"

cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"User signal detected: out-of-focus or audio-narration request. Consider invoking the /voice-explainer skill (~/.codex/skills/voice-explainer/SKILL.md). Generate a short narration (60-120 words max) of what you're currently doing or planning, in plain conversational tone. Match the user's language (Hebrew if they wrote Hebrew, English if English, Arabic if Arabic). Run ~/.claude/bin/generate-voice.py with --voice calm_female (default) and embed the markdown reference inline. Do not narrate code; narrate what code is for and what's happening next."}}
EOF
