# Docs Index: Claude OS

Every tracked prose document under `docs/`, grouped. One TODO, one INDEX
(docs-control-plane rule).

Coverage is the point. On 2026-07-31 this file listed 22 of 112 prose documents;
`docs/DOCMAP.md` had been printing that reachability number on every regeneration
with nothing failing on it. Measured in
`analysis/2026-07-31-inventory-reconciliation-and-the-docs-control-plane.md`.
A status shown as `not declared` is a real gap in that document, not a gap here:
`docmap.py` derives a class-based status when a document declares none, which
answers what kind of document it is and never whether it is still true.

Titles and declared statuses below were extracted from the files themselves rather
than written from memory; the spine section is hand-curated. There is no generator on
disk, which means this file WILL drift the next time a document lands. That is the
open ticket, not a promise made here: nothing currently fails when it drifts.

## Spine

- [../CLAUDE-OS.md](../CLAUDE-OS.md): single source of truth. Layers L0 to L8, deep-work protocol, native-feature map, supersession table.
- [SESSION-BOOT.md](SESSION-BOOT.md): any fresh session, full context from disk in 60 seconds (ADR-0010).
- [charters.md](charters.md): the four session lanes A/B/C/D. Letters renumbered from B/C/D/E by ADR-0016 on 2026-07-30; pre-cutover ledger rows still say the old letter.
- [OPERATOR-RUNBOOK.md](OPERATOR-RUNBOOK.md): the manual steps only the operator can do.
- [EXECUTION-PLAN.md](EXECUTION-PLAN.md): P0 to P4 harness build phases.
- [SYSTEM-MAP.md](SYSTEM-MAP.md): the whole OS scored inv-versus-need. Created 2026-07-24; several rows marked VERIFIED there are now stale, corrected in the 2026-07-31 reconciliation.
- [QUALITY-CONTRACT.md](QUALITY-CONTRACT.md): why `quality-contract.json` says what it says, per domain.
- [taste.md](taste.md): the /diverge pick ledger, one row per decision with its reason.
- [ESTATE-DIRECTORY-CATALOG.md](ESTATE-DIRECTORY-CATALOG.md): directory and repository catalog for the estate.
- [dir-purpose.txt](dir-purpose.txt), [doc-status.txt](doc-status.txt): the two registries `codemap.py` and `docmap.py` read.
- [CODEBASE-MAP.md](CODEBASE-MAP.md), [DOCMAP.md](DOCMAP.md): GENERATED. A hand edit reads as drift and fails the gate.

## PRDs

- [prd/2026-07-30-consolidation-and-migration.md](prd/2026-07-30-consolidation-and-migration.md): PRD: Consolidation, document mapping, and the Linux migration *(status: APPROVED for autonomous execution )*
- [prd/autonomy-ecosystem.md](prd/autonomy-ecosystem.md): PRD: Autonomy Ecosystem (Claude OS v2) *(status: living)*
- [prd/claude-os.md](prd/claude-os.md): PRD: Claude OS (personal Claude control plane) *(status: active)*

## Standards

- [standards/agentic-repo-standard.md](standards/agentic-repo-standard.md): Root agentic repository standard *(status: active)*

## ADRs

- [0001](adr/0001-claude-setup-as-canonical-os-repo.md): claude-setup is the canonical OS repo
- [0002](adr/0002-subscription-oauth-over-metered-api.md): Subscription OAuth token, not metered API key, for all fleet auth
- [0003](adr/0003-native-push-over-onesignal.md): Native Claude push for the personal approvals rail, not OneSignal
- [0004](adr/0004-two-model-agreement-gate.md): PR review uses a two-model agreement gate
- [0005](adr/0005-enforcement-over-prose.md): Enforcement over prose (hooks/gates bind, CLAUDE.md requests)
- [0006](adr/0006-one-scheduler-topology.md): One scheduler topology: native cron local + cloud routines
- [0007](adr/0007-codex-reviewer-only.md): Second reviewer = free different-family models (Codex removed)
- [0008](adr/0008-reputation-from-external-truth-only.md): Persona reputation is computed from external ground truth ONLY
- [0009](adr/0009-slm-swarm-asymmetric-leaf-executors.md): SLM swarm = asymmetric leaf executors + trace flywheel (not a debate swarm)
- [0010](adr/0010-sessions-are-ephemeral-disk-is-memory.md): Sessions are ephemeral; disk is the only memory
- [0011](adr/0011-one-operational-state-db.md): One operational state DB (ecosystem.db), seeded from intent-control-plane
- [0012](adr/0012-autonomy-ships-only-via-pr-gate.md): Autonomous work ships ONLY through PR + review gate
- [0013](adr/0013-session-topology-concierge-plus-lanes.md): Session topology: one concierge + three chartered lanes
- [0014](adr/0014-social-publish-draft-first-hard-gate.md): Social publishing is draft-first behind a hard phone-approval gate
- [0015](adr/0015-opus5-default-fable-exceptional.md): Opus 5 is the lead default; Fable is exceptional-only
- [0016](adr/0016-lane-letters-renumbered-a-through-d.md): Lane letters renumbered B/C/D/E to A/B/C/D
- [0017](adr/0017-intent-control-plane-lives-in-claude-setup.md): intent-control-plane is authoritative in claude-setup; the new-recruit copy is redundant
- [0018](adr/0018-two-tier-inter-agent-channel.md): inter-agent messages get two channels, and the dense one carries an oracle
- [0019](adr/0019-supply-chain-verification.md): third-party tools are adopted on recorded evidence, not refused on principle
- [0020](adr/0020-agentic-repo-standard.md): one repository standard for the estate, enforced by adopted alint

