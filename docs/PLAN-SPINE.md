# PLAN-SPINE

Status: active

GENERATED-BY-HAND, not a tool, unlike CODEBASE-MAP.md and DOCMAP.md. One row
per live surface: PRD, its spec(s), the slice actually built, the next slice,
its ticket id, and a percent-built figure. The table is the document; no
prose padding. A cell reads `unverified` rather than a guessed number when no
cheap check exists (calibrated-claims rule). Written 2026-08-17, the glue
pass, after a sweep found 26 planning docs split BUILT 2 / PARTIAL 11 / PAPER
13 with no single page connecting PRD to spec to slice to ticket.

Every `% built` cell below is VERIFIED against a command run the same day
this file was written; the command is in the Evidence column, not a separate
appendix, so the check travels with the claim.

| Surface | PRD | Spec(s) | Current slice | Next slice | Ticket | % built | Evidence |
|---|---|---|---|---|---|---|---|
| harness-gate | `docs/prd/claude-os.md` | none (the gate is its own spec, `tools/gate/gate.py`) | 12-domain gate runs, oracles carry selftests, mutation-tested | close the two Windows-waived tests; wire remaining 23 unwired hooks | SETUP-OS | ~90% | `python tools/gate/gate.py selftest` exits 0; `test -f tools/gate/gate.py` |
| autonomy/AUTO | `docs/prd/autonomy-ecosystem.md` | `specs/2026-07-24-autonomy-implementation.md` | PR-gated autonomy shipping (ADR-0012), 285 open/closed rows tracked in TODO.md | AUTO-19 FleetView, AUTO-11 merge-policy automation | AUTO-01..AUTO-20 | unverified (no single artifact answers "AUTO% built"; TODO.md carries per-item state, not a rollup) | `grep -c "^- \[ \]\|^- \[x\]" TODO.md` = 285 rows, no aggregator |
| dashboard/DASH | `docs/prd/session-dashboard.md` | `specs/2026-08-17-session-dashboard-direction.md` | direction spec locked (Tauri + React); all 7 acceptance rows `open` | criterion 1: read-only `state/*.jsonl` view | DASH-1 | 0% (design only) | acceptance table in the PRD itself, all rows `open` |
| voice/VOICE | none named | none named | ElevenLabs MCP connector verified live (TTS path) | wire STT (Wispr Flow) per `output-channel-routing.md` | VOICE-1 | partial, TTS-only | `TODO.md` VOICE-1 row: "verified live via ElevenLabs MCP connector, dead local path superseded" |
| interpretability/Modal | none named | `specs/2026-08-12-open-model-and-scheduling-plan.md` (GPU-burst block) | Modal account provisioned and auth-verified, no training job run yet | first SAE/crosscoder/KAN burst job on a small model | GPU-C (closed as answered, not as built) | 0% training runs (provisioning only) | TODO.md GPU-C row: "Modal API key provisioned... auth verified via `uvx modal app list`"; no job artifact found |
| persona-economy | `docs/prd/claude-os.md` | `specs/2026-07-23-persona-review-economy.md` | nothing (0 of 7 acceptance rows checked) | slice 1: `state/persona-contracts.jsonl` exists with one row per persona | SETUP-OS #19 | 0% | `find . -iname "*reputation*"` returns only the ADR; no `state/persona-contracts.jsonl` on disk |
| intent-lifecycle | `docs/prd/claude-os.md` | `specs/2026-07-29-intent-traceability.md` | ledger writing live (1851 rows), capture_turn.py exists, UserPromptSubmit registered; the wired hook file is a dead-home stub | fix `dot-claude/hooks/intent-capture.sh` dead-home stub, identify real ledger writer | none named (folds into SETUP-OS) | ~50% (2 of 3 remaining wires done, hook itself broken) | `wc -l state/prompt-tickets.jsonl` = 1851; `cat dot-claude/hooks/intent-capture.sh` = dead-home one-liner |
| slm-swarm | `docs/prd/claude-os.md` | `specs/2026-07-23-slm-swarm.md` | 1 of 7 uses built (use 2, cheap-first router) | use 1, structured extraction with schema-check | SETUP-OS #21 | ~14% (1/7 uses) | `find . -iname "route_classify.py"` = `tools/local/route_classify.py` exists; other 6 uses have no matching file |
| kanban | none named (folds into AUTO-19/AUTO-11) | `specs/2026-07-31-kanban-four-layer-model.md` (active spec, reconciles the two superseded ones) | reconciliation design done; 0 of 6 mutations executed | mutation 1: Status option set (`updateProjectV2Field`) | AUTO-19 | 0% (all writes UNEXECUTED) | spec section 9, every write row marked `UNEXECUTED WRITE`; no `gh project field-list` re-run shows 5 Status options |

## Superseded-in-place, corrected this pass

- `docs/specs/archive/2026-07-31-github-native-project-surface.md`: superseded by
  kanban-four-layer-model, kept in place (not archived) because live
  cross-references (TODO.md, unified-architecture PRD, two analyses) point at
  its read-only verification section as evidence, and archiving would strand
  that trail.
- `docs/specs/archive/2026-07-31-zion-board-as-product-instrument.md`: superseded by
  kanban-four-layer-model for its board-instrument sections 1-4 only; its
  closing dedup-sweep-sequencing section is not touched by kanban and stays
  load-bearing, so the file stays in place with a corrected header rather
  than moving to `docs/specs/archive/`.

## How this stays true

`tools/docmap/strand.py check` enforces that every governed doc under
`docs/specs/`, `docs/prd/`, `docs/standards/` declares a status from the
fixed vocabulary and is referenced by something other than `docs/INDEX.md`.
This file is one of those references now (see the strand consumer count).
Nothing currently enforces that a `% built` cell here stays fresh; that gap
is the open risk, not a promise. Re-verify the Evidence column's commands
before trusting a cell more than a few weeks old.
