Completed the scheduled hot-zone run.

Report written to [HOT_ZONES_2026-06-14.md](/home/shovalbe/.claude/docs/HOT_ZONES_2026-06-14.md).

Result:
- Scanned 8 active repos.
- Found 1 qualifying hot zone: `qc-telephony-api/src/api/activities/durable_activities.py`.
- No matching test file under `tests/`; ratio is infinite.
- ADO Task creation was blocked:
  - `~/.claude/bin/work-item.sh` only supports PR comments, not `create`.
  - Direct `az boards work-item create` failed because `dev.azure.com` DNS resolution is unavailable in the sandbox.
- Created local Hive fallback bead `88` for `qc-telephony-api`.

I also checked the prompt’s cited cs-agent SHAs. The active repo does not match the prompt claim exactly: three cited `fix(webhook)` commits did touch `tests/test_chatwoot_webhook.py`, one cited SHA is a merge subject rather than strict `fix(` prefix, and the webhook source path is outside the strict `src/` / `app/` filter. That discrepancy is recorded in the report.

Verification evidence is included in the report, including the failed ADO attempts and the Hive bead creation.

