Completed the sweep and wrote the report here:

[SECURITY_TESTING_PYRAMID_2026-07-05.md](/home/shovalbe/.claude/docs/SECURITY_TESTING_PYRAMID_2026-07-05.md)

Created 4 local Hive beads:

- `#156` cs-agent: add AGENTS/Hive manifest to active rig path
- `#157` seekapa-training-platform: fix frontend Playwright E2E matrix
- `#158` campaign-analysis: tie high fix churn to regression gates
- `#159` ORM-AGENT: gate root deploy on social-media-agent tests/QA suite

Key finding: training and campaign are the churn outliers (`68.3%` and `47.5%` fix-like commits over last 120). ORM does have tests now, but the root production pipeline does not run them before deploy. No external auth-dependent cloud probes were run; this was local read/propose/beads only.

