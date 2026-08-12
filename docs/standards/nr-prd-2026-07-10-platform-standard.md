---
prd: platform-standard
ticket: none (internal platform engineering)
status: active
owner: Shoval
created: 2026-07-10
reground: 2026-07-10 (6 read-only investigators, live tests + scorer + pipeline reads)
---

# PRD: Unified Platform Standard

The single living PRD for the platform work. One standard for every repo and the setup:
canonical structure, a six-dimension compliance score, mandatory AI-review gates, stage/prod
environments, Foundry-per-environment IaC, a Codex-first delegation flywheel, a sim-before-real
discipline, and a concurrent-session safety guard, with the intent-control-plane as the platform
brain. This table is the control plane; update the status column as work lands, do not spawn
dated notes. Every status below was re-verified against live state on 2026-07-10.

## Goal

Every repo is measurable and comparable on six dimensions, gaps become a verified delegation
queue that Codex (Haiku fallback) closes on stage branches behind a blocking, comment-resolved
review gate, destructive/git-hygiene ops are guarded against concurrent-session collision, and
the whole setup is one localizable, standardized system.

## Stop condition

Estate scorecard rises to target via verified work; Codex-review is a mandatory + comment-
resolved gate on the strongest repo; at least one repo has a real cost-efficient stage
environment; a concurrent-session guard blocks shared-repo writes when another session is live;
the intent-control-plane is git-versioned, packaged, and reliable.

## Acceptance table

Legend: done = verified live; partial = exists but below bar; specd = documented only, no
implementation; pending = not started / gated on approval.

| #   | Item | Status | Evidence (verified 2026-07-10) |
|-----|------|--------|--------------------------------|
| A1  | Canonical repo structure (3 classes) | done | `docs/canonical-repo-structure-2026-07-10.md` (product-service, harness, agentic-langgraph) |
| A2  | Six-dimension compliance scorer + scorecard | done | `intent_control_plane.standards`, `50 passed in 3.94s`, live 13-repo scorecard captured |
| A3  | Docs control-plane taxonomy (global rule) | done | `~/.claude/rules/docs-control-plane.md`, `grep -c` in CLAUDE.md = 1 |
| A4  | Project map (class, langgraph, azure, tests, CI) | done | `intent_control_plane.project_map`, live 13-repo map with gap detection |
| A5  | Control-tower TUI (first slice) | done | `intent_control_plane.dashboard`, reads 266 real a2a calls, fail_rate 0.289 |
| A6  | Mandatory Codex-review + comment-resolution gate | partial | `CodexReview` stage on `origin/master` fires every PR, posts resolvable threads, but `continueOnError: true` (advisory); comment-resolution `D*` unenforced per `CICD-SOTA-Pipeline-Audit-2026-07-06.md` |
| A7  | Stage environment (branch + Azure, cost-efficient) | specd | `stage` is a git branch only; one Function App `func-cs-agents-dev`, one RG `AZAI_group`, one ADO env `production`, no slot; push to `stage` deploys nothing |
| A8  | Foundry per-environment IaC (azd env + AVM Bicep) | specd | no azd env estate-wide; one lone `.bicepparam` (video-understanding); rule prose in `canonical-repo-structure` sec 2 |
| A9  | Wiki-as-code (docs/ published to ADO wiki, audit) | specd | rule item 5 in `docs-control-plane.md`; no pipeline configures "Publish code as wiki" |
| A10 | Delegation flywheel (Codex-first, Haiku fallback) | partial | `a2a-codex-call.sh` + `codex-review-on-push.sh` + `self-improve.py` real and working, `rate_limited` detected; Haiku-fallback half missing (ADR-0001 decision 3) |
| A11 | Mojuco sim2real, full ladder (deterministic pyramid, simulated user, calibrated rollout) | partial | T4.1/T4.3/T4.4/T4.7 pure cores WIRED + recorded via `intent eval` (`eval_cmds.py`, eval_results rows), 2026-07-11; T4.2/T4.5/T4.6/T4.8 still pending (need cs-agent scaffold / shared-HOME) |
| A12 | Local git hygiene (branch/worktree/root cleanup) | pending | HOME repo: 49 branches, 3 worktrees (1 prunable), 239 uncommitted; needs per-action OK |
| A13 | git-init the intent-control-plane package | done | commit `1e05912` on master, clean tree, 50 tests pass (was stale-pending) |
| A14 | Concurrent-session guard (pre-flight live-session check) | partial | logic + 24 tests done, commit `283803e`; defect: `_live_other_sessions` uses `pgrep -x claude` which misses node-based Claude Code, needs `pgrep -f` fix before wiring the hook |
| A15 | HOME de-anomaly (decouple $HOME from cs-agents clone) | done | RESOLVED 2026-07-10: `$HOME` is a fresh local-only setup repo (no remote), cs-agents decoupled to `~/projects/axia-seekapa-cs-agents`; `git -C ~ remote -v` empty |
| A16 | Measured self-improving loop (strategy bandit + evolve tracker) | done | `policy.py` (Thompson strategy bandit) + `evolution.py` (weekly golden-set delta) + `intent policy|telemetry|eval|retrieve|evolve`; 244 tests, ADR-0003; closes the /loop which-strategy-wins intent |

