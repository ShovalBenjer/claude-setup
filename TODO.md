# TODO: Claude OS - Roadmap

This file is the **roadmap**, not a task tracker. Closed items were archived to
`docs/archive/2026-08-24-todo-done-archive.md` (see `docs/archive/MIGRATION-NOTES.md`).
Fresh session? Read `docs/SESSION-BOOT.md` first, then `docs/PLAN-SPINE.md` (the one page
connecting PRD → spec → current/next slice → ticket → % built, across harness-gate,
autonomy/AUTO, dashboard/DASH, voice/VOICE, interpretability/Modal, persona-economy,
intent-lifecycle, slm-swarm, and kanban).

The roadmap is derived from the research corpus (`work-docs/research/`), especially the
2026-07-07 gap analysis ("prose is not enforcement") and the 2026-07-08 global/per-project
suggestions. Strategic objectives exist because the research named them; key results are the
load-bearing outcomes; the initiative tracker is the active work; the risk log is what the
research and the file-by-file sweeps showed is still unverified.

---

## 1. Strategic Objectives

| # | Objective | Source | North star |
|---|---|---|---|
| SO-1 | Make every stated claim enforceable by something that runs | gap-analysis (root finding) | Zero "prose-only" rails; every rule bound to a hook/CI |
| SO-2 | Close the memory read-back half of the loop | gap-analysis G1, context-engineering | SessionStart recall injects digest + candidate skills on every session |
| SO-3 | Enforce contracts as gates, not comments | 2026-07-08 G2 | `allowed-tools` on sensitive skills; completion without proof is blocked |
| SO-4 | Stand up a real eval gate | gap-analysis G4, 2026-07-08 G4 | promptfoo + DeepEval pre-push; block on regression; Inspect AI for agent SUT |
| SO-5 | Run a weekly self-improvement loop | gap-analysis G1, 2026-07-08 G1 | Codex-run job proposes router/skill/persona diffs; human approves |
| SO-6 | Auto-route personas like skills | 2026-07-08 G3 | prompt-router injects owning persona per task |
| SO-7 | Move recurring workflows onto a typed SDK | 2026-07-08 G5 | claude-agent-sdk-python for audit/eval/self-improve with tracing |
| SO-8 | Harden the reviewer economy | persona-review-economy spec | reputation from external truth; Thompson-sampled routing |
| SO-9 | Temporal, superseding memory | graphiti pattern (2026-07-08) | decisions/findings superseded, not silently stale |
| SO-10 | Ship rules as portable SKILL.md | superpowers/anthropics-skills (2026-07-08) | gastown personas run unmodified from Codex CLI |

---

## 2. Key Results

Annual arc; each KR ties to a row in `CLAUDE-OS.md` §9 (Acceptance).

| KR | Target | Linked objective | Status |
|---|---|---|---|
| KR-1 | Docs control plane live on every repo (ONE TODO, ONE INDEX, generated DOCMAP) | SO-1 | in progress |
| KR-2 | Deep Work Protocol hooks live (spec-anchor, handoff, slop gate, postconditions) | SO-1, SO-3 | partial |
| KR-3 | SessionStart recall wired on Windows | SO-2 | partial (deployed, Windows-native pending) |
| KR-4 | PR fabric posts agreement-gated reviews with provenance + audit | SO-4, SO-8 | TODO |
| KR-5 | Weekly self-improvement loop running and proposing diffs | SO-5 | TODO |
| KR-6 | Skills estate fully owned/merged/archived (unwired = defect) | SO-1 | TODO |
| KR-7 | Daily digest push live from cron (needs always-on) | SO-2 | partial (generator + cron built) |
| KR-8 | WhatsApp copilot: triage + style drafts + coaching | - | scope granted, TODO |
| KR-9 | Learning-card emitter → הסדנה queue | - | TODO |
| KR-10 | Scheduler topology consolidated; WSL systemd retired | - | TODO |

---

## 3. Initiative Tracker

Active work, grouped by lane (`docs/charters.md`). "Lane" = harness work unless noted.

