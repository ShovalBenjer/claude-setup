#!/usr/bin/env bash
# notify.sh -- production deploy / pipeline notification (house standard template).
# Reference for prod-deploy-rules rule E. Copy into a project as bin/<name>.sh.
# Modeled on the existing bin/tlg_notification.sh, with two fixes:
#   1. No emoji (uses [OK] / [FAIL] per the global output rule).
#   2. JSON-safe message encoding (handles quotes/newlines), and a guard so a
#      missing notification config never fails the pipeline.
#
# Secrets come from pipeline SECRET vars or Key Vault. Never hardcode a token.
#   NOTIFY_BOT      Telegram bot path, e.g. "bot<token>"   (SECRET)
#   NOTIFY_CHAT_ID  target chat id                         (SECRET)
# Context vars (set in the pipeline YAML):
#   STATUS          SUCCESS | FAILED   (default SUCCESS)
#   PIPELINE        pipeline / app name
#   BRANCH          source branch
#   COMMIT_AUTHOR   commit author
#   FAILED_STAGE    optional: failing stage name when STATUS=FAILED
set -euo pipefail

STATUS="${STATUS:-SUCCESS}"
PIPELINE="${PIPELINE:-pipeline}"
BRANCH="${BRANCH:-unknown}"
COMMIT_AUTHOR="${COMMIT_AUTHOR:-unknown}"
COMMIT_SUBJECT="$(git log --format=%s -n 1 2>/dev/null || echo 'n/a')"

if [ "$STATUS" = "FAILED" ]; then
  MSG="[FAIL] ${PIPELINE} FAILED on ${BRANCH}
Stage: ${FAILED_STAGE:-unknown stage}
Commit: ${COMMIT_SUBJECT} (${COMMIT_AUTHOR})"
else
  MSG="[OK] ${PIPELINE} succeeded on ${BRANCH}
Commit: ${COMMIT_SUBJECT} (${COMMIT_AUTHOR})"
fi

# Guard: a missing notification config is not a deploy failure.
if [ -z "${NOTIFY_BOT:-}" ] || [ -z "${NOTIFY_CHAT_ID:-}" ]; then
  echo "notify: NOTIFY_BOT / NOTIFY_CHAT_ID unset; skipping notification" >&2
  exit 0
fi

# JSON-encode the message body safely (quotes, newlines).
TEXT_JSON="$(printf '%s' "$MSG" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"

curl -fsS -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"chat_id\": \"${NOTIFY_CHAT_ID}\", \"text\": ${TEXT_JSON}}" \
  "https://api.telegram.org/${NOTIFY_BOT}/sendMessage" >/dev/null
