Created the audit report at [CLAUDEMD_DRIFT_2026-06-21.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-21.md).

Summary:
- `home`: blocked, `/home/shovalbe/CLAUDE.md` missing.
- `cs-agent`: blocked, rig root `/home/shovalbe/projects/cs-agent` missing.
- `qc-telephony-api`: `76.7%`, no ADO task required.
- `video-understanding`: `75.0%`, no ADO task required.
- `campaign-analysis`: `64.3%`, ADO task required.

I attempted the required ADO work-item command for `campaign-analysis`, but it failed because `/home/shovalbe/.claude/bin/work-item.sh` only supports `comment <pr-id> <body-file> [--dry-run]`, not `create`. That blocker is recorded in the report. I also ran a sensitive-pattern scan on the report; it returned no matches.

