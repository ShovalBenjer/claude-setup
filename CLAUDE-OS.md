# CLAUDE OS - Single Source of Truth

Status: ACTIVE (living document, the spine). Date: 2026-08-24.
Owner: Shoval Benjer. Maintainer: the Claude-setup session.
Repo: `github.com/ShovalBenjer/claude-setup` - canonical home of the OS; `dot-claude/`,
`dot-codex/`, `dot-agents/` are the deployable payload.

This file MERGES and SUPERSEDES every prior setup plan. Predecessors remain as history only.
`CONTRIBUTING.md` is the contributor entry point; `README.md` is the public overview; this
file is the spine. `docs/INDEX.md` is the curated reading order.

The one sentence that explains every rule below: **prose is not enforcement.** The 2026-07-07
gap analysis (`work-docs/research/2026-07-07-claude-setup-gap-analysis.md`) found the OS named
its own best practices in `CLAUDE.md` and skills prose while 12 of 13 test layers had zero
executing enforcement. The fix is never "add more prose" - it is "wire the prose to a hook."

---

## 1. Mission

A personal Claude Operating System: everything Shoval captures (WhatsApp, docs, specs,
prompts) becomes gated, evidenced action across his ventures, with Shoval reduced to an
approval surface, running on the Claude subscription at near-zero marginal cost.

Three client ventures (each its own session/repo; the OS serves all):
1. **Hiring machine** (new-recruit) - P(hire) optimization.
2. **Learning platform** (הסדנה / daily-deep-learning) - closing the gap between building
   AI-natively and actually knowing it.
3. **The OS itself** (this repo) - rails, gates, review fabric, notification fabric.

---

## 2. Project structure

Four conceptual areas; every path below is payload or verification instrument, never a
running app.

| Area | Paths | Role |
|---|---|---|
| **Harness** | `tools/`, `tests/`, `quality-contract.json` | The oracles, gates, schedulers, review fabric that verify the OS. `AGENTS.md` is the harness spine. |
| **Dotfiles** | `dot-claude/`, `dot-codex/`, `dot-agents/` | The deployable config payload (committed copy of `~/.claude`/`~/.codex`). Editing here changes nothing until deployed. |
| **Research** | `research-papers/`, `work-docs/research/` | The corpus that shapes the rules. Docs must cite and align with it. |
| **Work / control plane** | `docs/` (prd/spec/adr/analysis/INDEX/TODO), `state/` (ledgers), `intent-control-plane/`, `nexus-engine-rs/`, `dashboard/` | Where decisions are recorded and work is tracked. Docs are the control plane. |

The `docs` control plane mandates: prd/ spec/ adr/ analysis/ as doc types, ONE `TODO.md`, ONE
`docs/INDEX.md`, and `docs/DOCMAP.md` generated (never hand-edited). See `docs/doc-status.txt`
for the residue registry.

---

## 3. The Layers

### L0 - SDLC Kernel (the operating discipline; under everything)

- **Intent contract first.** Substantive task → first artifact is an acceptance checklist
  extracted from plan/context (task bus). Judged against THAT.
- **Loop, don't hand back.** Workflows with a separate adversarial done-verifier
  (refute-by-default). Full budget; speed is only a virtue on explicit quick fixes.
- **Done has a format.** Verification evidence (command + output) + intent-coverage statement.
  No coverage table = not done.
- **State machine legality:** no GENERATED→SHIPPED without JUDGED+VERIFIED; no close without
  evidence; zero-opacity content is killed, never softened. Enforced in hooks, not prose.
- **Confidence gates:** ≥0.90 autonomous; 0.70–0.90 work + explicit proof gate; <0.70 ask or
  spawn reviewer.

### L1 - Governance & Identity
- One reconciliation ADR series. Codex = independent reviewer only; model policy enforced in
  settings.
- Secrets: `.env`/credentials never read/echoed/committed; PII never enters embedding indexes.
- Cost: subscription-window backoff on cron fleets; metered APIs get a hard monthly cap.
- **Capability honesty matrix:** the OS maintains a table of what each rail actually verifies
  vs claims. Stub functions and always-pass checks are defects by definition.

