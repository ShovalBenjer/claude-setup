# Specs Archive

Status: reference. Superseded or retired technical specifications. These documents are preserved for
historical reference but are no longer maintained.

## What belongs here

- Specs superseded by a newer version (e.g., v1 superseded by v2).
- Specs whose decisions have been implemented and are now recorded in ADRs.
- Specs that were speculative and were never built.

## Migration procedure

1. Verify the spec has been superseded or its decisions have reached a mechanism.
2. Move the document to `docs/specs/archive/`.
3. Update the superseding spec or ADR to reference the archived version.
4. Write a migration note in `docs/archive/MIGRATION-YYYY-MM-DD.md`.
5. Regenerate `docs/DOCMAP.md` via `python tools/docmap/docmap.py write`.
6. Commit with message: `docs: archive specs/<filename> - <reason>`.

## Current state

No specifications have been migrated in this pass. The following are candidates
for future migration (documented in `docs/archive/MIGRATION-2026-08-24.md`):

- `specs/2026-07-29-architecture-build-plan.md` - superseded by v2 the same day
- `specs/2026-07-31-github-native-project-surface.md` - design complete, some ideas adopted