## Phase roadmap

Ordered by dependency and leverage. Detail per task lives in the Execution tasks section.

- **P0 Safety + harness hardening (blocks everything git-touching).** A14 concurrent-session
  guard; harness packaging (`[build-system]` so the scorer runs without `PYTHONPATH`, fix the
  one ruff nit) so the platform brain is copy-pasteable and clean.
- **P1 Prove the review gate (A6).** Make cs-agent's `CodexReview` blocking + comment-resolution
  required, rolled advisory then required with severity routing.
- **P2 One real stage environment (A7 + A8).** A cost-efficient stage Azure target (slot or
  scale-to-zero) plus per-env Bicep on cs-agent; also rename the `func-cs-agents-dev` prod/dev
  ambiguity.
- **P3 Complete the delegation flywheel (A10).** Haiku-fallback-on-rate-limit executor, fed by
  the scorecard gaps, everything verified before it counts.
- **P4 Sim-before-real, the full ladder (A11).** Deterministic pyramid (tiers 1-2) + layer-isolated
  no-LLM regression harness + pass^k reliability + trace replay + sim-reviewer, then a tau2-bench
  simulated user and judge-calibration hygiene, then a gated shadow/canary rollout. The next-gen
  leap is simulating trajectories and users, not single outputs. Re-scoped from the mojuco workflow.
- **P5 Wiki-as-code (A9).** Publish `docs/` to the ADO wiki so PRD/ADR are audit-traceable.
- **P6 Git hygiene + de-anomaly (A12 + A15).** Gated on A14 + explicit per-action OK + no live
  parallel sessions. Extract and push `feat/v109` product work cleanly, then decouple `$HOME`.
- **Cross-cut estate lift.** Once P3 exists, close `code_health` (0/2 on 6 repos) and
  `supply_chain` (0/3 on 4 repos) gaps via the flywheel; re-score to measure.

## Execution tasks

Each task: goal, slices, owner persona, verification (proof), stop condition. Vertical TDD
slices where code changes; RED before GREEN. No task is done without pasted command output.

### P0 - Safety + harness hardening

- **T0.1 concurrent-session guard (A14).** Owner: Security and Compliance Office + Workflow
  Clerk. A `~/.claude/bin/session-guard.sh` that counts other live `claude`/`codex` processes on
  other ptys (via `pgrep -a` + own-pty exclusion) and a PreToolUse hook that, for shared-HOME git
  writes (`git worktree`, `git branch -d`, `git clean`, `git reset --hard`, `~/.git` moves),
  aborts with a named "N other sessions live" message unless `SESSION_GUARD_OVERRIDE=1`. Slices:
  (RED) test that `sessions_live()` returns >0 when a second `claude` pty exists; (GREEN)
  implement via pgrep; (RED) test the hook blocks a `git worktree prune` command string and
  allows a read-only `git status`; (GREEN) wire the deny-list. Verify: unit tests pass +
  simulate a blocked command with real hook output. Stop: a destructive git command is provably
  blocked while another session runs, overridable by the env flag.
