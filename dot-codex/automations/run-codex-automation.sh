#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:-}"
BASE_DIR="${CODEX_AUTOMATIONS_HOME:-$HOME/.codex/automations}"
PROMPT_FILE="$BASE_DIR/prompts/${JOB_ID}.md"
LOG_DIR="$BASE_DIR/logs"
LAST_DIR="$BASE_DIR/last-messages"
LOCK_ROOT="$BASE_DIR/locks"

if [[ -z "$JOB_ID" || "$JOB_ID" == "--help" || "$JOB_ID" == "-h" ]]; then
    echo "Usage: $0 <automation-id>"
    echo "Example: $0 a01-memory-curator-sweep"
    exit 2
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: prompt file not found: $PROMPT_FILE" >&2
    exit 2
fi

mkdir -p "$LOG_DIR" "$LAST_DIR" "$LOCK_ROOT"

RUN_STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
LOG_FILE="$LOG_DIR/${JOB_ID}-${RUN_STAMP}.log"
LAST_FILE="$LAST_DIR/${JOB_ID}-${RUN_STAMP}.md"
LOCK_DIR="$LOCK_ROOT/${JOB_ID}.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $JOB_ID already running; skipping." | tee -a "$LOG_FILE"
    exit 0
fi

cleanup() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT

exec > >(tee -a "$LOG_FILE") 2>&1

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Starting Codex automation: $JOB_ID"
echo "Prompt: $PROMPT_FILE"
echo "Last-message output: $LAST_FILE"

if ! command -v codex >/dev/null 2>&1; then
    echo "ERROR: codex CLI not found on PATH." >&2
    exit 127
fi

export HOME="${HOME:-/home/shovalbe}"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export CLAUDE_LOOP_MODE="${CLAUDE_LOOP_MODE:-nightly}"
export HIVE_HOME="${HIVE_HOME:-$HOME/.hive}"
export PATH="$HIVE_HOME/bin:$PATH"
export CODEX_MODEL="${CODEX_MODEL:-gpt-5.5}"
export CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
export CODEX_AUTOMATION_ID="$JOB_ID"
export CODEX_AUTOMATION_RUN_AT="$RUN_STAMP"

if [[ -f "$HOME/.codex/secrets/runtime/global.env" ]]; then
    set +u
    set -a
    # shellcheck disable=SC1091
    source "$HOME/.codex/secrets/runtime/global.env"
    set +a
    set -u
fi

{
    cat <<EOF
You are running as an unattended scheduled Codex automation.

Automation id: $JOB_ID
Run timestamp UTC: $RUN_STAMP
Workspace root: $HOME

Operational rules:
- Do not ask the user questions; if blocked, write the requested report with a clear BLOCKED section.
- Keep changes scoped to the automation prompt.
- Never delete files or secrets.
- Never print credentials, tokens, email bodies, or private message bodies.
- Use model gpt-5.5 with medium reasoning unless this prompt explicitly says otherwise.
- Treat ~/.hive as the local Claude/Codex work bus. You may create local beads with bead-create when the prompt asks for actionable routing.
- Prefer writing audit/proposal output to the exact path requested by the prompt.
- If auth, network, or external services are unavailable, record that fact and exit cleanly.
- Include verification evidence in the report when commands are run.

Scheduled task prompt follows.

EOF
    cat "$PROMPT_FILE"
} | codex exec --full-auto --skip-git-repo-check -C "$HOME" \
    ${CODEX_REASONING_EFFORT:+-c reasoning_effort=$CODEX_REASONING_EFFORT} \
    ${CODEX_MODEL:+-m $CODEX_MODEL} \
    --output-last-message "$LAST_FILE" -

echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] Finished Codex automation: $JOB_ID"