## Specs

- [specs/2026-07-23-persona-review-economy.md](specs/2026-07-23-persona-review-economy.md): Spec: Persona Review Economy (a dynamic labor market of reviewers) *(status: active)*
- [specs/2026-07-23-slm-swarm.md](specs/2026-07-23-slm-swarm.md): Spec: SLM Swarm (how we actually use small models) *(status: active)*
- [specs/2026-07-24-autonomy-implementation.md](specs/2026-07-24-autonomy-implementation.md): Implementation spec: Autonomy Ecosystem *(status: active)*
- [specs/2026-07-24-command-center-superior.md](specs/2026-07-24-command-center-superior.md): Spec: FleetView: a superior command center over the Claude OS *(status: active)*
- [specs/2026-07-29-architecture-build-plan-v2.md](specs/2026-07-29-architecture-build-plan-v2.md): Architecture build plan v2, 2026-07-29 (supersedes v1 the same day) *(status not declared)*
- [specs/2026-07-29-architecture-build-plan.md](specs/2026-07-29-architecture-build-plan.md): Architecture build plan, merged 2026-07-29 (plan of record) *(status not declared)*
- [specs/2026-07-29-decision-rules.md](specs/2026-07-29-decision-rules.md): Decision rules: when to use what *(status: proposed)*
- [specs/2026-07-29-deterministic-preflight.md](specs/2026-07-29-deterministic-preflight.md): Deterministic preflight: proposal (not built) *(status: PROPOSAL, operator-originated 2026)*
- [specs/2026-07-29-intent-traceability.md](specs/2026-07-29-intent-traceability.md): Intent traceability: wiring, not building *(status not declared)*
- [specs/2026-07-29-prompt-to-ticket-lifecycle.md](specs/2026-07-29-prompt-to-ticket-lifecycle.md): Implementation spec: prompt-to-ticket lifecycle *(status: active)*
- [specs/2026-07-29-trace-model-sacred-timeline.md](specs/2026-07-29-trace-model-sacred-timeline.md): Trace model: worldlines, cones, and one canonical branch *(status not declared)*
- [specs/2026-07-30-data-architecture-and-orchestration.md](specs/2026-07-30-data-architecture-and-orchestration.md): Data architecture and orchestration: what SQLite is for, what git is for, and what shape the DAG actually is *(status: PROPOSAL, pending operator approva)*
- [specs/2026-07-31-agentic-directory-standard-sota.md](specs/2026-07-31-agentic-directory-standard-sota.md): SOTA Agentic Repository Directory Standard & Estate Enhancement Plan *(status: SPECIFICATION & ARCHITECTURAL COMP)*
- [specs/2026-07-31-github-native-project-surface.md](specs/2026-07-31-github-native-project-surface.md): GitHub-native project surface for ShovalBenjer/claude-setup and Zion (project 3) *(status: DESIGN)*
- [specs/2026-07-31-kanban-four-layer-model.md](specs/2026-07-31-kanban-four-layer-model.md): The four-layer board, fitted to claude-setup *(status: DESIGN)*
- [specs/2026-07-31-project-federation.md](specs/2026-07-31-project-federation.md): Per-repo project federation for the ShovalBenjer estate, and why it is not built *(status not declared)*
- [specs/2026-07-31-research-corpus-and-cache.md](specs/2026-07-31-research-corpus-and-cache.md): Research corpus and cache (row-reuse, cache2action) *(status not declared)*
- [specs/2026-07-31-zion-board-as-product-instrument.md](specs/2026-07-31-zion-board-as-product-instrument.md): Zion as a product instrument, not a task list *(status: active)*

