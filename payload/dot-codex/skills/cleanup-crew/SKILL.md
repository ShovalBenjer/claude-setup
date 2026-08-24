---
name: cleanup-crew
description: "Cleanup Crew - SOTA 2026"
allowed-tools: ["Bash", "Read", "Edit", "Grep", "Glob"]
---

# Cleanup Crew - SOTA 2026

**Invocation:** `/cleanup-crew` | `~/.codex/skills/cleanup-crew/detect.sh`

## Workflow

1. **Detect** (read-only): `detect.sh` → reports in `.cleanup/`
2. **Review**: Human verification (watchdog blocks >100 files)
3. **Cleanup**: `cleanup.sh` → small batches (10-50), test between
4. **Commit**: Atomic commits per type
5. **Verify**: `/ground-truth`

## Detection

**JavaScript:** `bunx knip --reporter json > .cleanup/knip-report.json`
**Python:** `uv run ruff check --select F401,F841 src/ > .cleanup/ruff-unused.txt`
**Docs:** `find .codex/docs -name "*.md" -mtime +90 > .cleanup/stale-docs.txt`

## Cleanup Types

1. Dead code (Knip, Ruff, Vulture)
2. Unused dependencies
3. Stale docs → `.codex/archive/`
4. Build artifacts (`__pycache__`, `.DS_Store`)

## Safety

**Never delete:** `.git/`, `.env`, `node_modules/`, `.venv/`, lock files, `.codex/rules/`, `.codex/hooks/`
**Require approval:** >50 files, >10 deps, .codex/ changes
**Watchdog:** Blocks bulk deletions

## Atomic Commits

```bash
git commit -m "chore: remove dead code (Knip-verified)"
git commit -m "chore: remove unused dependencies"
git commit -m "chore: archive stale documentation"
```

## Integration

- Watchdog: Prevents destructive bulk ops
- Ground-truth: Verifies no regressions
- Per-project: Auto-detects tooling (bun vs uv)