### L2 - Memory, Continuity & Comms Copilot
- **Task bus as spine**: all sessions read/write tasks with owner + evidence + deps.
- SessionStart recall rewired to inject intent digest + candidate skills.
- Intent ledger (`~/.intent/`): capture prompts as SDLC artifacts.
- **WhatsApp communications copilot:** read groups + 1:1s, triage digest, drafted replies in
  Shoval's voice. Draft-only - the send path is deliberately unbuilt.

### L3 - Orchestration
- One scheduler topology: native local cron + cloud routines; WSL systemd retired.
- Standing personas with real cadence.
- Subagent admission criteria: spawn only when parallel/risky/specialist/context-isolating;
  default 0, max 4; every spawn gets fresh context + budget + output contract.
- Hive bead bus retained where multi-session work needs atomic claim/close.

### L4 - I/O
- Inbound: WhatsApp copilot, Gmail via gws, GitHub/ADO events, phone RC voice.
- Outbound: **one daily digest push** + immediate push for P0. Push-beats-pull.
- Outward posts (Jira, LinkedIn, email, PR comments beyond agreement gate) are drafted, never
  auto-sent.
- One owner process for automation Chrome; phases serialize through the task bus.

### L5 - Quality Fabric
- **a2a ⇄ GitHub PR review sync**: two independent reviews → agreement gate → provenance.
- The fabric reviews the OS's own changes (dogfooding).
- Eval gates (promptfoo/deepeval) non-blocking until trusted; deterministic checks always
  before LLM judges.
- Weekly self-improvement loop; skills estate owned per persona (unwired = defect).
- **Validity discipline:** any scorer needs ground-truth calibration or is labeled a heuristic.

### L6 - Project Portfolio
- Registry: every repo → owner persona, standards score, deploy story, docs compliance.
- GitHub claim-consistency is a standing weekly invariant.
- Docs control plane applies to every repo incl. this one.

### L7 - Platform & Machine
- Windows-first purge; TUI hardening; always-on-PC health for the daemon; SQLite everywhere
  with WAL.

### L8 - Frontier
- mojuco (adversarial sim-verify) and artifixer (opacity-masked generation) as OS-wide
  patterns.
- Learning-card emitter bridging AI-native building to mastery.
- Agent contracts + reputation; closed-loop recalibration; claims ledger discipline - every
  load-bearing claim maps to an enforcing test.

---

## 4. Deep Work Protocol (the answer to "partial and shallow")

Grounded in the July-2026 literature sweep (METR time-horizons; arXiv 2509.09677
self-conditioning; ACL 2026 "Illusion of Insight"; debate-martingale results; LLM
homogenization/"AI slop" studies; Verbalized Sampling 2510.01171; Antislop ICLR 2026; MAST
NeurIPS 2025; Anthropic long-running-harness + context-engineering posts). Four findings drive
everything: (1) long-task failure is EXECUTION failure - a model seeing its own errors errs
more; (2) visible self-reflection is mostly theater - only external checks deepen output; (3)
same-context ensembles/debate cannot exceed their correlated-error floor - value requires
information asymmetry; (4) homogenization is measured and prompt-resistant - organic feel
requires distribution-eliciting generation + human taste + slop gates.

The protocol - every rule has a native mechanism and a stick:

| # | Rule | Native mechanism | Sticks via |
|---|---|---|---|
| 1 | Spec-as-spine: no substantive build without spec + acceptance table | Plan mode → prd; UserPromptSubmit hook injects active-spec | hook + docs-control-plane rule |
| 2 | Fresh-context resumption: never continue polluted context | Stop/PreCompact hook writes handoff | hook file + progress artifacts |
| 3 | External verifiers at every boundary | PostToolUse test hooks; `/verify`, `/run` | hooks + production-means-smoked rule |
| 4 | HTN-lite: every subgoal carries a postcondition + check command | Plan-mode template; task metadata `postcondition` | task-bus convention |
| 5 | Wide-then-curate for taste | AskUserQuestion previews; `docs/taste.md` | creative-brief skill |
| 6 | Defixation: forbid the obvious solution first | creative-brief skill | skill + memory rule |
| 7 | Slop lint as a GATE on prose | Stop-hook / review pass | hook, not suggestion |
| 8 | Fanout for breadth with information asymmetry | Agent tool + Workflow; `/model [1m]` | hive-mind rule + L3 criteria |
| 9 | Typed memory: decisions / episodes / procedures / taste | auto-memory dir; curator cron | memory taxonomy |
| 10 | Compaction never decides what survives | PreCompact hook | hook file |
| 11 | Long horizon = the LOOP, not the session | CronCreate / /schedule | cron jobs + artifacts |
| 12 | Aspect-split verification: parallel single-aspect verifiers | Workflow pipeline templates | workflows in repo |

