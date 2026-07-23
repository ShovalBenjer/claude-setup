#!/usr/bin/env bash
# QC Telephony monitoring health check (read-only).
#
# Answers, from OUR side only (needs nothing from the caller/Vlad):
#   1. Is App Insights telemetry alive + persisting? (AppTraces flowing)
#   2. Which functions executed in the window, and how often?
#   3. Did call-analyzer (Vlad) transcription traffic actually land?
#   4. Any errors/exceptions?
#   5. AppRequests-table status (known gap: host request telemetry not emitting).
#
# Emits a compact markdown block on stdout. On auth/network failure it prints a
# clear BLOCKED line and exits 0, so a daily report always carries a status line
# instead of silently dropping the section.
#
# Usage: qc-monitoring-check.sh [hours]   (default 24)
set -uo pipefail

WS="${QC_LA_WORKSPACE:-ef6e6783-8c3c-486f-a10a-b9bbee73032b}"   # workspace-groupK0Th customerId
ROLE="${QC_APP_ROLE:-func-qc-telephony-prod}"
HOURS="${1:-24}"
NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

q() {
  # Run a KQL query, return TSV rows (no headers), empty on any failure.
  az monitor log-analytics query -w "$WS" --analytics-query "$1" -o json 2>/dev/null \
    | jq -r "${2:-.[]? | @tsv}" 2>/dev/null
}

echo "## QC Telephony Monitoring — \`${ROLE}\` — ${NOW} (last ${HOURS}h)"
echo

# --- 0. auth/reachability probe: can we query the workspace at all? ---
PROBE="$(az monitor log-analytics query -w "$WS" --analytics-query "print ok=42" -o json 2>&1)"
if ! echo "$PROBE" | grep -q '42'; then
  echo "- **STATUS: BLOCKED** — cannot query Log Analytics (az auth/network). Re-run after \`az login\`."
  echo "  - detail: $(echo "$PROBE" | head -1 | cut -c1-120)"
  exit 0
fi

# --- 1. telemetry alive? (AppTraces volume + last seen) ---
TN="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | count" '.[0].Count|tostring')"
TLAST="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | summarize m=max(TimeGenerated)" '.[0].m|tostring')"
TN="${TN:-0}"
if [ "$TN" -gt 0 ] 2>/dev/null; then
  echo "- **Telemetry: ALIVE** — AppTraces ${TN} rows in ${HOURS}h, last ${TLAST}"
else
  echo "- **Telemetry: NO TRACES in ${HOURS}h** — pipeline idle or broken; verify with a live probe (curl /api/health then re-check this)"
fi

# --- 2. function executions by name ---
echo "- Functions executed (${HOURS}h):"
q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where Message startswith \"Executed 'Functions.\" | parse Message with \"Executed 'Functions.\" fn \"'\" * | summarize n=count() by fn | order by n desc" \
  '.[]? | "    - \(.fn): \(.n)"'
FNS="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where Message startswith \"Executed 'Functions.\" | count" '.[0].Count|tostring')"
[ -z "$(echo "$FNS")" ] || [ "${FNS:-0}" = "0" ] && echo "    - (none)"

# --- 3. transcription traffic (= call-analyzer/Vlad, since campaign-analysis uses his bulk API not our sync route) ---
# Count COMPLETED transcribe_v2/batch executions and the upstream Scribe calls they make.
TXEXEC="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where Message startswith \"Executed 'Functions.transcribe\" | count" '.[0].Count|tostring')"
SCRIBE="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where Message has '/v1/speech-to-text' | count" '.[0].Count|tostring')"
TXLAST="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where Message startswith \"Executed 'Functions.transcribe\" | summarize m=max(TimeGenerated)" '.[0].m|tostring')"
TXEXEC="${TXEXEC:-0}"; SCRIBE="${SCRIBE:-0}"
if [ "$TXEXEC" -gt 0 ] 2>/dev/null; then
  echo "- **Transcription traffic: PRESENT** — ${TXEXEC} transcribe executions (${SCRIBE} upstream Scribe calls), last ${TXLAST}"
  echo "    - NOTE: confirm these are call-analyzer and not a manual load test (tests/load/*) before reporting Vlad as live"
else
  echo "- **Transcription traffic: NONE** — 0 transcribe executions in ${HOURS}h. call-analyzer not sending; our endpoint logs every call the moment it lands"
fi

# --- 4. errors / exceptions ---
EXC="$(q "AppExceptions | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | count" '.[0].Count|tostring')"
ERR="$(q "AppTraces | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | where SeverityLevel >= 3 | count" '.[0].Count|tostring')"
echo "- Errors (${HOURS}h): AppExceptions=${EXC:-0}, error-level traces=${ERR:-0}"

# --- 5. AppRequests-table status (known gap) ---
REQ="$(q "AppRequests | where TimeGenerated > ago(${HOURS}h) | where AppRoleName == '${ROLE}' | count" '.[0].Count|tostring')"
if [ "${REQ:-0}" -gt 0 ] 2>/dev/null; then
  echo "- AppRequests table: ${REQ} rows (host request telemetry healthy)"
else
  echo "- AppRequests table: 0 (KNOWN GAP — host request telemetry not emitting; monitor via AppTraces above, not the portal Requests blade)"
fi
