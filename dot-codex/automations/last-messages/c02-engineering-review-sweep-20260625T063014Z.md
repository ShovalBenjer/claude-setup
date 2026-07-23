Completed the scheduled sweep and wrote the report:

[ENGINEERING_REVIEW_2026-06-25.md](/home/shovalbe/.claude/docs/ENGINEERING_REVIEW_2026-06-25.md)

Created Hive beads:
- `#127` `cs-agent` P1: restore behavioral eval / prompt-sync gate
- `#128` `qc-telephony-api` P2: fix Hive manifest path drift

Key blockers recorded in the report:
- Azure DevOps auth needs refresh.
- DNS/network to `dev.azure.com` failed for `git ls-remote`.
- Additional `bead-create` attempts failed with silent exit code `11`.

Verification:
- Report exists: `176` lines.
- Bead `#128` verified via `bead-list`; bead `#127` was created and visible in `cs-agent` bead list.
- Static checks were run for all four rigs and failed; details are in the report.

