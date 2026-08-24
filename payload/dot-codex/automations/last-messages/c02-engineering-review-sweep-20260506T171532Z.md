Completed the scheduled sweep.

Report written: [.claude/docs/ENGINEERING_REVIEW_2026-05-06.md](/home/shovalbe/.claude/docs/ENGINEERING_REVIEW_2026-05-06.md)

Verification:
- Generated report for timestamp `20260506T171532Z`
- Scanned `17` git repos
- Scanned `44` spec docs
- Attempted `3` configured lint/static commands
- Found `12` pipeline/YAML risk hits
- Azure DevOps remote coverage is blocked as `auth-needs-refresh`; `az account show` succeeded, but `az repos list` and active PR listing both returned rc `1`

I also updated the existing sweep helper at [.claude/c2_engineering_review_sweep_tmp.py](/home/shovalbe/.claude/c2_engineering_review_sweep_tmp.py) so it uses fresh ADO probes and accepts the scheduler timestamp instead of reusing stale report metadata.

