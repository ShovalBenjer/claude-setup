Completed the scheduled engineering review sweep.

Report written: [ENGINEERING_REVIEW_2026-07-06.md](/home/shovalbe/.claude/docs/ENGINEERING_REVIEW_2026-07-06.md)

Created Hive beads:
- `160` `cs-agent` P1: eval gate disabled without hard replacement
- `161` `qc-telephony-api` P1: QC monitoring not ALIVE in last 24h
- `162` `video-understanding` P1: Cloudflare origin-lock stage fails open
- `163` `campaign-analysis` P2: full-root lint polluted by scratch/generated outputs

Key blockers recorded in the report: ADO remote coverage was blocked by DNS resolution for `dev.azure.com`; QC pytest verification got stuck with no output, while no matching pytest/uv process was visible afterward. QC monitoring verdict is FAIL per the prompt rule.

