# Milestone task plan, 2026-08-11

Status: active. Supersedes `2026-08-10-milestone-task-plan.md`. Re-derive before acting
if the date above is more than a week old.

Lane A. Branch `claude/project-planning-tasks-x6nifm`, PR #61.

## Measured state

| what | measured |
|---|---|
| gate verdict | **PASS** at `c776b63`, tree `5fb6ea53` |
| contract domains | 16 (3 N/A, 1 WAIVED) |
| waivers live | 1 (`skills`, expiring **2026-08-12**, DRIFT: 16) |
| open issues | 37 (33 are Zion epics with 184 checklist items, 5 checked) |
| open PRs | 6 (5 draft, 1 ready for review) |
| mutation specs | 4 complete (gate, refute, codemap, skills_sync), 0 survivors |
| AUTO acceptance | 5/20 (3 DONE, 2 POLICY-SET, 2 PARTIAL, 1 STAGED, 2 BLOCKED, 10 TODO) |
| prior-art records | 41, earliest expiry 2026-09-07 |

## Operator decisions needed (9)

1. **Rotate ElevenLabs key** exposed in commit `e695af5` (cannot be done by agent)
2. **Skills waiver**: measure drift from your machine today (expires Aug 12)
3. **PR #42** (boundary persona): merge or close? Ready for review, 6 days old
4. **4 stale draft PRs** (#47, #52, #53, #60): keep, rebase, or close each?
5. **Three-tree question**: should skills_sync read `dot-agents/skills` too?
6. **Archive `dot-agents`, `dot-codex`**, or keep?
7. **AUTO-10**: provide `GEMINI_API_KEY` secret for two-model review
8. **AUTO-05**: concierge session architecture (phone RC routing)
9. **AUTO-18**: Task Scheduler setup for laptop-sleep survival

## PR triage

Merge order recommendation: #61 first (clean), then #53, #60, #42, #52, #47 last.

| PR | Title | Status | Diff | Age | Call |
|---|---|---|---|---|---|
| #61 | Milestone plan + mutation spec + refute CI | clean | +7.5k/-5.4k | 1d | undraft |
| #53 | Corpus extractor + host-shape fix | draft | +815/-27 | 5d | rebase |
| #60 | Recover 10 days of dropped prompt text | draft | +11k/-116 | 1d | rebase |
| #42 | Boundary persona | CI fail (review) | +10k/-5.4k | 6d | rebase+fix |
| #52 | Chrome WSL-to-Windows bridge | draft | +653/-4 | 5d | rebase |
| #47 | Skill deps filter | blocked (hookgate) | +4.5k/-11.5k | 5d | operator |

**Hookgate overlap**: PRs #47, #53, and #61 all independently fix hookgate drift.
Whichever merges first causes conflicts in the others.

## M0: Unmerged Work & Secret Rotation

Six branches carry finished work. Merging them changes what every later milestone says.

- [ ] Rotate ElevenLabs API key (pushed in `e695af5`, operator only)
- [ ] PR #42 — boundary persona, ready for review, 6 days old
- [ ] PR #61 — this branch, undraft to get CI
- [ ] PR #60 — prompt backfill, recovers 10 days of data
- [ ] PR #53 — corpus extractor, exposed host-shape bug
- [ ] PR #47 — skill deps filter, blocked on operator hookgate decision
- [ ] PR #52 — chrome bridge, depends on WSL migration (#9)

## M1: Gate Integrity & Contract Completeness (P0)

Gate passes but relies on one waiver expiring tomorrow and three N/A domains.

- [x] #4 — Gate & fingerprint integrity (16 domains, 4 mutation specs, 0 survivors)
- [x] #49 — Falsifier layer (5 claims refuted, broken verifiers = 0)
- [ ] Skills waiver (DRIFT: 16) — measure from operator machine, decide renew/resolve
- [ ] #10 — Commit at-risk work, settle absorption verdicts (41 records, 0 reviewed)
- [ ] #50 — Bind instruments to a ratchet
- [ ] #28 — Waiver reasons must name the mechanism their falsifier tests

## M2: Verification Infrastructure (P1)

Tools and oracles that are incomplete or not yet measuring what they should.

- [ ] #20 — Gate in CI (ship-gate.yml live, review job intermittent, nightly wired)
- [ ] #5 — Reconcile contradictions the repo states about itself
- [ ] #6 — Dead pointers, stubs, repo-vs-live drift
- [ ] #34 — Adopt ast-grep
- [ ] #32 — Fix data structures and interfaces
- [ ] #31 — Record where the plan was refuted
- [ ] #27 — Prose gate measures the ruled form
- [ ] #25 — Supply-chain verification

## M3: Native Surfaces & Ecosystem (P1-P2)

Wiring subscription features and the autonomy ecosystem.

- [ ] #12 — Wire Claude Code native surface
- [ ] #16 — Run one workflow under routing rules
- [ ] #22 — Autonomy ecosystem backlog (AUTO-01..20)
- [ ] #11 — Licensing & privacy blockers (blocked-operator)
- [ ] #15 — Kilo Code integration (blocked-operator)
- [ ] #14 — Persona review economy
- [ ] #13 — Replace agent bridge with ACP

## M4: Scale, Polish & Research (P2-P3)

Repo hygiene, design foundations, research transfer.

- [ ] #8 — Shrink 1682 tracked files to under 600
- [ ] #35 — Repo clear, enforced standard
- [ ] #29 — Review work recomputes its own numbers
- [ ] #26 — Point-in-time reconstruction
- [ ] #23 — Research transfer, five findings owed
- [ ] #33 — Run artifact through measurement function
- [ ] #17 — Design foundations
- [ ] #7 — Phase D reclamation
- [ ] #21 — GitHub repo standards maintained by agent
- [ ] #9 — WSL2 migration
- [ ] #24 — RTK adoption
- [ ] #19 — Absorb open-design and OpenGame
- [ ] #18 — The Construct v4

## Standalone issues (not in epics)

- [ ] #58 — Two lane sessions shared one checkout
- [ ] #57 — flow.py calls working control dead
- [ ] #56 — Lane D: the-bench genre mismatch
- [ ] #38 — Agent feed: derived cross-repo telemetry

## Orchestration

Per operator decision 2026-08-11:

- **claude-setup Projects board** (to create) — milestones M0-M4, 37 issues + 6 PRs
- **claude-setup Discussions** (to create) — ADRs, operator questions, cross-lane coordination
- **Zion** (exists) — global cross-repo orchestration
- **Cloud agents**: new-recruit stays lane B, daily-learning stays lane C, both grounded
  against claude-setup specs but working their own scope