- **T0.2 harness packaging (A2/A13 follow-up).** Owner: Engineering Firm. Add `[build-system]`
  (hatchling) to `intent-control-plane/pyproject.toml` so `uv run python -m intent_control_plane.standards`
  works without `PYTHONPATH=src`; fix the `UP022` ruff nit in `tests/test_local_alpha.py:29`
  (`capture_output=True`). Verify: `uv run python -m intent_control_plane.standards ~/projects`
  runs clean AND `uv run ruff check .` = 0 errors AND `50 passed`. Stop: scorer runs from the
  documented command, ruff fully clean end-to-end.

### P1 - Prove the review gate (A6)

- **T1.1 severity routing in the reviewer.** Owner: Runtime Agents Division. Have
  `scripts/codex_pr_review.py` tag each finding severity (block / warn / nit). Slices: (RED)
  fixture PR with a known blocker -> expect one `block` thread; (GREEN) classify. Verify: replay
  a recorded diff, assert the severity split in output. Stop: findings carry severity, dismissal
  rate measurable.
- **T1.2 flip CodexReview to blocking on blockers only.** Owner: Release Bureau. Change the
  `CodexReview` stage so `block`-severity findings fail the stage (remove `continueOnError` for
  that path); `warn`/`nit` stay advisory. Roll advisory -> required behind a pipeline variable.
  Verify: a PR with a seeded blocker shows a red required check; a nit-only PR stays green. Stop:
  blocking gate live on cs-agent, rollback variable documented.
- **T1.3 comment-resolution required.** Owner: Release Bureau. Set the ADO branch policy so
  unresolved reviewer threads block completion (the `D*`-documented-only policy made real).
  Verify: `az repos policy` shows the policy enforced; a PR with an open thread cannot complete.
  Stop: comment-resolution enforced on cs-agent, dismissal-rate metric under 20%.

### P2 - One real stage environment (A7 + A8)

- **T2.1 stage Azure target.** Owner: Azure Ops Utility. Add a cost-efficient stage target: a
  deployment slot on the existing Function App (scale-to-zero) OR a second Consumption-plan app,
  chosen for near-zero idle cost. Wire the `stage` branch's Deploy condition to it. Verify: push
  to `stage` deploys to the stage target and a live smoke returns 200 from the stage URL (not
  prod). Stop: `stage` branch actually deploys somewhere non-prod, prod untouched.
- **T2.2 per-env Bicep.** Owner: Azure Ops Utility. `infra/main.bicep` + `dev/stage/prod.bicepparam`
  for cs-agent, imported into the pipeline. Verify: `az deployment group what-if` clean for each
  param file. Stop: env config is IaC, not portal-clicked.
- **T2.3 name the prod/dev ambiguity.** Owner: Architecture Office. Resolve `func-cs-agents-dev`
  being the production target: either rename to `-prod` or document the ADR that the `-dev`-named
  app IS production. Verify: ADR written, name reconciled. Stop: no reader can mistake which app is prod.

### P3 - Complete the delegation flywheel (A10)

- **T3.1 Haiku-fallback executor.** Owner: Mayor Opus + Engineering Firm. When
  `a2a-codex-call.sh` returns `state=rate_limited`, fall back to a Haiku subagent executor with
  the same task contract; record which path ran in the audit log. Slices: (RED) test the
  dispatcher picks Haiku when the a2a result is `rate_limited` and Codex otherwise; (GREEN)
  implement the branch. Verify: unit test + a forced-rate-limit trace showing Haiku ran. Stop:
  rate-limit no longer means dead-stop; audit shows fallback path.
- **T3.2 scorecard-fed queue.** Owner: Data Bureau. Turn the six-dim gaps into a delegation queue
  (lowest-scoring dimension per repo first). Verify: queue generated from live scorer output,
  each item cites the failing check. Stop: a ranked, evidence-backed work queue exists.
