# A8. CLAUDE.md Drift Per Project

Schedule: Tuesdays 6:00 PM
Repo root: every `~/projects/<name>/`
Mode: read + propose

For each active rig in `~/.hive/rigs.yaml` with a corresponding `CLAUDE.md`, plus `~/CLAUDE.md`.

Do not scan closed or inactive projects. Explicitly skip:

- `seekapa-training-platform`

1. Parse any file paths or directory references in the doc.
2. Verify each path exists with `test -e`.
3. Parse any `stack` or `deps` claims, for example `uses bun` or `Python 3.12`. Verify against `package.json` or `pyproject.toml`.
4. Parse any branch flow claim. Verify against `git branch -r`.
5. Parse any commands, for example `run pytest tests/unit`. Check that the referenced files or scripts exist.

Output `~/.claude/docs/CLAUDEMD_DRIFT_<DATE>.md` with per-project:

- Drift score from 0 to 100, as percent of claims that hold.
- List of contradicted claims.
- Suggested edits as a diff block.

Projects with drift score below 70 percent: file an ADO work item via:

```bash
~/.claude/bin/work-item.sh create --type Task --title "CLAUDE.md drift: <project>" --tags "docs-drift"
```
