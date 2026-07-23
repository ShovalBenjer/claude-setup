Completed the scheduled C1 platform hygiene sweep.

Report written to [PLATFORM_HYGIENE_2026-06-14.md](/home/shovalbe/.claude/docs/PLATFORM_HYGIENE_2026-06-14.md).

Verification:
- Required sections present: `MEMORY_PROPOSALS`, `HOOK_HEALTH`, `SKILL_USAGE`, `PST_PIPELINE_HEALTH`, `HIVE_PARITY`, `HIVE_BEADS_CREATED`, `ACTIONABLE_NEXT_STEPS`
- Report length: 223 lines
- Secret/body scan: no obvious credential or email-body patterns found
- No new Hive beads created because existing open beads already cover RTK parity `#22` and Obscura CDP `#23`

Main findings: PST pipeline is degraded due to missing Claude PST scripts/schema mismatch, `cs-agent` Hive manifest parity is broken at the configured rig path, Claude Bash RTK enforcement is still not actively wired, and Obscura is documented but currently stopped.

