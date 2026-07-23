Wrote the drift report here: [.claude/docs/CLAUDEMD_DRIFT_2026-05-26.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-05-26.md).

Scores:
- `cs-agent`: 74%
- `qc-telephony-api`: 74%
- `video-understanding`: 88%
- `campaign-analysis`: 73%
- `~/CLAUDE.md`: missing, recorded as unavailable
- `seekapa-training-platform`: explicitly skipped

No active rig scored below 70%, so no ADO work item was required. I also recorded that `~/.claude/bin/work-item.sh` is missing, which would block future required routing if a project falls below threshold.

Verification: `rtk proxy test -s /home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-05-26.md` passed; report is 367 lines.

