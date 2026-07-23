Completed the scheduled A8 audit.

Report written to [CLAUDEMD_DRIFT_2026-05-26.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-05-26.md).

Scores:
- `cs-agent`: 43%
- `qc-telephony-api`: 50%
- `video-understanding`: 75%
- `campaign-analysis`: 52%
- `home`: 0%, blocked because `/home/shovalbe/CLAUDE.md` is missing

ADO routing was required for the sub-70 project docs, but no work items were created because `/home/shovalbe/.claude/bin/work-item.sh` does not exist (`test -e` and `test -x` both returned `1`). I also verified the generated report is nonempty and ran a basic secret-pattern scan with no matches.

The audit helper used for generation is at [claudemd_drift_audit.py](/home/shovalbe/tmp/claudemd_drift_audit.py).