Cross-cutting: depth is ENFORCED by structure, never REQUESTED from the model. A "please think
deeply" prompt is the canonical anti-pattern.

---

## 5. Development workflow

Followed by every contributor (see `CONTRIBUTING.md` for full detail).

1. **Boot.** `docs/SESSION-BOOT.md`: name your lane from `docs/charters.md`, append a claim
   row to `state/claims.jsonl`. Ground truth is git + `state/`, never a doc.
2. **Branch.** `kebab-case`, intent-prefixed (`feat/`, `fix/`, `docs/`, `chore/`, `test/`,
   `refactor/`). Never work on `main`.
3. **Commit.** Conventional Commits (`<type>(<scope>): <subject>`, imperative, lowercase).
4. **Implement behind tests (TDD).** RED → GREEN → REFACTOR. No mock violations, no emojis.
   Every production bug gets a permanent regression test.
5. **Gate.** `python3 tools/gate/gate.py run --project . -v` must be green locally before
   push.
6. **Ship via PR gate only** (ADR-0012). Merge into `main` through the PR gate; no direct
   commits, no force-push.

Design decisions run `/diverge` first (charters rule 2).

---

## 6. CI/CD

`.github/workflows/ship-gate.yml` splits the contract across three jobs; its header comment
states exactly what each job covers. The `pipeline` domain greps the workflow files for a
literal `gate.py run` invocation - do not rename it there without updating the domain.

Tiered enforcement (from `dot-codex/rules/tdd-enforcement.md`):

- **Tier 1 - every commit (<5s):** linter 0 errors, formatter 0 violations, type check 0
  errors, unit tests pass, property/invariant tests pass.
- **Tier 2 - every PR (<2m):** all Tier 1 + integration + regression + coverage floor.
- **Tier 3 - nightly:** fuzz, mutation (target >80%), performance baselines, chaos.
- **Tier 4 - pre-release:** full regression, load, security scan.

"Production" = **merged to `main` and smoke-tested**
(`dot-codex/rules/production-means-merged-and-smoked.md`). A local PASS is not evidence about
the CI runner - the gate must be green on the merged tree.

---

## 7. Conventions (binding rules)

These `dot-codex/rules/` are binding, not advisory:

- **no-emojis** - no emojis in code, comments, commits, docs, tests, reports. Exception only
  on explicit user request.
- **no-mocks** - no mocking services/DBs/FS/network. Use real in-memory components, recorded
  VCR/nock cassettes from real APIs, or platform stubs only.
- **tdd-enforcement** - RED→GREEN→REFACTOR; every PR includes tests; every bug gets a
  regression test; no mock violations.
- **docs-control-plane** - prd/spec/adr/analysis taxonomy; ONE `TODO.md`, ONE `INDEX.md`;
  `DOCMAP.md` generated, never hand-edited.
- **production-means-merged-and-smoked** - merged + observed green on the runner.
- **boundary-contracts** - every module boundary declares its contract explicitly.
- **read-whole-before-reasoning** - read entire files before reasoning about them.

Prose is gated by `tools/slop_lint.py` (no emoji, no spaced em/en dash connectors, no banned
phrases, density/variance thresholds). A clean slop lint is not by itself evidence the content
is correct.

---

## 8. What makes it DYNAMIC (the reason it is an OS, not a script)

A script runs the same path every time. This is a **closed-loop control plane**: outcomes feed
back into how work is allocated, who does it, what the harness knows, and what the rules are.
Three feedback loops at three speeds:

