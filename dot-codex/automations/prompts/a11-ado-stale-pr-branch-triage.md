# A11. ADO Stale PR / Branch Triage

Schedule: Wednesdays 9:00 AM
Repo root: all Seekapa ADO repos
Mode: read + ADO comment + summary

Using `az repos pr list --status active` and `az repos ref list`, for each Seekapa repo on `dev.azure.com/Corp-domain/Corp-AI`:

1. PRs older than 5 days with no review activity: list with author and title.
2. PRs marked draft for more than 14 days: list as likely abandoned.
3. Branches older than 30 days with no commits and no open PR: list.
4. Branches that match `feature/*` but never merged to `stage`: list.

Output `~/.claude/docs/ADO_STALE_<DATE>.md`.

For PRs older than 5 days with no review activity, comment via:

```bash
~/.claude/bin/work-item.sh comment "This PR has been idle for N days; reviewer is X. Bump or close?"
```

Comment only once per PR. Track already-bumped PRs in `~/.claude/cache/ado-bumped-prs.txt` to avoid spamming.

Do not close PRs or delete branches automatically.
