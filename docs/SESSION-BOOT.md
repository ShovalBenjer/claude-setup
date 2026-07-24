# SESSION-BOOT — full context from disk in 60 seconds (ADR-0010)

Read in this order, nothing else needed:

1. `CLAUDE-OS.md` §0-§2 — what the system is (skim; you likely know it).
2. `docs/charters.md` — name your lane. Default for harness work: lane B.
3. `TODO.md` — current state by phase; DONE list = what exists.
4. `docs/prd/autonomy-ecosystem.md` — the live acceptance table (AUTO-*).
5. `tools/selfimprove/proposals.jsonl` — ranked open work; claim before starting.
6. `state/compact-log.md` (if present) — last session's dying snapshot.

Then verify ground truth (never trust docs over these):

```
git -C ~/claude-setup status -sb        # clean? on main?
git -C ~/claude-setup log --oneline -5  # last landed work
gh pr list -R shovalbenjer/claude-setup # open autonomy/review PRs
```

Operating rules already binding: disk-is-memory (write-through everything, ADR-0010);
autonomy only via PR gate (ADR-0012); /diverge on design decisions; lessons ledger on
any surprise; done = evidence + intent-coverage statement.

Archive provenance (if you need the work history): work bundles at
`~/Downloads/new-recruit/work-archive-2026-07-12/`, import record at
`docs/analysis/2026-07-24-work-archive-import.md`.
