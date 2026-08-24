Completed. Report written to [PLATFORM_HYGIENE_2026-04-27.md](/home/shovalbe/.claude/docs/PLATFORM_HYGIENE_2026-04-27.md:1).

Verification:
- `wc -l` -> `285`
- required sections found: `MEMORY_PROPOSALS`, `HOOK_HEALTH`, `SKILL_USAGE`, `PST_PIPELINE_HEALTH`, `ACTIONABLE_NEXT_STEPS`
- `sha256sum` -> `0a625e0ca138c24f974760fb59a207b50a62bbad10b033f7abf42224252932fc`

Key findings captured in the report: one hook syntax failure, all hooks missing budget comments, several strict-mode/tmp/timeout/auth-handling gaps, `pst-watch.service` blocked by user systemd bus access, PST DB has `emails=328`, and 33 skills are archive candidates by zero observed invocation in 90 days. No destructive changes were made.

