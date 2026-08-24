#!/bin/bash
set -euo pipefail

# Post-Compaction Re-Injection Hook
# Fires on SessionStart after a /compact or auto-compact event.
# Re-injects critical invariants that compaction may have summarized away.

INPUT=$(cat)
SOURCE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source',''))" 2>/dev/null || echo "")
CWD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || echo "")

# Only fire on compact-triggered restarts
if [ "$SOURCE" != "compact" ]; then
  echo '{}' 
  exit 0
fi

CONTEXT=""

# Detect project from CWD and inject relevant invariants
case "$CWD" in
  */social-intelligence-unit*)
    CONTEXT="POST-COMPACTION CRITICAL CONSTRAINTS (SIU):
- Signal score: 0.0-5.0 (NOT 0-1). Tier: S/A/B/C only. Confidence: high|degraded.
- Geo: SA, AE, QA only (Phase 1). Platform: meta|tiktok.
- Quality Gates: schema→freshness(≤7d)→geo→relevance(≥0.7)→media(CER<5%,WER<10%).
- Failed runs: gate_pass=false, confidence=degraded — NEVER use for analysis.
- Immutable raw storage: data/runs/<run_id>/raw/ is append-only.
- API P95 <200ms. Parameterized SQL only. DOMPurify for HTML.
- Stack: FastAPI+SQLite | Next.js 14 | GPT-5 Nano/Mini via Azure AI Foundry.
- Tooling: uv (Python), bun (JS). NEVER pip/npm/npx/yarn."
    ;;
  */figma-4-all*)
    CONTEXT="POST-COMPACTION CRITICAL CONSTRAINTS (Figma4All):
- ES2017 ONLY: NO optional chaining (?.), nullish coalescing (??), BigInt.
- Always run 'bun run validate:syntax' before committing.
- Aspect ratio lock MUST be applied BEFORE constraint solving (prevents distortion).
- Semantic types: BACKGROUND, HERO, HEADLINE, CTA, LOGO, UNCATEGORIZED.
- Target formats: STORY(1080x1920), SQ(1080x1080), PORT(1080x1440), LAND(1200x628).
- Tooling: bun/bunx ONLY. NEVER npm/npx/yarn.
- Test workflow: test:p0 (pre-commit) → test:staged (PR) → qa (VABB metrics)."
    ;;
  */el-vadt*)
    CONTEXT="POST-COMPACTION CRITICAL CONSTRAINTS (el-vadt):
- Diarization must be deterministic for same input.
- No duplicate segments allowed.
- Latency bounds must be respected.
- CRM contracts are immutable once published."
    ;;
  *)
CONTEXT="POST-COMPACTION REMINDER:
- Continue the previous task immediately. Do not stop just because compaction happened.
- Rebuild the task state from the snapshot below, then proceed with the next concrete action.
- Tooling: bun/bunx for JS, uv for Python. NEVER npm/pip.
- Always run tests before committing.
- Prefer minimal diffs. Do not refactor unless asked."
    ;;
esac

# Layer 7 closure: read the latest pre-compact snapshot if one exists.
# Pairs with ~/.codex/hooks/snapshot-state.sh which writes to the same pointer.
SNAP_POINTER="$HOME/.claude/observability/snapshots/.latest-pre-compact"
if [ -f "$SNAP_POINTER" ]; then
  SNAP_FILE=$(cat "$SNAP_POINTER" 2>/dev/null || echo "")
  if [ -n "$SNAP_FILE" ] && [ -f "$SNAP_FILE" ]; then
    SNAP_SUMMARY=$(python3 - "$SNAP_FILE" "$CWD" 2>/dev/null <<'PY'
import json, sys
try:
    snap_file, cwd = sys.argv[1], sys.argv[2]
    d = json.load(open(snap_file))
    snap_cwd = d.get('cwd') or ''
    if cwd and snap_cwd and snap_cwd != cwd:
        print('snap-skipped-cwd-mismatch')
        raise SystemExit(0)
    branch = d.get('git_branch') or '?'
    head = d.get('git_head') or '?'
    uncommitted = d.get('uncommitted_files', [])
    n = len(uncommitted) if isinstance(uncommitted, list) else int(uncommitted or 0)
    print(f"branch={branch} head={head} uncommitted={n} cwd={snap_cwd}")
except Exception as e:
    print('snap-load-failed')
PY
)
    if [ "$SNAP_SUMMARY" != "snap-skipped-cwd-mismatch" ]; then
      CONTEXT="$CONTEXT

PRE-COMPACT SNAPSHOT (re-injecting state lost in summary): $SNAP_SUMMARY
Snapshot: $SNAP_FILE"
    fi
  fi
fi

# Output additional context to be injected into the session
# Note: jq used to safely escape multi-line CONTEXT for JSON
if command -v jq >/dev/null 2>&1; then
  CONTEXT_JSON=$(printf '%s' "$CONTEXT" | jq -Rs .)
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": $CONTEXT_JSON
  }
}
EOF
else
  # Fallback: python json.dumps for safe escaping
  CONTEXT_JSON=$(printf '%s' "$CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": $CONTEXT_JSON
  }
}
EOF
fi
exit 0
