#!/usr/bin/env bash
# visual-explainer-trigger.sh — UserPromptSubmit hook
#
# Detects user phrases that signal "i don't understand, show me a visual"
# in English, Hebrew, and a few common Arabic phrases. On match, injects
# additional context nudging Claude to invoke the /visual-explainer skill.
#
# Registered in ~/.claude/settings.json under hooks.UserPromptSubmit.
#
# Input (stdin): JSON  { "prompt": "...", ... }
# Output (stdout): JSON
#   - hit:    {"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}
#   - no-hit: {}
#
# Cooldown: 1 hit per 60 seconds to avoid spamming context on repeated phrasings.

set -euo pipefail

INPUT=$(cat)
COOLDOWN_FILE="/tmp/.claude-visual-explainer-cooldown"
COOLDOWN_SECS=60

PROMPT=$(printf '%s' "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "")

if [ -z "$PROMPT" ]; then
  echo '{}'
  exit 0
fi

# Trigger phrases: English, Hebrew, Arabic
# Use grep -E with the | alternation; case-insensitive via -i
TRIGGER_RE="i don'?t understand|i dont understand|im lost|i'?m lost|im confused|i'?m confused|explain visually|show me a diagram|draw it|visualize this|make a picture|make a diagram|can you draw|i can'?t picture|i cant picture|איני מבין|לא מבין|תסביר ויזואלית|תסביר לי בויזואל|תראה לי דיאגרמה|תצייר|לא הבנתי|لا أفهم|اشرح بالصورة"

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
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"User signal detected: visual explanation needed. Consider invoking the /visual-explainer skill (defined at ~/.codex/skills/visual-explainer/SKILL.md). Run ~/.claude/bin/generate-visual.py with a clear technical-diagram prompt, then embed the returned markdown reference inline in your response. Use one image, default size 1024x1024 unless the concept needs wide (1536x1024) or tall (1024x1536). Caption what the image shows."}}
EOF
