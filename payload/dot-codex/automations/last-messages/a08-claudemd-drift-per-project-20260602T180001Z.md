Wrote the audit report to [CLAUDEMD_DRIFT_2026-06-02.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-02.md).

Summary:
- `cs-agent`: `10/19 = 53%`, ADO routing blocked
- `qc-telephony-api`: `19/28 = 68%`, ADO routing blocked
- `video-understanding`: `3/4 = 75%`, no work item required
- `campaign-analysis`: `21/36 = 58%`, ADO routing blocked
- `~/CLAUDE.md`: missing

Blocked item: `/home/shovalbe/.claude/bin/work-item.sh` does not exist, so the requested ADO work item creation could not run for projects below 70%.

Verification:
- `rtk proxy python3 /tmp/claudemd_drift_audit.py` exited `0`
- `test -s /home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-02.md && wc -l ...` returned `510`

