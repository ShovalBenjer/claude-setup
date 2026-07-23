#!/usr/bin/env bash
# codex-review-on-push.sh -- PreToolUse(Bash, if git push): Codex (the junior) reviews the
# diff about to be pushed, READ-ONLY, and injects its findings back to the senior (Claude) as
# additionalContext. It NEVER emits a permissionDecision, so it can never block or deny the
# push; other PreToolUse guards decide that. Uses the existing $0 a2a-codex-call.sh bridge.
#
# Safety: read-only sandbox (Codex cannot edit/commit/push), secret paths excluded from the
# diff, secret-pattern guard, size-gated, skips $HOME (HOME-as-repo), skips automation runs.
set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"

# Skip real automation (overnight loop / Codex-driven runs).
{ [ -n "${CLAUDE_LOOP_MODE:-}" ] || [ -n "${CODEX_AUTOMATION_ID:-}" ]; } && { echo '{}'; exit 0; }

CALL="$HOME/.claude/bin/a2a-codex-call.sh"
[ -x "$CALL" ] || { echo '{}'; exit 0; }

CWD="$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || true)"
[ -n "$CWD" ] || CWD="$PWD"
cd "$CWD" 2>/dev/null || { echo '{}'; exit 0; }

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || { echo '{}'; exit 0; }
[ "$ROOT" = "$HOME" ] && { echo '{}'; exit 0; }   # never review the HOME-as-repo worktree

# Diff about to be pushed (exact, pre-push). Exclude secret-bearing paths.
EXCL=(':(exclude).env' ':(exclude).env.*' ':(exclude)*.pem' ':(exclude)*.key' ':(exclude)**/secrets/**' ':(exclude)**/.ssh/**')
if git rev-parse '@{u}' >/dev/null 2>&1; then
  DIFF="$(git diff '@{u}'..HEAD -- "${EXCL[@]}" 2>/dev/null || true)"
else
  DIFF="$(git diff HEAD~1..HEAD -- "${EXCL[@]}" 2>/dev/null || true)"
fi

LINES=$(printf '%s\n' "$DIFF" | wc -l)
# Skip trivial (<8 lines) and oversized (>2000 lines) diffs.
{ [ "$LINES" -lt 8 ] || [ "$LINES" -gt 2000 ]; } && { echo '{}'; exit 0; }

# Secret-pattern guard: never send credential-looking content to the model.
if printf '%s' "$DIFF" | grep -Eiq '(api[_-]?key|secret[_-]?key|password|bearer [a-z0-9]|private[_-]?key|BEGIN (RSA|OPENSSH|EC|PGP) )'; then
  echo '{}'; exit 0
fi

PROMPT="You are a junior code reviewer. Review this git diff (repo $(basename "$ROOT")) for REAL correctness bugs, security issues, and boundary/error-handling gaps only. Be terse. Output at most 6 findings, each one line as FILE:LINE - issue. Do not restate the diff, do not praise, do not suggest style nits. If nothing material, output exactly: CLEAN.

$DIFF"

if [ -n "${CODEX_REVIEW_DRYRUN:-}" ]; then
  printf 'DRYRUN repo=%s diff_lines=%s sandbox=read-only would_call_codex=yes\n' "$(basename "$ROOT")" "$LINES" >&2
  echo '{}'; exit 0
fi

RESP="$(timeout 130 "$CALL" "$PROMPT" --sandbox read-only --effort low --timeout 120 2>/dev/null || true)"
TEXT="$(printf '%s' "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('response_text','').strip())" 2>/dev/null || true)"

# No usable response, or explicitly clean -> stay silent, do not vote on the push.
{ [ -z "$TEXT" ] || printf '%s' "$TEXT" | grep -qx 'CLEAN'; } && { echo '{}'; exit 0; }

MSG="CODEX JUNIOR REVIEW of the diff being pushed ($(basename "$ROOT")). Second opinion, verify before trusting, this does not block the push:
$TEXT"
python3 -c "import json,sys;print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','additionalContext':sys.argv[1]}}))" "$MSG"
exit 0
