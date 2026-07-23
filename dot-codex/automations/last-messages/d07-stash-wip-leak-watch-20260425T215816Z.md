Wrote the report to [STASH_LEAKS_20260425.md](/home/shovalbe/.claude/docs/STASH_LEAKS_20260425.md).

Summary: scanned 11 valid repos under `/home/shovalbe/projects/`; found 3 stash-pattern commits, all reachable only via `refs/stash`; found 0 branch HEAD leaks, so 0 PR comments were posted.

Verification:
- `rtk ls -l /home/shovalbe/.claude/docs/STASH_LEAKS_20260425.md` -> file exists, `7.1K`
- `rtk wc -l /home/shovalbe/.claude/docs/STASH_LEAKS_20260425.md` -> `126`
- Report includes the scan evidence, skipped invalid `.git` candidates, and the cs-agent cited SHA check.