## Analysis (point-in-time, inputs to TODO, never a decision)

- [analysis/2026-07-23-local-model-stress-test.md](analysis/2026-07-23-local-model-stress-test.md): Local model stress test: 2026-07-23 *(status not declared)*
- [analysis/2026-07-24-creativity-wow-gap.md](analysis/2026-07-24-creativity-wow-gap.md): Creativity / wow / deliberation-texture gap analysis *(status not declared)*
- [analysis/2026-07-24-deployment-gap-audit.md](analysis/2026-07-24-deployment-gap-audit.md): Deployment gap audit: claimed setup vs live harness, 2026-07-24 *(status not declared)*
- [analysis/2026-07-24-fleet-verification-gap.md](analysis/2026-07-24-fleet-verification-gap.md): Why the reference Opus 5 run shipped a game and this setup ships documents *(status not declared)*
- [analysis/2026-07-24-reference-repos-excavation.md](analysis/2026-07-24-reference-repos-excavation.md): Excavation: two WhatsApp-saved repos (amirfish1/claude-command-center, Master0fFate/just-my-skills) *(status: point-in-time scan, per docs-contr)*
- [analysis/2026-07-24-research-wiring-audit.md](analysis/2026-07-24-research-wiring-audit.md): Research-wiring audit + AUTO-17 pipeline design: 2026-07-24 *(status not declared)*
- [analysis/2026-07-24-setup-holding-us-back.md](analysis/2026-07-24-setup-holding-us-back.md): Is the setup holding us back? Synthesis of 5 audit lanes, 2026-07-24 *(status not declared)*
- [analysis/2026-07-24-skills-wiring-audit.md](analysis/2026-07-24-skills-wiring-audit.md): Skills-estate wiring audit: 2026-07-24 *(status not declared)*
- [analysis/2026-07-24-work-archive-import.md](analysis/2026-07-24-work-archive-import.md): Work-archive import: full sync of the work Claude setup (2026-07-24) *(status not declared)*
- [analysis/2026-07-25-claude-mastery-audit.md](analysis/2026-07-25-claude-mastery-audit.md): Claude Code Mastery, Evidence, and Learning-Corpus Audit *(status not declared)*
- [analysis/2026-07-25-claude-mastery-research-prompt.md](analysis/2026-07-25-claude-mastery-research-prompt.md): Claude Code mastery research prompt *(status not declared)*
- [analysis/2026-07-25-cloudflare-fit.md](analysis/2026-07-25-cloudflare-fit.md): Cloudflare fit audit: 2026-07-25 *(status not declared)*
- [analysis/2026-07-25-dynamic-setup-decisions.md](analysis/2026-07-25-dynamic-setup-decisions.md): Dynamic setup decisions: workflows, effort, thinking, cross-model, resources *(status: decision document, not a spec)*
- [analysis/2026-07-25-effort-and-thinking.md](analysis/2026-07-25-effort-and-thinking.md): Effort/thinking config audit: v2.1.219 binary evidence *(status: active)*
- [analysis/2026-07-25-free-tier-exploitables.md](analysis/2026-07-25-free-tier-exploitables.md): Free-tier exploitables: what closes the five open problems, 2026-07-25 *(status not declared)*
- [analysis/2026-07-25-other-resources.md](analysis/2026-07-25-other-resources.md): Other resources that can close the named weak points: 2026-07-25 *(status not declared)*
- [analysis/2026-07-25-our-own-dolt.md](analysis/2026-07-25-our-own-dolt.md): Can we build our own Dolt, and would it overcome theirs *(status not declared)*
- [analysis/2026-07-25-repo-benchmark-and-star-forensics.md](analysis/2026-07-25-repo-benchmark-and-star-forensics.md): Three-way repo benchmark and star forensics *(status not declared)*
- [analysis/2026-07-26-session-handoff.md](analysis/2026-07-26-session-handoff.md): Session handoff, 2026-07-26 *(status not declared)*
- [analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md](analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md): What the compile-once research says about THIS harness *(status not declared)*
- [analysis/2026-07-29-albert-prior-art-verdict.md](analysis/2026-07-29-albert-prior-art-verdict.md): Albert: prior art for the whole repository, and not adoptable *(status not declared)*
- [analysis/2026-07-29-local-dependency-audit.md](analysis/2026-07-29-local-dependency-audit.md): Local dependency audit, 2026-07-29 *(status not declared)*
- [analysis/2026-07-29-long-context-kernel-critique-response.md](analysis/2026-07-29-long-context-kernel-critique-response.md): The long-context kernel critique, tested against this repo's ledgers *(status not declared)*
- [analysis/2026-07-29-session-retro-modes-models-workflows-observability.md](analysis/2026-07-29-session-retro-modes-models-workflows-observability.md): Session retro, 2026-07-29 (lane B): modes, models, workflows, interruption, observability *(status not declared)*
- [analysis/2026-07-29-where-our-system-stands.md](analysis/2026-07-29-where-our-system-stands.md): Where our system stands against everything we researched *(status not declared)*
- [analysis/2026-07-30-context-engineering-and-the-absence-claim-class.md](analysis/2026-07-30-context-engineering-and-the-absence-claim-class.md): Context engineering, three absence claims in one session, and what /context showed *(status not declared)*
- [analysis/2026-07-30-github-repo-triage.md](analysis/2026-07-30-github-repo-triage.md): Saved GitHub repositories: first triage, and what it blocks *(status not declared)*
- [analysis/2026-07-30-native-surface-audit.md](analysis/2026-07-30-native-surface-audit.md): Claude Code native surface: what we wire, what we leave on the floor *(status not declared)*
- [analysis/2026-07-30-point-in-time-reconstruction.md](analysis/2026-07-30-point-in-time-reconstruction.md): Point-in-time reconstruction: what git already answers, and the narrow strip it does not *(status not declared)*
- [analysis/2026-07-30-self-chat-absorption-batch.md](analysis/2026-07-30-self-chat-absorption-batch.md): Self-chat absorption batch, 2026-07-30 *(status not declared)*
- [analysis/2026-07-31-density-gate-measurement.md](analysis/2026-07-31-density-gate-measurement.md): Density and variance: the measurement, and why no threshold was set *(status not declared)*
- [analysis/2026-07-31-the-green-test-gradient.md](analysis/2026-07-31-the-green-test-gradient.md): The green-test gradient, and two measurements of the bail-out path *(status not declared)*
- [analysis/reference/coherence-governor-AGENTS.md](analysis/reference/coherence-governor-AGENTS.md): Coherence Governor Agent *(status not declared)*

