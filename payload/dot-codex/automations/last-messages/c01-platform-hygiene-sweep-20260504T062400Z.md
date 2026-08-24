Wrote the requested report:

[PLATFORM_HYGIENE_2026-05-04.md](/home/shovalbe/.claude/docs/PLATFORM_HYGIENE_2026-05-04.md)

Verification: `wc -l` reports 226 lines, and all required sections are present: `MEMORY_PROPOSALS`, `HOOK_HEALTH`, `SKILL_USAGE`, `PST_PIPELINE_HEALTH`, `ACTIONABLE_NEXT_STEPS`.

Key findings:
- PST source exists and `readpst` is installed.
- PST pipeline is blocked: `~/.claude/bin/pst-watch.sh`, `pst-to-memory.py`, `pst-to-db.py`, `pst-to-knowledge.py`, and `~/.claude/cache/sessions.db` are missing.
- `pst-watch.service` exists but points at the missing watcher script.
- User systemd status was blocked by `Failed to connect to bus: Operation not permitted`.
- Hook syntax passed, but hook budget comments are missing.
- RTK Claude hook marker and `rtk-rewrite.sh` are missing from `~/.claude/hooks`.
- No skill archive candidates were proposed.

