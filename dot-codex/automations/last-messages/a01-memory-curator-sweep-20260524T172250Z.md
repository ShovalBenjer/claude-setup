Created the proposal report at [MEMORY_PROPOSALS_2026-05-24.md](/home/shovalbe/.claude/docs/MEMORY_PROPOSALS_2026-05-24.md).

Verification:
- `rtk wc -l /home/shovalbe/.claude/docs/MEMORY_PROPOSALS_2026-05-24.md` -> `198`
- `rtk rg -n '^## (ADD|UPDATE|REMOVE|NOOP|BLOCKED)' ...` -> all required sections present
- `rtk git status --short -- ...memory` -> only the new report is untracked; no `memory/` files changed
- Secret scan on the report for private keys, `sk-*`, and raw bearer values returned no matches

Summary: proposed 4 ADD items, 3 UPDATE items, 0 REMOVE items, plus NOOP confirmations and scan evidence.