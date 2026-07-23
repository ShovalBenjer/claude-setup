# Claude OS — Execution Plan

Sequenced build plan. Points to the spine (CLAUDE-OS.md), PRD (acceptance rows),
and ADRs; this file is the ORDER OF WORK with definition-of-done per item and
explicit blockers. Updated as items land.

## Phase 0 — Operator unblocks (documented; you do these when at the machine)
See docs/OPERATOR-RUNBOOK.md. These gate Phase 2.
- [ ] OAuth token authorized + secret on 22 repos (unblocks review fabric)
- [ ] `codex` CLI installed (unblocks the 2nd reviewer / agreement gate)
- [ ] `rtk` on PATH (unblocks token-efficiency guard) — optional
- [ ] Decisions: model default, key rotation, PR repo list, WhatsApp cadence

## Phase 1 — Buildable NOW (no token / codex / decisions). THIS PHASE.
Highest leverage first. Each is on hardware owned, verifiable this session.
- [ ] **P1.1 SessionStart recall (Windows)** — inject MEMORY.md digest + open TODO
  + candidate skills at session start. DoD: hook deployed + wired + pipe-tested,
  emits valid additionalContext. (gap-analysis Tier-0, no deps.)
- [ ] **P1.2 Reflex router + flywheel S1** — route_classify.py -> logged cheap-first
  classifier; every decision appended to a flywheel log (route, risk, text-hash),
  PII-safe. DoD: module + logger run, log grows, risk tag available. (SLM spec #2 + flywheel S1.)
- [ ] **P1.3 Memory + web write pipe** — query -> WebSearch -> distill -> typed
  memory card written to the auto-memory dir. DoD: run produces a real card. (#14)
- [ ] **P1.4 Blast-radius graph** — intra-repo import/call graph; a diff reports
  modules touched. DoD: runs on one repo, emits graph + touched-modules for a diff. (#16)
- [ ] **P1.5 Slop gate as a command** — /slop wraps slop_lint over changed prose.
  DoD: invocable, flags real hits. (kernel rule 7; slop_lint already built.)

## Phase 2 — Review fabric (needs Phase 0: token + codex)
- [ ] Live two-Claudes review on a fresh seeded PR (seed data for personas)
- [ ] a2a agreement gate: Claude + Codex independent, agreement -> gh pr review +
  provenance + audit.jsonl (ADR-0004)
- [ ] Persona review economy: contracts, reputation from external truth, Thompson
  allocation, PIP/fire/recruit (spec 2026-07-23-persona-review-economy, ADR-0008)

## Phase 3 — I/O, learning, frontier
- [ ] WhatsApp copilot: triage digest + style drafts + coaching (needs automation
  Chrome relaunched — was closed in the RAM clean) (#9)
- [ ] Learning-card emitter -> הסדנה queue (#10)
- [ ] Flywheel S2-S6: PII-strip -> cluster -> LoRA specialist -> eval -> promote
  (rented GPU per ADR-0009) (SLM spec #3)
- [ ] Daily digest headless via Task Scheduler (runbook §5)

## Phase 4 — Continuous / self-improving
- [ ] Weekly self-improvement loop (#13); branch-health sweep on cron (#17)
- [ ] Repo portfolio graph refresh + routing use (#15); rules-as-enforcement (#18)
- [ ] Scheduler consolidation; WSL systemd retired (#11); concierge phone (#20)

## Sequencing logic
Phase 1 needs nothing external -> do it now, fully. Phase 2 is gated on two 5-minute
operator actions (token + codex) -> the moment those land, it unblocks the highest-
value spine (the two-Claudes review + persona economy). Phase 3/4 layer on top.
Depth rule: each item looped to its DoD (evidence + coverage), not patched-and-reported.
