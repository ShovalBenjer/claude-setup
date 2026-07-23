Completed the scheduled drift audit and wrote the report to [.claude/docs/CLAUDEMD_DRIFT_2026-06-23.md](/home/shovalbe/.claude/docs/CLAUDEMD_DRIFT_2026-06-23.md).

Key outcomes:
- `campaign-analysis` scored `55.6%`, below threshold.
- Attempted the requested ADO work-item command, but `~/.claude/bin/work-item.sh` rejected `create` and only exposes `comment`; report records this as BLOCKED with exit `1`.
- `video-understanding` scored `75.0%`.
- `home`, `cs-agent`, and the configured `qc-telephony-api` rig path are blocked/missing or stale.
- Only the report file was added; no project docs, secrets, or source files were changed.

Verification included `rtk` checks for Hive rigs, `CLAUDE.md` discovery, `test -e` path checks, manifest reads, remote branch checks, and the failed work-item command.