- **Fast loop (per-task / per-PR): reputation + routing.** Every review/build updates an
  actor's reputation; allocation is Thompson sampling over actors. Signal must be EXTERNAL
  ground truth (ADR-0008); personas never rate personas.
- **Medium loop (weekly): self-improvement.** Reads what happened (skills fired vs never,
  hooks errored, intents without proof) and proposes diffs to rules/hooks/skills. Approved
  diffs mutate the harness. The system proposes, Shoval disposes (ADR-0005).
- **Slow loop (as-needed): hiring, PIP, firing, rule evolution.** A defect CLASS that keeps
  escaping recruits a specialist reviewer persona; decaying reputations get a PIP, then
  deactivation.

Four more axes: adaptive compute (effort/model/subagent scale to difficulty + confidence),
compounding memory (typed memory + taste corpus grow weekly), state-machine paths (next_state
= f(state, evidence, policy, budget, approval)), and an open intent surface (work enters from
anywhere; the router classifies + dispatches at runtime).

Maturity: core harness + tool orchestration high; memory, evaluation, observability, and the
dynamic loops are the build frontier.

---

## 9. Acceptance (PRD table)

| # | Criterion | Status |
|---|---|---|
| 1 | claude-setup repo = canonical, relocated, July state synced, pushed | done |
| 2 | Single source of truth (this file) supersedes all prior plans | this file |
| 3 | Notification fabric: phone push + desktop toast verified | DONE 2026-07-22 |
| 4 | Daily digest push live from cron | TODO |
| 5 | SessionStart recall injects digest + skills on Windows | TODO |
| 6 | PR fabric posts agreement-gated reviews with provenance + audit | TODO |
| 7 | SDLC kernel: checklist-first + done-verifier + coverage-format enforced by hooks | TODO |
| 8 | WhatsApp copilot: triage digest + style-matched drafts + coaching retro | TODO (scope granted) |
| 9 | Learning-card emitter feeding הסדנה queue | TODO |
| 10 | Scheduler topology consolidated; WSL systemd retired | TODO |
| 11 | Skills estate fully owned/merged/archived | TODO |
| 12 | Weekly self-improvement loop running | TODO |
| 13 | Always-fresh PR review workflow on every source repo | DONE 2026-07-23 |
| 14 | Deep Work Protocol hooks live (spec-anchor, handoff, slop gate, postconditions) | TODO |

---

## 10. Supersession table

| Predecessor | Disposition |
|---|---|
| CLAUDE-CODE-MASTER-PLAN-2026-05-03 (+ skills triage/scatter) | Superseded. Alive: dotfiles-repo idea, skill-pair merges, hook checklist. Dead: $HOME-worktree move, Seekapa phases, Kilocode conversion. |
| 2026-05-13 hive-adoption + 2026-05-17 systemd map | Superseded. Alive: bead bus semantics, evidence-to-close, TTL sweep. Dead: systemd timers, ADO webhooks. |
| 2026-06-14 agent-orchestration-rewire | Superseded. Alive: admission criteria, budget profiles, context packs. Dead: Codex-as-runtime. |
| 2026-06-25 local-intent-control-plane | Superseded as plan; intent ledger + authority order + confidence gates absorbed into L0/L2. |
| 2026-06-28 mojuco/artifixer | Superseded as plans; primitives absorbed into L0/L8. |
| 2026-07-07 gap analysis + 2026-07-08 suggestions | Absorbed (G1→L5 weekly loop, G2→L0 gates, G3→L2 recall/routing, G4→L5 eval gates). |
| 2026-07-09 harness-maturity-plan | Completed historically; shim discipline carried into L5. |
| Cowork session 2026-07-20 | Decision record only (local beats cloud-bridge for logged-in surfaces). |

---

## 11. Pending Shoval decisions

1. ~~Global default model change~~ CLOSED 2026-07-29: operator set `opus[1m]` directly.
2. API key in תזכורת לעצמי - rotate. Still unconfirmed since 2026-07-24 (CDP sweep found zero
   credential-shaped strings; deletion-from-view and wrong-chat look identical).
3. PR-fabric opt-in repo list.
4. WhatsApp copilot cadence (2x daily proposed) + coaching retro frequency.
