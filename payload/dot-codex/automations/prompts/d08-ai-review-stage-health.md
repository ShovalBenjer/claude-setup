# D8. AI PR Review Stage Health

Schedule: Weekdays 19:00
Repo root: `/home/shovalbe/projects/cs-agent`
Mode: read + summary + ADO Bug if degraded

Query ADO pipeline runs for the last 14 days of the **AIPullRequestReview** stage in cs-agent:

```bash
az pipelines runs list \
  --branch refs/heads/master \
  --pipeline-ids <cs-agent-pipeline-id> \
  --query-order QueueTimeDesc \
  --top 100 \
  -o json
```

For each run, capture:
- status (`succeeded` / `failed` / `canceled` / `timeout`)
- failure category — categorize the log into:
  - `auth` — 401, expired token, KV permission
  - `quoting` — bash quoting, curl arg parse
  - `trigger` — wrong branch pattern, race condition
  - `endpoint` — Foundry path mismatch, Responses API drift
  - `payload` — request body schema, missing field
  - `other`

Compute:
- success rate %
- top 3 failure categories with example PR IDs
- time-to-fix per category (commit time of fix - failure time)

Output `~/.claude/docs/AI_REVIEW_HEALTH_<DATE>.md`.

If success rate `<90%` over 14 days: file an ADO Bug:

```bash
~/.claude/bin/work-item.sh create --type Bug \
  --title "AI PR Review stage <90% healthy" \
  --tags "ci,ai-review"
```

Body: failure category breakdown, top offending PRs, suggested next actions (parameterize the failing curl, add a trigger smoke test, etc.).

Evidence cited: SHAs `e2f2225e` (401), `7000080e` (curl quoting), `9ea61fe5` (KV route), `f4668e76` (trigger), `402e182d` (widen trigger) — five distinct fixes in 60 commits. Stage is patched reactively. A health metric forces a pause to fix root cause.
