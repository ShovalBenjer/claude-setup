# tools/timetravel

Point-in-time reconstruction for the bytes git never sees: files matched by
`.gitignore`, and tracked files overwritten inside a session before any commit.
Content-addressed store under `state/timetravel/`, blobs gitignored and the
manifest committed, matching how `state/snapshots/` already splits content from
evidence.

Scoped to the complement of git on purpose. `git show <rev>:state/x.jsonl`
already reconstructs any tracked, committed ledger, and this tool does not
duplicate that.

```
python tools/timetravel/snapshot.py snap
python tools/timetravel/snapshot.py at 2026-07-30T12:00 --path state/api-usage.jsonl --content
python tools/timetravel/snapshot.py log state/handback-log.jsonl
python tools/timetravel/snapshot.py changed 2026-07-30 2026-07-31
python tools/timetravel/snapshot.py verify
python tools/timetravel/snapshot.py selftest
```

Reasoning, the measured incidents that motivated it, and the case for rejecting
it are in `docs/analysis/2026-07-30-point-in-time-reconstruction.md`.
