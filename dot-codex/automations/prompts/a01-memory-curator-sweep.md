# A1. Memory Curator Sweep

Schedule: Sundays 8:00 PM
Repo root: `/home/shovalbe/`
Mode: read + propose; no auto-write

Scan the last 7 days of Claude Code session transcripts under
`~/.claude/file-history/`, `~/.claude/cache/`, and `~/.claude/projects/-home-shovalbe/`.

For each session, identify:

1. Corrections the user made (rules that should become feedback memory).
2. Approaches the user explicitly approved (positive feedback worth capturing).
3. New project facts (team members, schedules, infra, decisions) not yet in memory.
4. Stale memories: facts that contradict the latest sessions.

Output a single file at `~/.claude/docs/MEMORY_PROPOSALS_<DATE>.md` with:

- Section `ADD`: new memories with frontmatter ready to drop into `~/.claude/projects/-home-shovalbe/memory/`.
- Section `UPDATE`: existing memory files that need editing; cite path and diff.
- Section `REMOVE`: memories that look stale or wrong.
- Section `NOOP`: confirmed-still-true, one line each.

Never auto-write. Never modify `MEMORY.md` or files in `memory/`. Only propose.
