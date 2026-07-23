# A9. Forge Loop Compliance Score

Schedule: Saturdays 9:00 AM
Repo root: `/home/shovalbe/.claude/cache/sessions/` or wherever transcripts persist
Mode: read + summary file

Audit Claude Code sessions from the last 7 days. For each session where the user requested an implementation, filter prompts containing `implement`, `fix`, `add feature`, `build`, or `refactor`.

Score on 8 forge-loop axes, 0 or 1 each:

1. `SPEC`: was a doc written under `docs/superpowers/specs/`?
2. `PREMORTEM`: were 5 failure modes listed in the spec?
3. `RED`: was a failing test pasted before code?
4. `GREEN`: was a passing test pasted after code?
5. `REFACTOR`: was `/simplify` run on changed files?
6. `COVERAGE`: were acceptance criteria explicitly mapped to tests?
7. `REFLECT`: was `/heidegger-reflect` run?
8. `CI BIND`: did the user push and confirm CI green?

Output `~/.claude/docs/FORGE_COMPLIANCE_<DATE>.md`:

- Per-session table: session_id, branch, score from 0 to 8, missing_steps.
- Trend: 4-week rolling average.
- Top 3 most-missed steps.

If the 4-week average drops below 5 out of 8, add a `SessionStart banner nudge` section for next week.
