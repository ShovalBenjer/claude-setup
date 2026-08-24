#!/usr/bin/env bash
# Set GEMINI_API_KEY as an Actions secret on every non-fork, non-archived
# ShovalBenjer repo (unblocks AUTO-10: gemini-review.yml second-model reviewer).
# Usage: GEMINI_API_KEY=<key> bash tools/rollout_gemini_key.sh [--dry-run]
# Get a free key at https://aistudio.google.com/apikey (AI Studio free tier).
set -u
[ -z "${GEMINI_API_KEY:-}" ] && { echo "GEMINI_API_KEY env not set"; exit 1; }
DRY="${1:-}"
repos=$(gh repo list ShovalBenjer --limit 200 --source --no-archived --json name -q '.[].name')
ok=0; fail=0
for r in $repos; do
  if [ "$DRY" = "--dry-run" ]; then echo "would set: $r"; continue; fi
  if gh secret set GEMINI_API_KEY -R "ShovalBenjer/$r" --body "$GEMINI_API_KEY" >/dev/null 2>&1; then
    echo "set: $r"; ok=$((ok+1))
  else
    echo "FAILED: $r"; fail=$((fail+1))
  fi
done
echo "---"
echo "set=$ok failed=$fail"
