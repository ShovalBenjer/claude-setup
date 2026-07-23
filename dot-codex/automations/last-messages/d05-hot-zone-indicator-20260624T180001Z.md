Created the scheduled audit report:

[HOT_ZONES_2026-06-24.md](/home/shovalbe/.claude/docs/HOT_ZONES_2026-06-24.md)

Result: scanned 11 active repos; no files met the strict hot-zone threshold of `>=3` `fix(...)` commits in the last 30 days under `src/` or `app/`.

ADO task filing: blocked and documented in the report. `/home/shovalbe/.claude/bin/work-item.sh` only supports PR comments, not `create --type Task`.

Verification included in the report:
- repo discovery and scan evidence
- `work-item.sh` source/usage evidence
- direct check of the cited cs-agent SHAs, including why they were excluded from this June 24, 2026 run: April commit dates, path outside `src/`/`app/`, and test file presence on three cited commits.