- **T3.3 verify-gate.** Owner: QA Lab. A delegated task counts only after re-score improves and
  tests pass. Verify: a closed item shows before/after dimension delta. Stop: churn cannot be
  mistaken for progress.

### P4 - Sim-before-real: the full ladder (A11)

Re-scoped 2026-07-10 from the mojuco scope workflow (local spec + a 2026 SOTA advisor, both
high/medium confidence). The original P4 (tiers 1-2 + a Haiku sim-reviewer) is only the cheapest
static-output screen. The next-gen leap is simulating trajectories and users (not single outputs),
scoring reliability, replaying against real traces, and staged live rollout with rollback. Ordered
adopt-now rungs, then a documented watch/frontier list. Owner: QA Lab + Runtime Agents Division.

- **T4.1 deterministic pyramid (tiers 1-2).** Schema/regex/JSON-shape/function-call-shape checks
  (tier-1) + a small toxicity/PII/injection classifier (tier-2), run BEFORE the grok/DeepSeek
  Foundry judges, each tier only on the residual. Verify: a seeded bad row fails tier-1 with no
  judge call; judge-call count drops on a recorded set. (local rung 1)
- **T4.2 layer-isolated no-LLM regression harness.** Assert the deterministic scaffold layers
  (intent/routing, tool-call schema, escalation, safety envelope) with a fast LLM-free suite in
  CI below the judge tier, so scaffold regressions are caught without judge cost or variance.
  Verify: sub-3s suite catches a seeded routing regression the aggregate judged score masks.
  (SOTA: arXiv 2606.11686, 238 cases in 2.39s)
- **T4.3 pass^k reliability.** Run each eval row k=4-8 times, report pass^k (all-k-succeed), not
  pass@1. Verify: pass^k computed on the smoke set; a flaky row shows the pass@1-vs-pass^k gap.
  (SOTA: tau-bench arXiv 2406.12045; 61% pass@1 -> 25% pass^8)
- **T4.4 deterministic trace replay.** Replay logged a2a + intent JSON verbatim against a
  candidate model/prompt, diff the divergence, virtualize the clock. Verify: a candidate change
  shows a divergence diff on the recorded trace set. (local rung 4)
- **T4.5 sim-reviewer.** Deterministic diff pre-check (lint/type/test) + a Haiku sim-reviewer;
  escalate to the real Codex/Foundry reviewer only on flagged risk. Verify: reviewer call volume
  drops on a recorded diff set with no missed real blocker. (local rung 2; cuts the 262-call/
  ~30%-fail waste)
- **T4.6 tau2-bench simulated user (Yasha/AxiaCS).** Reuse sierra-research/tau2-bench (MIT) + the
  tau2-bench-revised patches; an LLM persona with a goal + policy doc drives real tool APIs against
  a mock DB, scored on DB end-state, not transcript. Verify: end-state scoring on a persona set.
  TREAT the pass-rate as a SCREEN, not truth (arXiv 2601.17087: up to 9pp swing across simulators).
  (local rung 3 + SOTA)
- **T4.7 judge calibration hygiene.** For the grok-4-1 + DeepSeek-V3.2 2-judge panel: periodic
  sample scored vs human labels with Cohen's kappa, position/verbosity/self-preference bias checks,
  documented panel-size choice. Verify: a kappa number + a bias report exist. (SOTA: arXiv
  2603.05399, 2606.01034)
- **T4.8 shadow -> canary -> percentage -> full gate (GATED).** For a new agent/KB version: shadow
  (mirrored, unserved) -> 1-5% canary with auto-rollback (guardrail rate >1.5x baseline, Welch's t
  p<0.05 on rubric mean) -> ramp -> full. Adopt ONLY after T4.1-T4.6 exist. Verify: a live smoke
  through the shadow stage, rollback proven. (local rung 5 + SOTA)

