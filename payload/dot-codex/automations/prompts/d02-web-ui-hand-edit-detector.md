# D2. ADO Web UI Hand-Edit Detector

Schedule: Weekdays 09:30
Repo root: all active repos under `/home/shovalbe/projects/`
Mode: read + ADO comment

Walk all branches updated in the last 24h. For each commit, classify as **web-ui-hand-edit** if ALL these hold:

- Subject matches `/^(Updated?|Add(ed)?|Created?) [^\s].*\.(yml|yaml|sh|md|json|tf)$/`
- Body is empty (`git log -1 --format=%b == ""`)
- One file changed, ≤5 lines diff
- Author email is a non-CI committer (not `*@dev.azure.com`)

For each match:

1. Append to `~/.claude/docs/HANDEDIT_LOG_<DATE>.md` (path, sha, author, branch, file).
2. Comment on the active PR for that branch (if exists):

```bash
~/.claude/bin/work-item.sh comment <pr-id> "$(cat <<'EOF'
Direct ADO Web UI edit detected: <sha>. This bypassed forge-loop spec + reviewer. Pull the change locally, attach to a feature/* branch with linked work item, or document why this was a hotfix.
EOF
)"
```

3. If no PR exists: file an ADO Task via `~/.claude/bin/work-item.sh create --type Task --tags "forge-loop-bypass"` with body listing the commits and which forge-loop step (spec / RED / GREEN / REFACTOR) each one skipped.

Never auto-revert. Never block the branch. Only surface and tag.

Evidence cited: SHAs `83a51eb`, `ad78fbb`, `f714783`, `ef6d736`, `253c7a9` — all on `feature/v59-realmid-fix-multi-agent`, all by Yasha, all 1-line direct edits. This is the smoking-gun automation for that pattern.
