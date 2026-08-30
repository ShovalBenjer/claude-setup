---
enforce:
  cmd: "test -f docs/INDEX.md && test -f docs/CODEBASE-MAP.md && test -f docs/DOCMAP.md && test -d docs/specs && test -d docs/prd"
---
# Docs Control Plane (concrete taxonomy)

Global rule. Binds every repo and session. The concrete directory taxonomy under the
CLAUDE.md "PRD Control Plane" rule: it fixes the shape so a PRD is always the spine, specs
are always headered and archivable, and point-in-time scans never pollute the root. Scored
by the `docs` dimension of `intent_control_plane.standards`. Owner: Shoval's setup (this
rule is mine to keep current).

## The taxonomy (every repo)

- `docs/prd/` - one living PRD per surface; front-matter names its `DEV-####` ticket(s);
  body is an acceptance table with status + evidence. THE spine.
- `docs/specs/` - dated impl specs; each carries a header: `PRD:` / `Ticket:` /
  `Status: active|superseded-by`.
- `docs/analysis/` - point-in-time gap/health scans (inputs to the TODO), never at repo root.
- `docs/adr/` - one ADR per costly-to-reverse decision (Nygard: Context/Decision/Consequences).
- ONE `TODO.md` (grouped by surface, ticket-tagged) and ONE `docs/INDEX.md` per repo.

## Rules

1. New impl `.md` goes only under `specs/`, with the `PRD:/Ticket:/Status:` header.
2. When work lands, update the PRD acceptance table; do NOT spawn a dated note.
3. Superseded specs move to `specs/archive/`.
4. Point-in-time scans go to `analysis/`, never the repo root; the root stays clean.
5. The wiki is generated from `docs/`, not hand-edited (wiki-as-code): Azure DevOps
   "Publish code as wiki" binds the `docs/` folder to the wiki so every push republishes
   PRDs and ADRs, giving a versioned, PR-reviewed, audit-traceable trail.

## Why

This turns the PRD-as-control-plane rule into a fixed, findable shape. A reader (human or
agent) always finds the PRD spine, the headered specs, the ADR trail, and one TODO/INDEX,
and never trips over scattered dated notes at the root. It is the docs dimension of the
unified repo standard (companion to `harness-structure-standard`, `repo-standards`,
`repo-topology`, `boundary-contracts`).
