Completed the scheduled audit and wrote the report:

[CLAUDEMD_DRIFT_2026-06-16.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-16.md)

Summary:
- `qc-telephony-api`: 61% drift score, below threshold.
- `video-understanding`: 80% drift score, no ADO item required.
- `campaign-analysis`: 56% drift score, below threshold.
- `cs-agent` and `~/CLAUDE.md`: no `CLAUDE.md` found, recorded in scope.
- `seekapa-training-platform`: explicitly skipped.

ADO work-item creation was attempted for the below-70 projects, but blocked because `/home/shovalbe/.claude/bin/work-item.sh` only exposes `comment`, not `create`. The report includes that BLOCKED evidence.

Verification evidence is included in the report, including the `rtk` commands, `test -e` path checks, manifest checks, and `git branch -r` branch evidence.

