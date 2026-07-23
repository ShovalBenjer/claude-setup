# D3. Duplicate Commit Detector

Schedule: Tuesdays 11:30
Repo root: all repos under `/home/shovalbe/projects/`
Mode: read + summary file

For each repo, run:

```bash
git log --all --since="14 days ago" --pretty=format:"%H|%s|%an|%cd"
```

Group by exact subject + author. Flag any subject that appears ≥2 times across distinct SHAs.

For each duplicate group, output:
- subject
- list of `(sha, branch, date)`
- diff between the SHAs (likely identical — confirm)
- recommendation: which SHA to keep, which to drop, and how (interactive rebase vs cherry-pick `--strategy=ours`)

Save to `~/.claude/docs/DUPLICATE_COMMITS_<DATE>.md`.

**Do NOT rewrite history.** Recommend only.

Filters:
- Ignore subjects shorter than 20 chars (too generic to matter).
- Ignore `Merged PR N` (ADO auto-merge produces these).
- Ignore `WIP on` / `index on` (handled by D7).

Evidence cited: campaign-analysis SHAs `215e090`+`d1b1ecf`, `3929590`+`658cbc6`, `5394674`+`13ddb3a`, `bff6ee0`+`298e0aa`, `35764ac`+`296c05e` — five duplicate pairs in recent history. Cherry-pick / rebase without strategy is the pattern.
