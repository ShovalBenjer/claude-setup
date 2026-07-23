Wrote the hygiene report here:

[PLATFORM_HYGIENE_2026-05-11.md](/home/shovalbe/.claude/docs/PLATFORM_HYGIENE_2026-05-11.md)

Key results:
- Memory: proposals only, no memory files changed.
- Hooks: all current hook scripts pass `bash -n`; Claude-side RTK marker/rewrite hook are missing; meme hooks need `set -euo pipefail`, budget comments, and `/tmp` cleanup.
- Skills: all current `~/.claude/skills/` directories classified `HOT`; no archive candidates.
- PST: PST file exists and `readpst` is installed; expected `~/.claude/bin/pst-*` scripts are missing; `sessions.db` has `pst_messages` rows but no `emails` table; user systemd status was blocked by `Failed to connect to bus: No medium found`.

Verification included in the report with command output. No deletions, no secret printing, no email-body inspection.

