# D7. Stash / WIP Leak Watch

Schedule: Daily 08:45
Repo root: all repos under `/home/shovalbe/projects/`
Mode: read + comment

For each repo, run:

```bash
git log --all --since="7 days ago" --pretty=format:"%H|%s|%an|%D" |
  grep -iE "^[^|]+\|(WIP on|index on|stash@)"
```

For each match:
- which branch where it lives
- author
- whether it's at HEAD of any branch (worst case — flagged as P0)

Output `~/.claude/docs/STASH_LEAKS_<DATE>.md`.

For commits at branch HEAD: comment on the PR (if exists):

```bash
~/.claude/bin/work-item.sh comment <pr-id> "$(cat <<'EOF'
Stash artifact at branch HEAD detected: <sha>. This is a `git stash` auto-message that should not have been pushed.

Recommended: `git reset --hard HEAD^` (after verifying nothing is lost) or `git rebase -i HEAD~N` to reword/drop.
EOF
)"
```

**Do NOT auto-rewrite.** The user owns the cleanup.

Evidence cited: cs-agent SHAs `b743d141` "WIP on feat/align-test-connector-to-production" and `4908111d` "index on feat/...". Both currently visible in the branch's commit history. Real pattern, today.
