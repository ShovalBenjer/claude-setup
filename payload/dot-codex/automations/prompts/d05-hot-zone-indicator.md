# D5. Hot Zone Indicator (files churning faster than tests)

Schedule: Wednesdays 11:00
Repo root: all active repos
Mode: read + propose tests

For each repo, find the top 5 files by `fix()` commit count in the last 30 days:

```bash
git log --since="30 days ago" --name-only --pretty=format: |
  sort | uniq -c | sort -rn | head -50
```

Filter to files where:
- ≥3 commits with subject prefix `/^fix\(/`
- file is in `src/` or `app/` (not `tests/`, not `docs/`)

For each hot-zone file:
- list the `fix()` commits and their messages (1-line each)
- check if a parallel test file exists in `tests/` with similar name
- if no test file exists: high priority
- if test file exists: count `def test_*` / `it(`/`test(` (rough proxy for assertions)
- compute **fix-to-test-assertion ratio** (more fixes per assertion = bad)

Output `~/.claude/docs/HOT_ZONES_<DATE>.md` ranked by ratio (worst first).

For top 3: file an ADO Task via:

```bash
~/.claude/bin/work-item.sh create --type Task \
  --title "Hot zone needs regression tests: <file>" \
  --tags "test-debt"
```

Body: the fix log + a suggested regression test (one per `fix()` commit), each describing the *behavior* (not the diff) that should be locked in.

Evidence cited: cs-agent SHAs `9c05bfed`, `1a241851`, `be30edc7`, `985a0967` — four `fix(webhook)` commits in 30 days, no parallel test file added in any of them. The pattern reveals webhook flow is the hot zone.
