#!/bin/bash
# Sends a Telegram build notification.
# Required env: BOT, CHAT_ID, PIPELINE, BRANCH, STATUS, DEPLOY_TIME, COMMIT_AUTHOR
# Optional env:  BUILD_ID, BUILD_URL

COMMIT_MESSAGE=$(git log --format=%B -n 1 2>/dev/null | head -5)
STATUS=${STATUS:-SUCCESS}

if [ "$STATUS" == "FAILED" ]; then
    ICON="❌"
    LABEL="Build FAILED"
else
    ICON="✅"
    LABEL="Build Succeeded"
fi

MSG="${ICON} *${LABEL}*
📦 *Pipeline:* \`${PIPELINE}\`
🌿 *Branch:* \`${BRANCH}\`
👤 *Author:* ${COMMIT_AUTHOR}
💬 *Commit:* ${COMMIT_MESSAGE}
🕐 *Time:* ${DEPLOY_TIME}"

if [ -n "${BUILD_ID:-}" ]; then
    MSG="${MSG}
🔢 *Build ID:* ${BUILD_ID}"
fi

if [ -n "${BUILD_URL:-}" ]; then
    MSG="${MSG}
🔗 [View Pipeline Run](${BUILD_URL})"
fi

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://api.telegram.org/$BOT/sendMessage" \
    -d "chat_id=${CHAT_ID}" \
    -d "parse_mode=Markdown" \
    --data-urlencode "text=${MSG}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "Telegram notification failed (HTTP $HTTP_CODE): $BODY"
    exit 1
fi

echo "Telegram notification sent (HTTP $HTTP_CODE)"