## Reflections (session postmortems)

- [reflections/2026-07-29-full-scope-and-slop-violation.md](reflections/2026-07-29-full-scope-and-slop-violation.md): Reflection: the full-scope claim and the ungated output channel *(status not declared)*
- [reflections/2026-07-29-what-is-going-wrong.md](reflections/2026-07-29-what-is-going-wrong.md): Reflection: why the research did not become the system *(status not declared)*
- [reflections/2026-07-30-analysis-that-never-becomes-code.md](reflections/2026-07-30-analysis-that-never-becomes-code.md): Reflection: analysis that never becomes code *(status not declared)*
- [reflections/2026-07-30-thesis-and-deck-review.md](reflections/2026-07-30-thesis-and-deck-review.md): Reflection: reviewing Yarin Beer's MSc thesis and its presentation deck *(status not declared)*
- [reflections/2026-07-30-what-i-saw.md](reflections/2026-07-30-what-i-saw.md): Reflection: everything I saw, including what I did not say at the time *(status not declared)*
- [reflections/2026-07-31-session-close-what-the-instruments-caught.md](reflections/2026-07-31-session-close-what-the-instruments-caught.md): Reflection: what the instruments caught, and what only the operator caught *(status not declared)*

## Handoffs (dated, between lanes and sessions)

