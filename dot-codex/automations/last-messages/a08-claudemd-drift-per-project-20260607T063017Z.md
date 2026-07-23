Completed the scheduled audit.

Report written to [CLAUDEMD_DRIFT_2026-06-07.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-07.md).

Key outcomes:
- Audited active rigs only: `cs-agent`, `qc-telephony-api`, `video-understanding`, `campaign-analysis`.
- Explicitly skipped `seekapa-training-platform`.
- `/home/shovalbe/CLAUDE.md` is missing, recorded as blocked.
- Below-threshold drift found:
  - `cs-agent`: `58%`
  - `campaign-analysis`: `67%`
- ADO work-item creation was blocked because `/home/shovalbe/.claude/bin/work-item.sh` is missing/not executable (`work_item_exit:1`).

Verification: report exists and is non-empty: `232` lines.