Done. Wrote the audit report here:

[CLAUDEMD_DRIFT_20260519T171708Z.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_20260519T171708Z.md)

Summary: all discovered project `CLAUDE.md` files scored below 70%, and `/home/shovalbe/CLAUDE.md` is missing. ADO work item filing was blocked because `/home/shovalbe/.claude/bin/work-item.sh` is missing or not executable, so the report includes the exact create command for each below-threshold project.

Verification:
- `rtk proxy test -s /home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_20260519T171708Z.md` exited `0`
- `rtk wc -l /home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_20260519T171708Z.md` returned `618`
- Git shows the report as a new untracked file.

