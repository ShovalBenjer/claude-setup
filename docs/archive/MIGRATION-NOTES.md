# Archive - Migration Notes

This directory holds retired, superseded, or closed content that must never be deleted
silently. Every file here carries a `Status:` or is declared in `docs/doc-status.txt` so the
docmap domain stays clean. A document lands here for one of three reasons:

1. **Closed work** - a task tracker item that is done and no longer belongs in the live
   roadmap (`TODO.md`). Moved, not deleted, so the history of what was accomplished survives.
2. **Superseded plans** - a predecessor plan absorbed by `CLAUDE-OS.md` or a newer spec. The
   supersession table in `CLAUDE-OS.md` §10 records the disposition.
3. **Operator input** - research pastes or external dumps that were INPUT to the repo, not
   documents it maintains.

## Index of archive contents

| File | Moved | Why | Successor / disposition |
|---|---|---|---|
| `2026-08-24-todo-done-archive.md` | 2026-08-24 | Closed `TODO.md` items extracted when `TODO.md` became a roadmap | `TODO.md` (roadmap) |
| `2026-07-29-external-absorption-brief.md` | 2026-07-31 | Dated-snapshot brief, absorbed | `docs/analysis/` lineage |
| `HANDOFF-*.md` | 2026-07-27 → 2026-08-05 | Per-session handoff docs, frozen at session close | consolidated into `CLAUDE-OS.md` |
| `gemini-code-*.md`, `prompt-research-*.md` | - | Operator-supplied research pastes (INPUT) | n/a |
| `sagemaker-hyperpod.md` | 2026-08-12 | Fetched AWS doc page, dropped | belongs under `docs/analysis/` if kept |

## Migration rules

- A change reaches "production" when it is **merged to `main` and smoke-tested**
  (`dot-codex/rules/production-means-merged-and-smoked.md`). Archiving is a documentation
  move, not a deployment.
- Do not hand-edit `docs/DOCMAP.md` (generated). If you add a file here, declare its status in
  `docs/doc-status.txt` or it reads UNDECLARED and fails the gate.
- Prefer moving a closed item to this directory over deleting it; a deleted finding is a
  finding nobody can re-verify.
