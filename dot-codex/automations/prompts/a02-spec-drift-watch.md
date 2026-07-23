# A2. Spec Drift Watch

Schedule: Wednesdays 10:00 AM
Repo root: `/home/shovalbe/projects/docs/superpowers/specs/` and project-level specs
Mode: read + ADO comment/work item when requested below

Walk every file under `docs/superpowers/specs/` and any project-level `docs/specs/` directories. For each spec:

1. Read the frontmatter date and status.
2. Check git log for the file's last modification date.
3. Cross-reference against the most recent commit on the branch the spec names: do any of the spec's listed files exist with non-zero LOC yet?
4. Classify:
   - `ACTIVE`: modified <7 days, has a `feat/*` branch with code.
   - `STALLED`: older >14 days, no code on the branch named in the spec.
   - `ORPHAN`: branch deleted, spec status still `draft`.
   - `MERGED`: code shipped, spec not closed out.

Output `~/.claude/docs/SPEC_DRIFT_<DATE>.md` with one row per spec.

For `STALLED` and `ORPHAN`: file an ADO work item via:

```bash
~/.claude/bin/work-item.sh create --title "Spec stalled: <name>" --type Task --tags "spec-drift"
```

Include the spec path, days since last edit, and a checklist of options: resume, archive, or split.
