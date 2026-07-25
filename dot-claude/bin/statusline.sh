#!/usr/bin/env bash
# ISDD AI Department — Claude Code Status Line
# Monitors: context bar | model | cost | git state | project | health | workflow phase
# Input: JSON from stdin with session metadata

INPUT=$(cat)

# DEBUG: capture raw stdin only when explicitly enabled
if [ "${CLAUDE_STATUSLINE_DEBUG:-0}" = "1" ]; then
  echo "$INPUT" > /tmp/.claude-statusline-debug.json
fi

# Parse fields from JSON (graceful fallback for each)
CONTEXT_PCT=$(echo "$INPUT" | jq -r '(.context_window.used_percentage // 0) | floor' 2>/dev/null)
MODEL=$(echo "$INPUT" | jq -r 'if (.model | type) == "object" then (.model.id // .model.display_name // "unknown") else (.model // "unknown") end' 2>/dev/null)
COST=$(echo "$INPUT" | jq -r '.cost.total_cost_usd // .cost.total // 0' 2>/dev/null)
TURNS=$(echo "$INPUT" | jq -r '.turns // 0' 2>/dev/null)
WORKDIR=$(echo "$INPUT" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)
PROJECT_DIR=$(echo "$INPUT" | jq -r '.workspace.project_dir // empty' 2>/dev/null)

# Normalize numeric fallbacks
[[ "$CONTEXT_PCT" =~ ^[0-9]+$ ]] || CONTEXT_PCT=0
[[ "$TURNS" =~ ^[0-9]+$ ]] || TURNS=0
[[ "$COST" =~ ^[0-9]+([.][0-9]+)?$ ]] || COST=0

# Resolve working directory from payload, fallback to shell cwd
[ -n "$WORKDIR" ] && [ -d "$WORKDIR" ] || WORKDIR="$PWD"
[ -n "$PROJECT_DIR" ] && [ -d "$PROJECT_DIR" ] || PROJECT_DIR="$WORKDIR"

# ── Context Progress Bar (20 chars) ──────────────────────────
BAR_WIDTH=20
CONTEXT_PCT=${CONTEXT_PCT:-0}
FILLED=$(( CONTEXT_PCT * BAR_WIDTH / 100 ))
[ "$FILLED" -gt "$BAR_WIDTH" ] && FILLED=$BAR_WIDTH
EMPTY=$(( BAR_WIDTH - FILLED ))

if [ "$CONTEXT_PCT" -ge 80 ]; then
  BAR_COLOR="31"   # red
elif [ "$CONTEXT_PCT" -ge 50 ]; then
  BAR_COLOR="33"   # yellow
else
  BAR_COLOR="36"   # cyan
fi

BAR="\033[${BAR_COLOR}m$(printf '▓%.0s' $(seq 1 "$FILLED" 2>/dev/null) 2>/dev/null)$(printf '░%.0s' $(seq 1 "$EMPTY" 2>/dev/null) 2>/dev/null)\033[0m"

# ── Desperation Health Indicator ─────────────────────────────
if [ "$TURNS" -ge 20 ]; then
  HEALTH="\033[31m COOL-DOWN\033[0m"
elif [ "$TURNS" -ge 12 ]; then
  HEALTH="\033[33m ~check\033[0m"
else
  HEALTH=""
fi

# ── Infinity Logo Color (system health composite) ────────────
# Green=all clear, Yellow=warning, Red=critical, Cyan=normal
# Factors: context%, CI status, test result, desperation
LOGO_COLOR="1;36"  # default: bright cyan
CI_STATE=$(cat /tmp/.claude-ci-status 2>/dev/null || echo "")
TEST_STATE=$(cat /tmp/.claude-last-test-result 2>/dev/null || echo "")

# Red: any critical condition
# 65% = quality degrades (Issue Map), not 85% — warn the logo early
if [ "$CONTEXT_PCT" -ge 65 ] || [[ "$CI_STATE" == FAIL* ]] || [[ "$TEST_STATE" == FAIL* ]] || [ "$TURNS" -ge 20 ]; then
  LOGO_COLOR="1;31"  # bright red
# Yellow: any warning condition
elif [ "$CONTEXT_PCT" -ge 40 ] || [[ "$CI_STATE" == WARN* ]] || [ "$TURNS" -ge 12 ]; then
  LOGO_COLOR="1;33"  # bright yellow
# Green: everything is good (tests pass, CI ok)
elif [[ "$TEST_STATE" == PASS* ]] && [[ "$CI_STATE" == OK* ]]; then
  LOGO_COLOR="1;32"  # bright green
fi

