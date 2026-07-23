#!/usr/bin/env bash
set -euo pipefail

JOB_ID="${1:-}"
RUNNER="${GASTOWN_CODEX_RUNNER:-$HOME/.codex/automations/run-codex-automation.sh}"
LOCK_ROOT="${GASTOWN_LOCK_ROOT:-$HOME/.codex/automations/locks}"
STALE_LOCK_MINUTES="${GASTOWN_STALE_LOCK_MINUTES:-360}"
MAX_LOAD_PER_CPU="${GASTOWN_MAX_LOAD_PER_CPU:-1.35}"

if [[ -z "$JOB_ID" || "$JOB_ID" == "--help" || "$JOB_ID" == "-h" ]]; then
  echo "Usage: $0 <automation-id>"
  exit 2
fi

timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

host_load_too_high() {
  local load cpus limit
  load="$(awk '{print $1}' /proc/loadavg)"
  cpus="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
  limit="$(awk -v cpus="$cpus" -v per_cpu="$MAX_LOAD_PER_CPU" 'BEGIN { printf "%.2f", cpus * per_cpu }')"
  awk -v load_avg="$load" -v limit="$limit" 'BEGIN { exit !(load_avg > limit) }'
}

clear_stale_locks() {
  [[ -d "$LOCK_ROOT" ]] || return 0

  while IFS= read -r lock_dir; do
    if rmdir "$lock_dir" 2>/dev/null; then
      echo "[$(timestamp)] gastown: cleared stale empty lock $lock_dir"
    else
      echo "[$(timestamp)] gastown: stale lock not empty or not removable: $lock_dir"
    fi
  done < <(find "$LOCK_ROOT" -maxdepth 1 -mindepth 1 -type d -name '*.lock' -mmin "+$STALE_LOCK_MINUTES" -print 2>/dev/null || true)
}

skip_known_blocked_job() {
  case "$JOB_ID" in
    a05-pst-email-action-mining)
      if systemctl --user is-active --quiet pst-watch.service 2>/dev/null; then
        return 1
      fi
      echo "[$(timestamp)] gastown: skipping $JOB_ID because pst-watch.service is not active"
      return 0
      ;;
  esac

  return 1
}

set_job_effort() {
  case "$JOB_ID" in
    c02-engineering-review-sweep|c03-prompt-drift-sweep|c04-security-testing-pyramid-sweep|a09-forge-loop-compliance-score|d05-hot-zone-indicator)
      export CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-high}"
      ;;
    *)
      export CODEX_REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
      ;;
  esac
}

if [[ ! -x "$RUNNER" ]]; then
  echo "[$(timestamp)] gastown: runner not executable: $RUNNER" >&2
  exit 127
fi

clear_stale_locks

if host_load_too_high; then
  echo "[$(timestamp)] gastown: skipping $JOB_ID because host load is above limit"
  exit 0
fi

if skip_known_blocked_job; then
  exit 0
fi

set_job_effort

echo "[$(timestamp)] gastown: starting $JOB_ID with CODEX_REASONING_EFFORT=$CODEX_REASONING_EFFORT"

if [[ "${GASTOWN_DRY_RUN:-0}" == "1" ]]; then
  echo "[$(timestamp)] gastown: dry run, would exec $RUNNER $JOB_ID"
  exit 0
fi

exec "$RUNNER" "$JOB_ID"