### Harness / gate (lane A)
- **Truth & hygiene (L1/L7).** Rotate the exposed API key (operator; NOT reproduced - CDP
  probe found 0 credential-shaped strings, does not clear it). Purge WSL-era `/cdp` paths,
  reground docs. Catch PRD/ADR text up to reality (#4 done, #8 partial, ADR-0007 Codex-out).
- **Deep Work Protocol hooks (L0).** Remaining: handoff-on-stop, postcondition metadata (#5);
  RTK bash guard (blocked: `rtk` binary missing on Windows); daily digest push from cron (#6,
  needs always-on Task Scheduler).
- **Review fabric (L5).** Wire second model (free Gemini) → a2a-gemini bridge + gemini-review
  workflow; agreement-gated a2a⇄GitHub review + provenance + audit (#8); persona review
  economy build (#19).
- **Continuous.** Repo portfolio graph (#15) + blast-radius graph (#16); git branch health
  sweep (#17); rules-as-enforcement per repo (#18); skills estate owned/merged/archived (#12);
  weekly self-improvement loop (#13).
- **Filed 2026-07-29/31.** Stack-lint oracle (stack preferences → mechanical checks),
  lane-enforcement Stop-gate check, waiver-falsifier execution (gate.py runs the command a
  waiver names).

### Autonomy Ecosystem (AUTO, lane B)
- ADRs 0010–0015 + PRD + spec + charters seeded. Hook fire-proof (AUTO-01/02 closed).
  Compaction churn resolved 2026-07-29. Remaining: full autonomy slice, persona routing,
  contract enforcement on the autonomy path.

### Dashboard / multi-session (DASH, new)
- Evaluate adopting `amirfish1/claude-command-center` (MIT) as the missing session-dashboard
  layer (Kanban, spawn/resume, cost, cross-session). Excavate-before-building: do NOT rebuild.

### Orchestration (L3)
- Scheduler consolidation; WSL systemd retired (#11); standing personas; concierge phone
  topology (#20).

### I/O & frontier (L2/L4/L8)
- WhatsApp copilot (#9); learning-card emitter → הסדנה (#10); memory + web write pipe (#14);
  latent/vector channel readiness; closed-loop recalibration.

### Research transfer (RT) & external absorption (ABSORB/EXT)
- Close the research-to-repo work map; evaluate external SOTA named in
  `work-docs/research/2026-07-08-trending-agent-repos.md` as learn-from, not adopt-wholesale.

---

## 4. Risk Log

Risks the research and the file-by-file sweeps showed are still open. Severity reflects blast
radius, not effort.

| ID | Risk | Severity | Evidence | Mitigation |
|---|---|---|---|---|
| R-1 | A secret reached a pushed commit; only the operator can finish removal | HIGH | `docs/analysis/2026-08-10-inbox-secret-exposure.md`; value in `e695af5` on `gh/main` history | Rotate the key (works whatever git does); history rewrite denied to assistant on purpose |
| R-2 | CI has been red on every run and nothing said so | HIGH (historical) | `gh run list`: 4 Ship gate runs, all failure; `gate` job missing pytest dep | Fixed by adding pytest to the step; UNVERIFIED until a green run on the runner |
| R-3 | 90 of 96 open TODO items invisible at session boot | MED | TODO sweep 2026-08-01 | This roadmap + `docs/SESSION-BOOT.md` surface the live set |
| R-4 | Prose-not-enforcement: 12 of 13 test layers had zero executing enforcement | HIGH | gap-analysis root finding | Every new rule bound to a hook/CI (SO-1) |
| R-5 | Memory write-only, never read back at session start | MED | gap-analysis second root finding | SessionStart recall (SO-2) |
| R-6 | Skills oracle reads one of three trees, reports the other two as drift | MED | TODO FOG section | `skills_sync.py check` truthfully reports; drift measured both directions |
| R-7 | Nothing enforces the coding-style standard on `tools/` | MED | TODO FOG section | Stack-lint oracle initiative |
| R-8 | Mutation control red on `bus.py`; survivors were the lock | HIGH (closed) | `mutate.py --spec all` 2 survived; structural fix landed (23/23 caught) | `bus.py selftest` parses `__file__`; `tests/test_bus_lock.py` pins it; Windows CI leg still the only true behavioral test |
| R-9 | Zion board throughput zero (31 epics, 0 closed) | LOW | TODO FOG section | Decide whether epic-only board is the used surface |
| R-10 | Unverified items depend on operator blocks (model keys, scheduling) | MED | open-model + scheduling plan waits on 5 operator blocks (A–E) | Surface as blockers; do not silently mark done |

**Standing invariant:** a local gate PASS is not evidence about the CI runner. The gate must
be green on the merged tree (`dot-codex/rules/production-means-merged-and-smoked.md`).
