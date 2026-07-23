#!/usr/bin/env bash
# Roll out .github/workflows/claude-code-review.yml to every non-fork, non-archived
# ShovalBenjer repo via the GitHub contents API. Idempotent: updates if present.
# Usage: rollout_pr_review.sh [--dry-run]
set -u
TEMPLATE="$(dirname "$0")/../github/claude-code-review.yml"
DEST=".github/workflows/claude-code-review.yml"
DRY="${1:-}"
B64=$(base64 -w0 < "$TEMPLATE")
repos=$(gh repo list ShovalBenjer --limit 200 --source --no-archived --json name -q '.[].name')
ok=0; fail=0; skip=0
for r in $repos; do
  if [ "$DRY" = "--dry-run" ]; then echo "would update: $r"; continue; fi
  sha=$(gh api "repos/ShovalBenjer/$r/contents/$DEST" -q .sha 2>/dev/null || true)
  if [ -n "$sha" ]; then
    existing=$(gh api "repos/ShovalBenjer/$r/contents/$DEST" -q .content 2>/dev/null | tr -d '\n')
    if [ "$existing" = "$B64" ]; then echo "unchanged: $r"; skip=$((skip+1)); continue; fi
    args=(-f message="ci: update Claude always-fresh PR review workflow" -f content="$B64" -f sha="$sha")
  else
    args=(-f message="ci: add Claude always-fresh PR review workflow" -f content="$B64")
  fi
  if gh api -X PUT "repos/ShovalBenjer/$r/contents/$DEST" "${args[@]}" >/dev/null 2>&1; then
    echo "updated: $r"; ok=$((ok+1))
  else
    echo "FAILED: $r"; fail=$((fail+1))
  fi
done
echo "---"
echo "updated=$ok unchanged=$skip failed=$fail"