# ── Git State ────────────────────────────────────────────────
BRANCH="-"
if git -C "$WORKDIR" rev-parse --git-dir >/dev/null 2>&1; then
  BRANCH=$(git -C "$WORKDIR" branch --show-current 2>/dev/null || echo "-")
fi

# Dirty (unstaged modified) + staged + untracked counts
DIRTY=$(git -C "$WORKDIR" diff --name-only 2>/dev/null | wc -l | tr -d ' ')
STAGED=$(git -C "$WORKDIR" diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
GIT_STATE=""
[ "$STAGED" -gt 0 ] && GIT_STATE="\033[32m+${STAGED}\033[0m"
[ "$DIRTY" -gt 0 ] && GIT_STATE="${GIT_STATE}\033[33m~${DIRTY}\033[0m"

# Unpushed commits
UNPUSHED=0
if git -C "$WORKDIR" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  UNPUSHED=$(git -C "$WORKDIR" log --oneline "@{u}..HEAD" 2>/dev/null | wc -l | tr -d ' ')
fi
[ "$UNPUSHED" -gt 0 ] && GIT_STATE="${GIT_STATE}\033[35m^${UNPUSHED}\033[0m"

# ── Project Detection ────────────────────────────────────────
PROJECT=$(basename "$WORKDIR")

# ── Model Short Name ─────────────────────────────────────────
case "$MODEL" in
  *opus*) MODEL_SHORT="Op" ;;
  *sonnet*) MODEL_SHORT="So" ;;
  *haiku*) MODEL_SHORT="Ha" ;;
  *) MODEL_SHORT=$(echo "$MODEL" | head -c 6) ;;
esac

# ── Cost ─────────────────────────────────────────────────────
COST_FMT=$(printf '$%.2f' "$COST" 2>/dev/null || echo "\$$COST")

# ── Last Test Result (from cached file, written by stop-verify hook) ──
TEST_IND=""
if [ -f /tmp/.claude-last-test-result ]; then
  LAST_TEST=$(cat /tmp/.claude-last-test-result 2>/dev/null)
  case "$LAST_TEST" in
    PASS*) TEST_IND="\033[32mP\033[0m" ;;
    FAIL*) TEST_IND="\033[31mF\033[0m" ;;
  esac
fi

# ── Workflow Phase (from cached file, skills can write to this) ──
PHASE=""
if [ -f /tmp/.claude-workflow-phase ]; then
  PHASE_RAW=$(cat /tmp/.claude-workflow-phase 2>/dev/null)
  [ -n "$PHASE_RAW" ] && PHASE="\033[2m${PHASE_RAW}\033[0m "
fi

# ── CI Build Status (from cached file, written by ci-status-poll.sh) ──
CI_IND=""
if [ -f /tmp/.claude-ci-status ]; then
  CI_RAW=$(cat /tmp/.claude-ci-status 2>/dev/null)
  case "$CI_RAW" in
    OK*) CI_IND="\033[32mCI:ok\033[0m" ;;
    WARN*) CI_IND="\033[33mCI:warn\033[0m" ;;
    FAIL*) CI_IND="\033[31mCI:fail\033[0m" ;;
    BUILDING*) CI_IND="\033[36mCI:...\033[0m" ;;
    NO_AUTH*|NO_PIPELINE*|NO_BUILDS*) CI_IND="" ;;
    *) CI_IND="" ;;
  esac
fi

# ── Time-based health triggers (stateless: uses daily/interval stamp files) ──
HOUR_NOW=$(date +%-H 2>/dev/null || echo 99)
MIN_NOW=$(date +%-M 2>/dev/null || echo 99)

# EOD alert: 16:25–16:45, fires once per day
if [ "$HOUR_NOW" -eq 16 ] && [ "$MIN_NOW" -ge 25 ] && [ "$MIN_NOW" -le 45 ] 2>/dev/null; then
  EOD_MARK="/tmp/.claude-eod-$(date +%Y%m%d)"
  if [ ! -f "$EOD_MARK" ]; then
    touch "$EOD_MARK"
    bash /home/shovalbe/.claude/bin/health-reminder.sh eod &>/dev/null &
    disown 2>/dev/null
  fi
fi

# Water reminder: every 90 min, but only during working hours (8–20)
if [ "$HOUR_NOW" -ge 8 ] && [ "$HOUR_NOW" -lt 20 ] 2>/dev/null; then
  DRINK_STAMP="/tmp/.claude-drink-last"
  DRINK_AGE=99999
  if [ -f "$DRINK_STAMP" ]; then
    DRINK_AGE=$(( $(date +%s) - $(stat -c %Y "$DRINK_STAMP" 2>/dev/null || echo 0) ))
  fi
  if [ "$DRINK_AGE" -gt 5400 ] 2>/dev/null; then
    touch "$DRINK_STAMP"
    bash /home/shovalbe/.claude/bin/health-reminder.sh drink &>/dev/null &
    disown 2>/dev/null
  fi
