Completed the scheduled C2 engineering review sweep.

Report written: [ENGINEERING_REVIEW_2026-05-21.md](/home/shovalbe/.claude/docs/ENGINEERING_REVIEW_2026-05-21.md)

Created Hive beads:
- `5` `cs-agent` P1: Reconcile Foundry prompt drift and project git root
- `6` `qc-telephony-api` P2: Repair QAResponse doc drift and Ruff gate debt
- `7` `campaign-analysis` P1: Review dirty deletion of Foundry prompt and OpenAPI artifacts
- `8` `video-understanding` P2: Resolve branch and CI/deploy path ambiguity

Key blockers recorded in the report:
- Azure DevOps CLI returned `auth-needs-refresh`.
- `git ls-remote` to `dev.azure.com` failed DNS resolution.
- Live Foundry prompt comparison could not run due auth/network limits.

Verification included local git baselines, manifest/spec scans, Ruff/typecheck/lint checks, bead creation, `bead-list --json`, and report section validation.

