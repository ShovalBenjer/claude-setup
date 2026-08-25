# Analysis Archive

Dated analysis snapshots that have been superseded, absorbed, or whose findings have
reached a mechanism. These are point-in-time scans and are not maintained.

## What belongs here

- Analysis documents whose findings have been absorbed into specs, standards, or code.
- Dated snapshots with no live referrer outside of `docs/INDEX.md` and `docs/DOCMAP.md`.
- Closed handoff documents and session retrospection whose action items are complete.

## Migration procedure

1. Verify the analysis has no live referrers (beyond `docs/INDEX.md` and `docs/DOCMAP.md`).
2. Move the document to `docs/analysis/archive/`.
3. Update references in `docs/INDEX.md` to point to `analysis/archive/<filename>`.
4. Write a migration note in `docs/archive/MIGRATION-YYYY-MM-DD.md`.
5. Regenerate `docs/DOCMAP.md` via `python tools/docmap/docmap.py write`.
6. Commit with message: `docs: archive analysis/<filename> - <reason>`.

## Current state

No analysis documents have been migrated in this pass. The following are candidates
for future migration (documented in `docs/archive/MIGRATION-2026-08-24.md`):

- `analysis/2026-07-23-local-model-stress-test.md` - superseded by model-selection.md
- `analysis/2026-07-24-creativity-wow-gap.md` - absorbed into specs/2026-08-03-detail-passes-teleology-and-creativity.md
- `analysis/2026-07-24-deployment-gap-audit.md` - findings absorbed, no live mechanism
- `analysis/2026-07-24-fleet-verification-gap.md` - historical record only
- `analysis/2026-07-24-reference-repos-excavation.md` - absorbed into prior-art records
- `analysis/2026-07-24-research-wiring-audit.md` - tool still unbuilt (research_sweep.py)
- `analysis/2026-07-24-setup-holding-us-back.md` - synthesis completed, decisions made
- `analysis/2026-07-24-skills-wiring-audit.md` - absorbed into skills_sync.py
- `analysis/2026-07-25-claude-mastery-audit.md` - historical record
- `analysis/2026-07-25-claude-mastery-research-prompt.md` - prompt archived
- `analysis/2026-07-25-our-own-dolt.md` - Dolt rejected, 3 of 5 features absorbed
- `analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md` - findings absorbed into layers
- `analysis/2026-07-29-local-dependency-audit.md` - findings addressed or owned
- `analysis/2026-07-29-session-retro-modes-models-workflows-observability.md` - retro complete
- `analysis/2026-07-30-point-in-time-reconstruction.md` - Dolt decision made
- `analysis/2026-08-03-math-trends-and-model-stack.md` - historical snapshot
- `analysis/2026-08-05-implementation-reasoning-per-file.md` - per-file rationale, superseded by ADR-0021
- `analysis/2026-08-06-skill-candidates-dependency-filter.md` - candidates decided
- `analysis/2026-08-07-toplevel-dir-decisions.md` - 3 decisions still open
- `analysis/2026-08-08-na-domains-rechecked.md` - recheck complete
- `analysis/2026-08-09-session-scope-ledger.md` - scope accounted for
- `analysis/2026-08-10-inbox-secret-exposure.md` - active security finding (NOT archive candidate)
- `analysis/2026-08-10-milestone-task-plan.md` - superseded by 2026-08-11 version
- `analysis/2026-08-10-three-skill-trees-measured.md` - measurement complete, findings in TODO
- `analysis/2026-08-11-estate-audit.md` - audit complete, findings tracked in TODO
- `analysis/2026-08-11-milestone-task-plan.md` - superseded by newer planning
- `analysis/2026-08-11-repo-compare.md` - comparison complete
- `analysis/2026-08-12-claude-code-repo-gap.md` - gap analysis complete
- `analysis/2026-08-12-minimalism-audit.md` - audit complete, batch pass pending
- `analysis/2026-08-12-plain-handoff.md` - handoff delivered
- `analysis/2026-08-13-buzz-adoption-handoff.md` - handoff delivered
- `analysis/2026-08-13-repo-compare-ui-ux.md` - comparison complete
- `analysis/2026-08-15-frontier-curriculum.md` - curriculum design
- `analysis/2026-08-15-research-context-audit-and-forecast.md` - audit complete
- `analysis/2026-08-15-research-to-repo-work-map.md` - mapping complete
- `analysis/2026-08-15-unfinished-work-inventory.md` - inventory complete, items in TODO
- `analysis/2026-08-17-external-landscape-comparison.md` - comparison complete
- `analysis/2026-08-17-repo-compare-block-buzz.md` - comparison complete
- `analysis/2026-08-17-repo-compare-everything-claude-code.md` - comparison complete
- `analysis/2026-08-23-books-corpus-wiring.md` - wiring complete
- `analysis/2026-08-23-dashboard-stack-and-supply-chain.md` - stack decided
- `analysis/2026-08-23-issue-and-milestone-reasoning.md` - reasoning delivered
- `analysis/2026-08-23-pocock-skills-delta.md` - delta measured
- `analysis/2026-08-23-prompt-triage.md` - triage complete
- `analysis/2026-08-23-whatsapp-links-vs-plan.md` - triage complete
- `analysis/2026-08-23-whatsapp-repo-reminder-list.md` - list compiled
