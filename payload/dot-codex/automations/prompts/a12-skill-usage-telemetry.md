# A12. Skill Usage Telemetry -> Trim/Tier Suggestion

Schedule: Last Sunday of the month, 4:00 PM
Repo root: `/home/shovalbe/.claude/`
Mode: read + propose

Scan the last 30 days of session transcripts and `history.jsonl` for Skill tool invocations. For each skill in `~/.claude/skills/`:

- `count_invocations`.
- `last_used_date`.
- `avg_session_yield`, rough estimate: sessions where the skill ran and the user later expressed satisfaction or shipped code.

Classify into:

- `HOT`: at least 10 invocations.
- `WARM`: 1 to 9 invocations.
- `COLD`: 0 invocations in 30 days.
- `DEAD`: 0 invocations in 90 days.

Output `~/.claude/docs/SKILL_USAGE_<DATE>.md`:

- Per-skill row: name, count, last_used, classification.
- `DEAD` skills: suggest archive by moving to `~/.claude/skills/.archive/`.
- `COLD` skills: suggest one-line `still keep?` review.

Do not move or delete anything.
