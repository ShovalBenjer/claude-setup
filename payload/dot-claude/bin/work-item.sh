#!/usr/bin/env bash
# work-item.sh — Post a comment thread to an Azure DevOps PR.
#
# Usage:
#   work-item.sh comment <pr-id> <body-file> [--dry-run]
#
# Auth (in priority order):
#   1. $SYSTEM_ACCESSTOKEN  (CI — passed in as env var; never echoed)
#   2. ambient `az login`   (local dev — uses existing az session)
#
# Prereq: "Contribute to pull requests" on the Build Service identity.
# Without that permission the API returns HTTP 403.
#
# Post mechanism:
#   az devops invoke --area git --resource pullRequestThreads
#   --route-parameters project=<P> repositoryId=<R> pullRequestId=<id>
#   --http-method POST --api-version 7.1 --in-file <json>
#
# --dry-run:  Prints the constructed az command + JSON payload (NO secret values).
#             Does NOT post anything.

set -euo pipefail

# --------------------------------------------------------------------------- #
# Config (override via env)
# --------------------------------------------------------------------------- #
ADO_ORG="${ADO_ORG:-Corp-domain}"
ADO_PROJECT="${ADO_PROJECT:-Corp-AI}"
ADO_REPO="${ADO_REPO:-axia-seekapa-cs-agents}"
ADO_ORG_URL="https://dev.azure.com/${ADO_ORG}"

# --------------------------------------------------------------------------- #
# Arg parsing
# --------------------------------------------------------------------------- #
usage() {
  echo "Usage: $0 comment <pr-id> <body-file> [--dry-run]" >&2
  exit 1
}

SUBCOMMAND="${1:-}"
PR_ID="${2:-}"
BODY_FILE="${3:-}"
DRY_RUN=false

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

[[ "$SUBCOMMAND" == "comment" ]] || usage
[[ -n "$PR_ID" ]] || { echo "[work-item] ERROR: pr-id is required" >&2; exit 1; }
[[ -n "$BODY_FILE" ]] || { echo "[work-item] ERROR: body-file is required" >&2; exit 1; }
[[ -f "$BODY_FILE" ]] || { echo "[work-item] ERROR: body-file not found: $BODY_FILE" >&2; exit 1; }

# --------------------------------------------------------------------------- #
# Read body and build JSON payload
# --------------------------------------------------------------------------- #
BODY_CONTENT=$(cat "$BODY_FILE")

# Build JSON payload file (jq escapes content safely — no raw heredoc injection)
PAYLOAD_FILE=$(mktemp /tmp/work-item-payload-XXXXXX.json)
trap 'rm -f "$PAYLOAD_FILE"' EXIT

jq -n \
  --arg body "$BODY_CONTENT" \
  '{
    "comments": [
      {
        "parentCommentId": 0,
        "content": $body,
        "commentType": 1
      }
    ],
    "status": 1
  }' > "$PAYLOAD_FILE"

# --------------------------------------------------------------------------- #
# Build the az devops invoke command (array form for clean display)
# --------------------------------------------------------------------------- #
AZ_CMD=(
  az devops invoke
  --area git
  --resource pullRequestThreads
  --route-parameters
    "project=${ADO_PROJECT}"
    "repositoryId=${ADO_REPO}"
    "pullRequestId=${PR_ID}"
  --http-method POST
  --api-version 7.1
  --in-file "$PAYLOAD_FILE"
  --org "$ADO_ORG_URL"
  --output json
)

# --------------------------------------------------------------------------- #
# Dry-run: print command + payload, exit without posting
# --------------------------------------------------------------------------- #
if [[ "$DRY_RUN" == true ]]; then
  echo "=== [work-item --dry-run] Constructed command ==="
  echo ""
  # Print each arg on its own line for readability; token never printed
  printf '  %s\n' "${AZ_CMD[@]}"
  echo ""
  echo "=== Payload (${PAYLOAD_FILE}) ==="
  # Show payload but mask the body content beyond first line for safety
  BODY_LINES=$(wc -l < "$BODY_FILE")
  echo "{\"comments\":[{\"parentCommentId\":0,\"content\":\"<body from ${BODY_FILE} — ${BODY_LINES} lines, not echoed>\",\"commentType\":1}],\"status\":1}"
  echo ""
  echo "[work-item --dry-run] Nothing posted."
  exit 0
fi

# --------------------------------------------------------------------------- #
# Live run: configure auth then invoke
# --------------------------------------------------------------------------- #

# Auth: if SYSTEM_ACCESSTOKEN is set (CI), pipe it into az devops login.
# Token is never echoed; we only check presence.
if [[ -n "${SYSTEM_ACCESSTOKEN:-}" ]]; then
  echo "[work-item] Auth: SYSTEM_ACCESSTOKEN present — logging in (token not echoed)"
  printf '%s' "$SYSTEM_ACCESSTOKEN" | az devops login --org "$ADO_ORG_URL" 2>/dev/null
else
  echo "[work-item] Auth: using ambient az login session"
fi

echo "[work-item] Posting comment to PR #${PR_ID} in ${ADO_PROJECT}/${ADO_REPO}..."
RESULT=$("${AZ_CMD[@]}")

THREAD_ID=$(echo "$RESULT" | jq -r '.id // "unknown"' 2>/dev/null || echo "unknown")
echo "[work-item] Posted. thread_id=${THREAD_ID}"
