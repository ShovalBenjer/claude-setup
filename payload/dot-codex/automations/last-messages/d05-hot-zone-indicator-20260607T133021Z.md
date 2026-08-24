Completed the scheduled automation.

Report written: [HOT_ZONES_2026-06-07.md](/home/shovalbe/.claude/docs/HOT_ZONES_2026-06-07.md)

Verification:
```text
rtk python3 /tmp/codex-hot-zones-d05/hot_zone_indicator.py
/home/shovalbe/.claude/docs/HOT_ZONES_2026-06-07.md
hot_zones=0 active_repos=11 task_attempts=0
```

Result: no current files matched the strict hot-zone filter: `src/` or `app/`, at least 3 `fix(...)` commits in the last 30 days, excluding tests/docs. No ADO tasks were filed because there were no ranked top-three hot zones.

I also checked the prompt-cited `cs-agent` webhook SHAs. They exist, but they are dated April 1-6, 2026, outside this run’s 30-day window, and the implementation path is `azure-function-crm/...`, not `src/` or `app/`. The report records that mismatch explicitly.