Frontier / watch (documented, NOT scheduled): non-cooperative adversarial personas (sim users are
too cooperative and inflate success, arXiv 2603.11245 / 2605.12894); dialect/register fairness
calibration (directly relevant to Yasha he/ar/en, the AAVE/SAE 9pp finding is English-only, so a
multilingual analog is a hypothesis to test locally, not settled); reward-hacking audit of our own
eval rows (Cursor found 63% gamed runs, low effort). SKIP: world-model simulators (Qwen-AgentWorld,
arXiv 2606.24597, RL-training infra we do not need); L2 latent edges (open-weight hidden-state
transfer, R&D only, after L1 is stable). Adopt-now-but-high-effort multi-slice: artifixer/Foundry
L1 semantic transport + source-only opacity-repair (the "repair, not just score" leap).

### P5 - Wiki-as-code (A9)

- **T5.1 publish docs/ to ADO wiki.** Owner: Communications Desk + Release Bureau. Configure
  "Publish code as wiki" (or a CI wiki-sync step) binding a repo's `docs/` to its ADO wiki.
  Verify: a docs push republishes the PRD/ADR; the wiki shows the current commit. Stop: docs are
  audit-traceable and PR-reviewed, not hand-edited.

### P6 - Git hygiene + de-anomaly (A12 + A15) - gated

- **T6.1 branch + worktree cleanup (A12).** Owner: Release Bureau. Behind T0.1 guard + explicit
  per-action OK + no live parallel sessions: prune the stale worktree (`projects/axia-seekapa-cs-agents`),
  merged-branch sweep of the 49 local branches (keep unmerged + feat/v109). Verify: `git worktree
  list` clean, branch count down, `git status` unchanged for tracked files. Stop: hygiene done
  with zero data loss, each deletion individually approved.
- **T6.2 extract + push feat/v109 product work (A15 pre-req).** Owner: Release Bureau. The
  `azure-function-crm` product changes on `feat/v109` (local-only, 5 commits ahead of master)
  extracted into a clean branch containing only product files (no `.claude`, no `~/docs`,
  no shell dotfiles) and pushed to ADO. Verify: pushed branch diff contains only product paths;
  CI green. Stop: v109 product work is safe on the remote, independent of `$HOME`.
- **T6.3 decouple $HOME (A15).** Owner: Architecture Office + operator. Only after T6.2: move the
  cs-agents clone into `~/projects/axia-seekapa-cs-agents`, restore `$HOME` to a plain home dir
  (no `.git` rooted at `~`). Verify: `git -C ~ rev-parse` fails (no repo at HOME); the clone lives
  under `~/projects`; parallel sessions unaffected. Stop: `$HOME` no longer doubles as a corporate
  working tree.

## Premortem (5 failure modes)

1. Mandatory AI-review noise blocks merges. Mitigation: severity routing (block/warn/nit),
   advisory then required rollout, dismissal rate under 20%.
2. A git-hygiene or de-anomaly op collides with a live parallel session (this already happened
   2026-07-10). Mitigation: A14 guard lands in P0 and gates every shared-HOME write; P6 also
   requires explicit per-action OK.
3. Delegating unverified work is churn, not power. Mitigation: T3.3 verify-gate + re-score as the metric.
4. Stage env cost creep. Mitigation: scale-to-zero slot, one persistent stage max.
5. Cargo-culting the GitHub-OSS elite bar onto private Azure services. Mitigation: the standard
   is Azure-translated; skip OSS-only items (Trusted Publishing, OSS-Fuzz, community bots).

## References

`repo-standards-2026-07-09.md`, `harness-structure-standard-2026-07-09.md`,
`canonical-repo-structure-2026-07-10.md`, `repo-enterprise-maturity-todo-2026-07-09.md`,
`Documents/CICD_SOTA_Pipeline_Audit_20260706/CICD-SOTA-Pipeline-Audit-2026-07-06.md` (real
evidence for A6/A7, replaces the earlier phantom "research brief 1-4" citations), cs-agent
pipeline (`origin/master:azure-pipelines.yml`), ADR `docs/adr/0001-unified-platform-standard.md`.