- [2026-07-29-external-absorption-brief.md](2026-07-29-external-absorption-brief.md): External brief: absorb the saved-link corpus *(status not declared)*
- [HANDOFF-2026-07-27-research-transfer.md](HANDOFF-2026-07-27-research-transfer.md): Handoff: external research, and what it changes here *(status not declared)*
- [HANDOFF-2026-07-27-session-close.md](HANDOFF-2026-07-27-session-close.md): Session handoff, 2026-07-27 *(status not declared)*
- [HANDOFF-2026-07-29-absorption-session.md](HANDOFF-2026-07-29-absorption-session.md): Session handoff, 2026-07-29 evening, lane B *(status not declared)*
- [HANDOFF-2026-07-29-session-close.md](HANDOFF-2026-07-29-session-close.md): Session handoff, 2026-07-29, lane B *(status not declared)*
- [HANDOFF-2026-07-30-latent-channel-and-gastown.md](HANDOFF-2026-07-30-latent-channel-and-gastown.md): Handoff 2026-07-30: latent inter-agent channel, Gastown review loop, and two blockers *(status not declared)*
- [HANDOFF-2026-07-30-overnight-run.md](HANDOFF-2026-07-30-overnight-run.md): Handoff: overnight autonomous run, 2026-07-30 *(status not declared)*
- [HANDOFF-2026-07-30-session-close.md](HANDOFF-2026-07-30-session-close.md): Session handoff, 2026-07-29 into 2026-07-30, lane B *(status not declared)*
- [HANDOFF-2026-07-31-review-oracle-repair.md](HANDOFF-2026-07-31-review-oracle-repair.md): Handoff: review-domain oracle repair, and what the thesis job taught the harness *(status not declared)*
- [HANDOFF-2026-07-31-session-close.md](HANDOFF-2026-07-31-session-close.md): Handoff: WSL migration, review-oracle repair, and a duplicated launcher *(status not declared)*
- [HANDOFF-FROM-LEARNING-2026-07-27.md](HANDOFF-FROM-LEARNING-2026-07-27.md): Handoff to the Claude-setup session, from the learning-platform session *(status not declared)*
- [HANDOFF-FROM-LEARNING-2026-07-29.md](HANDOFF-FROM-LEARNING-2026-07-29.md): Handoff from the learning lane: discovery must watch organizations, not trending *(status not declared)*
- [HANDOFF-FROM-NEW-RECRUIT-2026-07-29.md](HANDOFF-FROM-NEW-RECRUIT-2026-07-29.md): Handoff: numerical stack preference was invisible to general sessions *(status not declared)*
- [HANDOFF-README-OWNERSHIP-2026-07-29.md](HANDOFF-README-OWNERSHIP-2026-07-29.md): Handoff to the resume engine: the GitHub profile README is yours to own *(status not declared)*
- [HANDOFF-TO-LEARNING-2026-07-27.md](HANDOFF-TO-LEARNING-2026-07-27.md): Handoff to the learning platform session, from the setup and resume session *(status not declared)*
- [HANDOFF-TO-LEARNING-2026-07-30-process-cost-and-boundaries.md](HANDOFF-TO-LEARNING-2026-07-30-process-cost-and-boundaries.md): Handoff to Lane C (learning): process cost, boundaries, and how to measure them *(status not declared)*

## Prior art

`prior-art/` holds one JSON record per component over 300 lines of Python, naming
what third-party tool could do its job. 39 records as of 2026-07-31, checked by
`python tools/map/codemap.py prior-art`. `prior-art/out-of-scope.txt` lists the
prefixes exempted and why.

## Operator input (pasted material, not authored here)

- [gemini-code-1785410845331.md](gemini-code-1785410845331.md): Refactoring the SOTA Agent Stack (July 2026) *(status not declared)*
- [gemini-code-1785455675294.md](gemini-code-1785455675294.md): MISSION SPECIFICATION: Build "nexus-engine-rs" *(status not declared)*
- [gemini-code-1785457549011.md](gemini-code-1785457549011.md): MISSION: BUILD A NEXT-GEN HYBRID RAG ENGINE (PAGEINDEX + LIGHTRAG + SPECULATIVE ROUTING) *(status not declared)*
- [gemini-code-1785458291930.md](gemini-code-1785458291930.md): gemini-code-1785458291930 *(status not declared)*
- [memory-layer--nexus-gemini-code-1785456331041.md](memory-layer--nexus-gemini-code-1785456331041.md): MISSION SPECIFICATION: Build "nexus-engine-rs" *(status not declared)*
- [prompt-research-effiefecnt-.md-files-gemini-code-1785450497712.md](prompt-research-effiefecnt-.md-files-gemini-code-1785450497712.md): Role & Purpose *(status not declared)*

## State (operational, ADR-0010 and ADR-0011)

- `../state/lessons.jsonl`: the lessons ledger, 42 rows.
- `../state/claims.jsonl`: lane claims, appended BEFORE work starts.
- `../state/claims-verify.jsonl`: 26 claims, each with a falsifier. Run `python tools/refute/refute.py run`.
- `../state/gate-runs.jsonl`, `../state/refutations.jsonl`: append-only verdict ledgers.
- `../state/bus.jsonl`: hash-chained cross-session bus. `python tools/bus/bus.py verify`.
- `../tools/selfimprove/proposals.jsonl`: ranked open work.

## TODO

- [../TODO.md](../TODO.md): the single ticket list, grouped by layer.
