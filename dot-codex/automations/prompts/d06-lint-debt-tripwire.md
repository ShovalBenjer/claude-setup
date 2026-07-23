# D6. Lint Debt Tripwire

Schedule: Weekdays 18:30
Repo root: all Python repos under `/home/shovalbe/projects/`
Mode: read + threshold alert

For each Python repo:

```bash
cd <repo>
uv run ruff check src/ --output-format=json | jq 'length'
```

Compare against the 7-day-rolling baseline stored at `~/.claude/cache/lint-baseline-<repo>.txt`.

Thresholds:
- count grew by `>20` violations vs baseline → **ALERT**
- count `>50` absolute → **ALERT**
- count `>100` absolute → file an ADO Task

Output `~/.claude/docs/LINT_DEBT_<DATE>.md` per-repo:
- current count
- 7-day delta
- top 5 rule codes
- files most affected (top 5)
- offending PRs (last 7 days, by author)

Update the baseline ONLY if count decreased — never silently accept growth.

For ALERT: comment on the most recent open PR via:

```bash
~/.claude/bin/work-item.sh comment <pr-id> "Lint debt grew by N violations on this PR. New rule codes: ..."
```

For >100 absolute: file an ADO Task to schedule a cleanup sprint.

Evidence cited: cs-agent SHA `1cd32c4c` "chore(lint): resolve all 164 ruff violations across codebase" — that one batched fix is the anti-pattern. Catching at +20 prevents the next batch.