fi

# ── Health Reminder display (reads /tmp/.claude-health-reminder written by health-reminder.sh) ──
HEALTH_REM=""
if [ -f /tmp/.claude-health-reminder ]; then
  HR_RAW=$(cat /tmp/.claude-health-reminder 2>/dev/null)
  if [ -n "$HR_RAW" ]; then
    # Extract message text (strip "type: " prefix)
    HR_MSG=$(echo "$HR_RAW" | sed 's/^[a-z]*: //' | cut -c1-40)
    case "$HR_RAW" in
      drink*) HEALTH_REM="\033[1;97;44m 💧 ${HR_MSG} \033[0m " ;;   # bold white on blue bg
      eat*)   HEALTH_REM="\033[1;97;43m 🍽  ${HR_MSG} \033[0m " ;;  # bold white on yellow bg
      eod*)   HEALTH_REM="\033[1;97;41m 🏠 GO HOME \033[0m " ;;     # bold white on red bg
    esac
  fi
fi

# ── Layer 7 Session Count (cached, refreshed every 60s) ──
L7_IND=""
L7_CACHE="/tmp/.claude-layer7-count"
L7_DB="/home/shovalbe/.claude/cache/sessions.db"
if [ -f "$L7_DB" ]; then
  # Refresh cache if missing, empty, or older than 60s
  NEEDS_REFRESH=0
  [ ! -s "$L7_CACHE" ] && NEEDS_REFRESH=1
  if [ "$NEEDS_REFRESH" = "0" ] && [ -f "$L7_CACHE" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$L7_CACHE" 2>/dev/null || echo 0) ))
    [ "$AGE" -gt 60 ] && NEEDS_REFRESH=1
  fi
  if [ "$NEEDS_REFRESH" = "1" ]; then
    sqlite3 "$L7_DB" "SELECT COUNT(*) FROM sessions" 2>/dev/null > "$L7_CACHE" || echo 0 > "$L7_CACHE"
  fi
  L7_COUNT=$(cat "$L7_CACHE" 2>/dev/null)
  [ -n "$L7_COUNT" ] && [ "$L7_COUNT" -gt 0 ] 2>/dev/null && L7_IND="\033[36mL7:${L7_COUNT}\033[0m"
fi

# ── Usage Tracker: 5h + Weekly Cost (Phase 4.3) ──────────────────
# Queries sessions.db for cost_usd. Cache refreshed every 5 minutes.
USAGE_IND=""
if [ -f "$L7_DB" ]; then
  USAGE_5H_CACHE="/tmp/.claude-usage-5h"
  USAGE_WK_CACHE="/tmp/.claude-usage-wk"
  NEEDS_USAGE_REFRESH=0
  [ ! -s "$USAGE_5H_CACHE" ] && NEEDS_USAGE_REFRESH=1
  if [ "$NEEDS_USAGE_REFRESH" = "0" ] && [ -f "$USAGE_5H_CACHE" ]; then
    USAGE_AGE=$(( $(date +%s) - $(stat -c %Y "$USAGE_5H_CACHE" 2>/dev/null || echo 0) ))
    [ "$USAGE_AGE" -gt 300 ] && NEEDS_USAGE_REFRESH=1  # refresh every 5 min
  fi
  if [ "$NEEDS_USAGE_REFRESH" = "1" ]; then
    sqlite3 "$L7_DB" \
      "SELECT ROUND(SUM(cost_usd),2) FROM sessions WHERE ts > datetime('now','-5 hours')" \
      2>/dev/null > "$USAGE_5H_CACHE" || echo "0" > "$USAGE_5H_CACHE"
    sqlite3 "$L7_DB" \
      "SELECT ROUND(SUM(cost_usd),2) FROM sessions WHERE ts > datetime('now','-7 days')" \
      2>/dev/null > "$USAGE_WK_CACHE" || echo "0" > "$USAGE_WK_CACHE"
  fi
  COST_5H=$(cat "$USAGE_5H_CACHE" 2>/dev/null | tr -d ' \n')
  COST_WK=$(cat "$USAGE_WK_CACHE" 2>/dev/null | tr -d ' \n')
  [ -z "$COST_5H" ] || [ "$COST_5H" = "" ] || [ "$COST_5H" = "NULL" ] && COST_5H="0"
  [ -z "$COST_WK" ] || [ "$COST_WK" = "" ] || [ "$COST_WK" = "NULL" ] && COST_WK="0"
  if [ "$COST_5H" != "0" ] || [ "$COST_WK" != "0" ]; then
    USAGE_IND="\033[2m5h:\$${COST_5H} wk:\$${COST_WK}\033[0m"
  fi
fi

# ── Codex Metrics (from cached file, written by codex-ci skill) ──
CODEX_IND=""
if [ -f /tmp/.claude-codex-status ]; then
  CODEX_RAW=$(cat /tmp/.claude-codex-status 2>/dev/null)
  [ -n "$CODEX_RAW" ] && CODEX_IND="\033[36mCx:${CODEX_RAW}\033[0m"
fi

# ── Scheduled/Loop Jobs (from cached file, written by loop/schedule skills) ──
JOBS_IND=""
if [ -f /tmp/.claude-active-jobs ]; then
  JOBS_RAW=$(cat /tmp/.claude-active-jobs 2>/dev/null)
  [ -n "$JOBS_RAW" ] && [ "$JOBS_RAW" != "0" ] && JOBS_IND="\033[35mJ:${JOBS_RAW}\033[0m "
fi

# ── Session Recall Indicator (Phase 4.1) ──────────────────────
# ↺:N — number of past sessions injected at startup by session-recall.py
RECALL_IND=""
if [ -f /tmp/.claude-recall-count ]; then
  RC=$(cat /tmp/.claude-recall-count 2>/dev/null)
  [ -n "$RC" ] && [ "$RC" -gt 0 ] 2>/dev/null && RECALL_IND="\033[36m↺:${RC}\033[0m"
fi

# ── Q-Learning Platform Phase Indicator (Phase 4.4) ───────────
# QL:1 = SQL recall active, QL:2 = semantic, QL:3 = reward wired
QL_IND=""
if [ -f /tmp/.claude-ql-phase ]; then
  QL=$(cat /tmp/.claude-ql-phase 2>/dev/null)
  [ -n "$QL" ] && QL_IND="\033[35mQL:${QL}\033[0m"
fi

# ── Context Urgency Warning ──────────────────────────────────
# 65%: quality starts degrading — warn early (Issue Map: context rot at 65%, not 85%)
# 85%: critical — Thanos /clear
CTX_WARN=""
if [ "$CONTEXT_PCT" -ge 85 ]; then
  CTX_WARN="\033[1;31m /clear!\033[0m"
elif [ "$CONTEXT_PCT" -ge 65 ]; then
  CTX_WARN="\033[33m ctx!\033[0m"
fi

# ── Time Since Last Commit ───────────────────────────────────
LAST_COMMIT=$(git -C "$WORKDIR" log -1 --format='%cr' 2>/dev/null | sed 's/ ago//' | sed 's/ /_/g' || echo "")
[ -n "$LAST_COMMIT" ] && COMMIT_AGE="\033[2m${LAST_COMMIT}\033[0m " || COMMIT_AGE=""

# ── Output (single line) ────────────────────────────────────
# ── Message Counter (file-based, since JSON turns resets on compact) ──
MSG_COUNT=""
if [ -f /tmp/.claude-msg-count ]; then
  MC=$(cat /tmp/.claude-msg-count 2>/dev/null)
  [ -n "$MC" ] && [ "$MC" -gt 0 ] 2>/dev/null && MSG_COUNT="M:${MC}"
fi

# ── Output ───────────────────────────────────────────────────
# Layout (groups separated by  ·  or double space):
#
#   [HEALTH ALERT]  ∞  [ctx░░░░] 12%  So $0.45  ⎇ master +2~3  project 2d  T:15 M:12  P CI:ok L7:388
#
# Group legend:
#   ∞            = logo (color = system health: cyan=ok, yellow=warn, red=crit)
#   [▓░░]  12%   = context window used (cyan<50%, yellow≥50%, red≥80%); /clear! at 85%
#   So $0.45     = model (So=Sonnet, Op=Opus, Ha=Haiku) + session cost USD
#   ⎇ master     = git branch
#   +2~3^1       = git: +staged / ~dirty / ^unpushed commits
#   project 2d   = project dir + time since last commit
#   T:15         = turns this session (yellow≥12, red≥20 = cool-down)
#   M:12         = total messages (persists across compacts)
#   P / F        = last test run: P=pass F=fail
#   CI:ok/fail   = last CI pipeline result
#   L7:388       = sessions embedded in Layer 7 vector DB (lifetime)
#   COOL-DOWN    = desperation signal (≥20 turns) — take a break

# Build session counters group
COUNTERS=""
[ -n "$MSG_COUNT" ] && COUNTERS="${MSG_COUNT}"
[ "$TURNS" -gt 0 ] 2>/dev/null && COUNTERS="${COUNTERS:+${COUNTERS} }T:${TURNS}"

# Build indicators group (test, CI, L7, recall, QL phase, usage, codex, jobs)
INDS=""
[ -n "$TEST_IND"   ] && INDS="${TEST_IND}"
[ -n "$CI_IND"     ] && INDS="${INDS:+${INDS} }${CI_IND}"
[ -n "$L7_IND"     ] && INDS="${INDS:+${INDS} }${L7_IND}"
[ -n "$RECALL_IND" ] && INDS="${INDS:+${INDS} }${RECALL_IND}"
[ -n "$QL_IND"     ] && INDS="${INDS:+${INDS} }${QL_IND}"
[ -n "$USAGE_IND"  ] && INDS="${INDS:+${INDS} }${USAGE_IND}"
[ -n "$CODEX_IND"  ] && INDS="${INDS:+${INDS} }${CODEX_IND}"
[ -n "$JOBS_IND"   ] && INDS="${INDS:+${INDS} }${JOBS_IND}"

# ── Ink Daemon: two-row statusline (falls back to single row below if unreachable) ──
_INK_SOCK="/tmp/.claude-ink.sock"
if [ -S "$_INK_SOCK" ]; then
  _TEST_R=""; case "${LAST_TEST:-}" in PASS*) _TEST_R="P";; FAIL*) _TEST_R="F";; esac
  _CI_R="";   case "${CI_RAW:-}"   in OK*)   _CI_R="ok";; FAIL*) _CI_R="fail";; WARN*) _CI_R="warn";; BUILDING*) _CI_R="building";; esac
  _L7=$(cat /tmp/.claude-layer7-count 2>/dev/null | tr -d ' \n' || echo 0); [[ "$_L7" =~ ^[0-9]+$ ]] || _L7=0
  _RC=$(cat /tmp/.claude-recall-count 2>/dev/null | tr -d ' \n' || echo 0); [[ "$_RC" =~ ^[0-9]+$ ]] || _RC=0
  _MC=$(cat /tmp/.claude-msg-count   2>/dev/null | tr -d ' \n' || echo 0); [[ "$_MC" =~ ^[0-9]+$ ]] || _MC=0
  _PH=$(cat /tmp/.claude-workflow-phase 2>/dev/null | tr -d '\n' || echo "")
  _HR=$(cat /tmp/.claude-health-reminder 2>/dev/null | sed 's/^[a-z]*: //' | cut -c1-35 | tr -d '\n"\\' || echo "")
  _STATE=$(printf '{"event":"state_update","data":{"context_pct":%d,"model":"%s","cost_usd":%s,"turns":%d,"branch":"%s","staged":%d,"dirty":%d,"project":"%s","test_result":"%s","ci_status":"%s","l7_count":%d,"recall_count":%d,"messages":%d,"phase":"%s","health":"%s"}}' \
    "${CONTEXT_PCT:-0}" "${MODEL_SHORT:-So}" "${COST:-0}" "${TURNS:-0}" \
    "${BRANCH:--}" "${STAGED:-0}" "${DIRTY:-0}" "${PROJECT:-}" \
    "$_TEST_R" "$_CI_R" "$_L7" "$_RC" "$_MC" "$_PH" "$_HR")
  _RAW=$(printf '%s\n' "$_STATE" | socat -T1 - UNIX-CONNECT:"$_INK_SOCK" 2>/dev/null || echo "")
  if [ -n "$_RAW" ]; then
    _ROWS=$(printf '%s' "$_RAW" | python3 -c "import sys,json; rows=json.load(sys.stdin).get('rows',[]); [print(r) for r in rows]" 2>/dev/null || echo "")
    if [ -n "$_ROWS" ]; then printf '%s\n' "$_ROWS"; exit 0; fi
  fi
fi

# ── Fallback: original single-row bash rendering ──────────────
echo -e "${HEALTH_REM}ISDD \033[${LOGO_COLOR}m∞\033[0m  ${BAR} ${CONTEXT_PCT}%${CTX_WARN}  \033[1m${MODEL_SHORT}\033[0m ${COST_FMT}  \033[2m⎇\033[0m \033[1m${BRANCH}\033[0m${GIT_STATE:+ ${GIT_STATE}}  \033[2m${PROJECT}\033[0m${COMMIT_AGE:+ ${COMMIT_AGE}}  ${COUNTERS}  ${INDS}${HEALTH}"
