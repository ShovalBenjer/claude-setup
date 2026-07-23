Wrote the sweep report here:

[PLATFORM_HYGIENE_2026-06-28.md](/home/shovalbe/.claude/docs/PLATFORM_HYGIENE_2026-06-28.md)

Key outcomes:
- No destructive changes.
- No new Hive beads created because existing open beads already cover the required P1/P2 platform issues: `#22` RTK compatibility and `#23` Obscura CDP smoke-testability.
- Main findings: Claude Bash still routes through `coverage-enforcer.sh` rather than general RTK enforcement, Obscura CDP is documented but currently stopped, `cs-agent` rig parity files are missing, and PST helper scripts are missing while `pst_messages` has `663` rows.
- Verification included required section-header check, file stat, git status, and a stricter secret-pattern scan with no matches.

