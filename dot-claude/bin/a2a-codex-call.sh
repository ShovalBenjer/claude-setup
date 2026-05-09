#!/usr/bin/env bash
# a2a-codex-call.sh — synchronous bridge from Claude → Codex CLI (gpt-5.5).
#
# Wraps `codex exec --full-auto` with timeout, audit logging, and the
# A2A response shape (JSON to stdout matching a2a-foundry-call.py).
#
# Auth: chatgpt subscription (auth_mode=chatgpt). $0 marginal cost.
#
# Usage:
#     a2a-codex-call.sh "<prompt>" [--timeout 60] [--effort medium] [--model gpt-5.5]
#     a2a-codex-call.sh "review src/handler.py for SQL injection" --effort high
#
# Output: JSON to stdout: {state, response_text, duration_ms, error?}
# Audit:  ~/.claude/cache/a2a/audit.jsonl
# Exit:   0 = completed, 1 = failed/timeout, 2 = config error

set -euo pipefail

PROMPT=""
TIMEOUT=60
EFFORT="medium"
MODEL=""
FROM_ADDR="claude:home"
TO_ADDR="codex:home"
CONV_ID=""

while [ $# -gt 0 ]; do
    case "$1" in
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --effort) EFFORT="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --from-addr) FROM_ADDR="$2"; shift 2 ;;
        --conversation-id) CONV_ID="$2"; shift 2 ;;
        --help) echo "usage: a2a-codex-call.sh \"<prompt>\" [--timeout N] [--effort low|medium|high|xhigh] [--model gpt-5.5]"; exit 0 ;;
        *)
            if [ -z "$PROMPT" ]; then PROMPT="$1"; shift
            else echo "unknown arg: $1" >&2; exit 2
            fi
            ;;
    esac
done

if [ -z "$PROMPT" ]; then
    echo '{"state":"failed","error":"empty prompt"}'
    exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
    echo '{"state":"failed","error":"codex CLI not on PATH"}'
    exit 2
fi

# Audit prep
PROMPT_HASH=$(echo -n "$PROMPT" | sha1sum | cut -c1-12)
TMPOUT=$(mktemp)
trap "rm -f $TMPOUT" EXIT

# Build codex args
CODEX_ARGS=(exec --full-auto --skip-git-repo-check -C "$PWD" --output-last-message "$TMPOUT")
[ -n "$MODEL" ] && CODEX_ARGS+=(-m "$MODEL")
[ -n "$EFFORT" ] && CODEX_ARGS+=(-c "reasoning_effort=$EFFORT")

# Time the call (millisecond precision)
T_START=$(date +%s%3N 2>/dev/null || date +%s)
TMPERR=$(mktemp)
trap "rm -f $TMPOUT $TMPERR" EXIT

# Run codex with timeout. Capture stderr so we can surface real errors
# (rate limits, auth failures, sandbox issues) instead of swallowing them.
if timeout --signal=TERM "${TIMEOUT}s" codex "${CODEX_ARGS[@]}" - <<<"$PROMPT" >/dev/null 2>"$TMPERR"; then
    STATE="completed"
else
    EXIT_CODE=$?
    STATE="failed"
    [ "$EXIT_CODE" -eq 124 ] && STATE="timeout"
fi

T_END=$(date +%s%3N 2>/dev/null || date +%s)
DURATION_MS=$((T_END - T_START))

# Surface common error patterns from stderr
ERR_MSG=""
if [ "$STATE" != "completed" ] && [ -s "$TMPERR" ]; then
    # Extract the most informative line (rate limit, auth, etc.)
    if grep -qE "usage limit|rate limit|429" "$TMPERR"; then
        ERR_MSG=$(grep -E "usage limit|rate limit|429" "$TMPERR" | head -1)
        STATE="rate_limited"
    elif grep -qE "unauthorized|401|auth" "$TMPERR"; then
        ERR_MSG=$(grep -iE "unauthorized|401|auth" "$TMPERR" | head -1)
        STATE="auth_failed"
    else
        ERR_MSG=$(tail -3 "$TMPERR" | tr '\n' ' ' | head -c 300)
    fi
fi

# Audit log (state may now be rate_limited or auth_failed for clearer diagnostics)
python3 "$HOME/.claude/bin/a2a-audit.py" log \
    "$FROM_ADDR" "$TO_ADDR" "$PROMPT_HASH" "$DURATION_MS" "$STATE" "$CONV_ID" \
    >/dev/null 2>&1 || true

# Persist the stderr tail to ~/.claude/cache/a2a/codex-errors.log for postmortem
if [ -n "$ERR_MSG" ]; then
    mkdir -p "$HOME/.claude/cache/a2a"
    echo "[$(date -u +%FT%TZ)] codex-call state=$STATE duration=${DURATION_MS}ms err=$ERR_MSG" \
        >> "$HOME/.claude/cache/a2a/codex-errors.log"
fi

# Emit JSON response (now includes error message when not completed)
RESP_TEXT=""
[ "$STATE" = "completed" ] && RESP_TEXT=$(cat "$TMPOUT" 2>/dev/null || echo "")
python3 -c "
import json
out = {
    'state': '$STATE',
    'agent': 'codex',
    'from': '$FROM_ADDR',
    'to': '$TO_ADDR',
    'response_text': '''${RESP_TEXT//\'/\\\'}''',
    'duration_ms': $DURATION_MS,
    'conversation_id': '$CONV_ID' or None,
    'effort': '$EFFORT',
    'model': '$MODEL' or 'gpt-5.5',
}
err = '''${ERR_MSG//\'/\\\'}'''.strip()
if err:
    out['error'] = err
print(json.dumps(out, indent=2, ensure_ascii=False))
"

[ "$STATE" = "completed" ] && exit 0 || exit 1
