# MIGRATION-2026-08-24: Mature documentation system pass

This migration log records all archival, deletion, and restructuring performed during
the mature documentation system pass (convoy/claude-setup-reorganization-cleanup/0de18e7b).

## Deleted

| File | Reason |
|---|---|
| `docs/icepanel-intent-to-done.json` | Stale IcePanel export artifact. No live referrers. Superseded by `docs/DOCMAP.md` and `docs/CODEBASE-MAP.md`. |

## Archived

No files were moved into `docs/archive/`, `docs/analysis/archive/`, or `docs/specs/archive/`
in this pass. Candidates are documented below with the rationale for deferring.

## Deferred candidates

### Analysis documents (37 candidates)

All 37 analysis documents in `docs/analysis/` remain in place. Rationale:

- **Live references:** Every analysis document is referenced by `docs/INDEX.md` or
  `docs/DOCMAP.md`. Archiving requires updating both files and the docmap generator.
- **Active findings:** Several documents contain open security findings (e.g.,
  `2026-08-10-inbox-secret-exposure.md`) or operator decisions (`2026-08-07-toplevel-dir-decisions.md`)
  that are still open.
- **TODO dependencies:** Many TODO rows reference specific analysis files by path.
  Moving those files would break TODO links.

Recommended future pass: archive analysis documents whose findings are closed AND
whose last reference in `TODO.md` is marked `[x]` or superseded.

### Spec documents (2 candidates)

- `specs/2026-07-29-architecture-build-plan.md` - Superseded by v2 the same day.
  **Deferred:** `docs/INDEX.md` references both versions side by side. Moving one
  requires updating the INDEX entry.
- `specs/2026-07-31-github-native-project-surface.md` - Design complete.
  **Deferred:** Referenced by `docs/INDEX.md` and `docs/prd/2026-08-03-unified-architecture.md`.

### Top-level documents (2 candidates)

- `docs/ESTATE-DIRECTORY-CATALOG.md` - Point-in-time snapshot. **Deferred:** referenced
  by `docs/INDEX.md` spine and `docs/DOCMAP.md`. Regenerating `docs/CODEBASE-MAP.md`
  makes this stale, but the INDEX link must be updated first.
- `docs/EXECUTION-PLAN.md` - Point-in-time P0-P4 plan. **Deferred:** referenced by
  `docs/INDEX.md` spine. Content is still directionally accurate.

## Structural changes

| Action | Path | Description |
|---|---|---|
| Created | `docs/archive/` | Top-level archive for retired content |
| Created | `docs/archive/README.md` | Archive policy, structure, and migration procedure |
| Created | `docs/analysis/archive/` | Dated analysis snapshot archive |
| Created | `docs/analysis/archive/README.md` | Analysis archive policy and candidate list |
| Created | `docs/specs/archive/` | Superseded specification archive |
| Created | `docs/specs/archive/README.md` | Spec archive policy and candidate list |
| Regenerated | `docs/DOCMAP.md` | Living document inventory (983 docs, 68 reachable) |
| Regenerated | `docs/CODEBASE-MAP.md` | Directory purpose map (439 dirs, 0 undocumented) |

## Verification

```bash
python tools/map/codemap.py write       # Regenerates CODEBASE-MAP.md
python tools/docmap/docmap.py write      # Regenerates DOCMAP.md
python tools/map/codemap.py check        # Verifies directory purposes
python tools/docmap/docmap.py check       # Verifies document status declarations
```

All checks pass after this migration.

## Next actions

1. Close or supersede open analysis findings that block archival.
2. Update `docs/INDEX.md` to remove spine entries for archived documents.
3. Run a second migration pass to move closed documents into archive directories.
4. Ratchet `docs/DOCMAP.md` reachability: currently 6.9% (68/983); target >80%.
