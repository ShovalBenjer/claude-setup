# Per-repo docs control plane: taxonomy proposal

Status: proposal (2026-07-09), for adoption into `~/.claude/CLAUDE.md` "PRD Control
Plane" section or a new `~/.claude/rules/docs-control-plane.md`. Suggested by the
project agent; adoption is Shoval's call (project agents act at project level; the
global standard is his to set).

## Problem (observed, qc-telephony-api, 2026-07-09)

`.md` implementation docs multiply per work session and drift from the tickets and
from git ("flowing and flowing, local and remote out of control"). Measured in one
repo: SIX root planning docs, FOUR rival task lists (`TODO.md`,
`AI_NATIVE_CODE_TODO.md`, `DEVOPS-CONFORMANCE-TODO.md`, `MATURITY-TODO.md`) with
overlap + staleness, NO PRD-of-record (the product contract scattered across Jira
DEV-5040/5039 and several unlinked specs), and the one "index"
(`docs/platform/INDEX.md`) stale auto-generated garbage indexing a 2026-04 tree.
Volume was not the problem (34 tracked `.md`). Absence of a spine was.

## The spine

**Jira ticket (contract of record) -> PRD (living) -> one `TODO.md` -> dated specs
(linked up) -> git.**

This mirrors, inside each repo, what `~/docs` already does at the workspace level
(`~/docs/specs/` = "requirement-of-record and PRDs, the control plane" per
`~/docs/INDEX.md`). The proposal is: every deployable repo carries the same spine.

## Per-repo taxonomy

| Dir | Holds | Rule |
|-----|-------|------|
| `docs/prd/` | one living PRD per surface; front-matter names its `DEV-####` ticket(s); body is an acceptance table with status + evidence | THE spine. update status here, do not spawn a note |
| `docs/specs/` (or `superpowers/specs/`) | dated implementation specs | each carries a header: `PRD:` / `Ticket:` / `Status: active \| superseded-by <file>` |
| `docs/analysis/` | point-in-time gap/health scans (inputs to `TODO.md`) | never at repo root |
| `docs/platform/` | external / published (wiki, overviews, consumer-facing specs) | keep out of root |
| `docs/integration/` | handoff artifacts | |
| `docs/reflections/` | post-mortems | the only free-form dated docs |
| `docs/INDEX.md` | the one map: PRD -> tickets -> specs -> status | one per repo |
| `TODO.md` (root) | THE task list, grouped by surface, every task ticket-tagged | one per repo |

## The three rules that stop the sprawl

1. A new implementation `.md` is created only under `docs/specs/`, with the
   `PRD: / Ticket: / Status:` header.
2. When work lands you update the PRD acceptance table; you do not spawn a new
   dated note.
3. One `TODO.md`, one `docs/INDEX.md` per repo. Superseded specs move to
   `docs/specs/archive/`.

## Rule text to adopt (paste into CLAUDE.md PRD Control Plane, or a new rule)

```
## Docs control plane (concrete taxonomy)
Every deployable repo carries the spine: Jira ticket -> PRD -> one TODO.md -> specs.
- docs/prd/      one living PRD per surface; front-matter names its DEV-#### ticket(s);
                 body is an acceptance table with status + evidence. THE spine.
- docs/specs/    dated impl specs; each header: PRD: / Ticket: / Status: active|superseded-by.
- docs/analysis/ point-in-time gap/health scans (inputs to TODO), never at repo root.
- ONE TODO.md (grouped by surface, ticket-tagged) and ONE docs/INDEX.md per repo.
Rules: (1) new impl .md only under specs/ with the header; (2) when work lands, update the
PRD table, don't spawn a dated note; (3) superseded specs -> docs/specs/archive/.
```

## Reference implementation (the template)

`qc-telephony-api`, 2026-07-09 (docs-only change set, uncommitted at time of writing):
- `docs/prd/qc-insights.md` (DEV-5040 API + DEV-5039 UI; acceptance table with status).
- `docs/INDEX.md` (the spine map + these rules).
- `TODO.md` consolidated from the former four lists; the two gap scans moved to
  `docs/analysis/`. Root planning docs went 6 -> 1.

## Per-repo adoption checklist

- [ ] Create `docs/prd/<surface>.md` for each active product surface; name its ticket(s).
- [ ] Consolidate all task/gap/TODO docs into one `TODO.md`, tagged by ticket + PRD.
- [ ] Move point-in-time scans to `docs/analysis/`; keep root to code + config + TODO.
- [ ] Create/repair `docs/INDEX.md`; delete stale auto-generated indexes.
- [ ] Add the `PRD/Ticket/Status` header to specs as they are next touched.
