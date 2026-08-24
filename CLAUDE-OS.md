# CLAUDE OS - Single Source of Truth

Status: ACTIVE (living document, the spine)
Date: 2026-08-24
Owner: Shoval Benjer. Maintainer: the Claude-setup session.
Repo: github.com/ShovalBenjer/claude-setup - canonical home of the OS; `dot-claude/`,
`dot-codex/`, `dot-agents/` are the deployable payload.

This file MERGES and SUPERSEDES every prior setup plan. Predecessors remain as
history/reference only; none is authoritative. See the supersession table at the end.

---

## 1. Mission

A personal Claude Operating System: everything Shoval captures (WhatsApp, docs, specs,
prompts) becomes gated, evidenced action across his ventures, with Shoval reduced to an
approval surface, running on the Claude subscription at near-zero marginal cost.

Three client ventures (each its own session/repo; the OS serves all):
1. **Hiring machine** (new-recruit) - P(hire) optimization, offer by ~end Sept 2026.
2. **Learning platform** (הסדנה / daily-deep-learning) - closing the gap between
   building AI-natively and actually knowing it.
3. **The OS itself** (this repo) - rails, gates, review fabric, notification fabric.

---

## 2. How to use Claude Code effectively

### 2.1 Session discipline

- **Read the boot path first.** `docs/SESSION-BOOT.md` is the canonical entry point.
  Skipping it is the most frequently logged failure in `state/lessons.jsonl`.
- **Name your lane.** `docs/charters.md` assigns lanes. Append a claim row to
  `state/claims.jsonl` before starting. Doing another lane's work is the second most
  logged failure.
- **Ground truth is git plus state files, never a doc.** `docs/analysis/` and
  `work-docs/` are dated snapshots and several are knowingly stale.

### 2.2 Prompt patterns

- **Spec-as-spine.** No substantive build without a spec + acceptance table. Every turn
  re-anchors to the active spec. The `UserPromptSubmit` hook injects the active-spec
  pointer.
- **Intent contract first.** Substantive task → first artifact is an acceptance checklist
  extracted from the operator's plan/context. Judged against THAT.
- **Loop, don't hand back.** Workflows with a separate adversarial done-verifier (mojuco
  pattern: one refuter, refute-by-default). Full time/token budget; speed is only a
  virtue on explicit quick fixes.
- **Done has a format.** Verification evidence (command + output) + intent-coverage
  statement (covered / uncovered + why). No coverage table = not done.
- **Wide-then-curate for taste.** Generate 5 candidates with verbalized conventionality
  probabilities; the operator picks. Pick + reason appended to taste corpus.
- **Defixation.** Name the obvious/default solution and forbid it first. Anchor vocabulary
  to excavated real artifacts.

### 2.3 Context management

- **Fresh-context resumption.** A thrashed session → write handoff, restart from
  artifacts; never continue polluted context. The `Stop`/`PreCompact` hook writes handoff
  (goal/phase/decisions/evidence/next). Progress files + git are the sole carry-over.
- **Compaction never decides what survives.** The mandated handoff schema is written first,
  then compaction runs.
- **Long horizon = the LOOP, not the session.** Cron-driven bounded runs over durable
  artifacts (feature-list, progress file, one advance per run, commit).
- **Subagent admission.** Spawn only when parallel, risky, specialist, or context-isolating.
  Default 0, max 4. Every spawn gets fresh context pack + budget + output contract.
- **Fanout with designed information asymmetry.** Breadth uses disjoint evidence/roles;
  depth stays in ONE context with the 1M model when the working set demands.

### 2.4 Safety guidelines

- **Confidence gates.** >=0.90 autonomous; 0.70–0.90 work + explicit proof gate;
  <0.70 ask or spawn reviewer.
- **State machine legality.** No GENERATED -> SHIPPED without JUDGED + VERIFIED; no close
  without evidence; zero-opacity content is killed, never softened.
- **Secrets.** `.env`/credentials never read/echoed/committed; PII never enters embedding
  indexes. Rotate exposed keys immediately.
- **Outward posts are drafted, never auto-sent.** Jira, LinkedIn, email, PR comments beyond
  agreement gate are drafted first.
- **Rules-as-enforcement.** A rule with no stick is a defect. Enforced in hooks/CI, not
  prose (ADR-0005).

### 2.5 Common workflows

#### Starting a session

1. Read `docs/SESSION-BOOT.md` in order.
2. Name your lane from `docs/charters.md`.
3. Append claim row to `state/claims.jsonl`.
4. Read `TODO.md` for current state.
5. Verify ground truth: `git status -sb`, `git log --oneline -5`.

#### Shipping work

1. Write a spec + acceptance table before coding.
2. Code in small, focused commits.
3. Run `python tools/gate/gate.py run --project . -v` before pushing.
4. Push to feature branch.
5. Open PR via `gh pr create`.
6. Address review feedback.
7. Merge only after CI green and approval.

#### Daily operations

```bash
python tools/gate/gate.py run --project . -v   # Morning gate check
python tools/bus/bus.py inbox                   # Check task bus
python tools/selfimprove/scan.py                # Ranked open work
python tools/audit/skills_sync.py check         # Drift check
```

#### Recovery

- Thrashed session: write handoff, restart.
- Dirty tree with only docs changes: gate downgrades docs-only deltas.
- Failed postcondition: replan that subgoal only, do not restart the whole task.

---

## 3. The Layers

### L0 - SDLC Kernel (the operating discipline; under everything)

- Intent contract first.
- Loop, don't hand back.
- Done has a format.
- State machine legality.
- Confidence gates.

### L1 - Governance & Identity

- One reconciliation ADR series.
- Secrets: rotate exposed keys; `.env` never committed.
- Capability honesty matrix: the OS maintains a table of what each rail actually verifies
  vs claims. Stub functions and always-pass checks are defects by definition.

### L2 - Memory, Continuity & Comms Copilot

- Task bus as spine: all sessions read/write tasks with owner + evidence + deps.
- Intent ledger (`~/.intent/`: events.jsonl + intent.db).
- WhatsApp communications copilot (Shoval-granted scope): read-only, draft-only, PII-safe.
- Auto-memory + weekly curator cron.

### L3 - Orchestration

- One scheduler topology: native local cron (browser/ledger/WhatsApp work), cloud routines.
- Standing personas with real cadence.
- Subagent admission criteria: spawn only when parallel, risky, specialist, or
  context-isolating.
- Hive bead bus for atomic claim/close across multi-session work.

### L4 - I/O

- Inbound: WhatsApp copilot, Gmail via gws, GitHub/ADO events, phone RC voice.
- Outbound: one daily digest push + immediate P0 push + Windows toasts.
- Browser fleet: ONE owner process for automation Chrome (port 9224).
- Outward posts drafted, never auto-sent.

### L5 - Quality Fabric

- a2a ⇄ GitHub PR review sync: dual review, agreement gate, provenance + audit.
- Eval gates non-blocking until trusted; deterministic checks ALWAYS before LLM judges.
- Weekly self-improvement loop: skills fired vs never, hooks errored, intents without proof.
- Skills estate: every skill owned by a persona or archived; unwired = defect.
- Validity discipline: any scorer needs ground-truth calibration, stratified checks,
  test-retest stability, and documented weight derivation.

### L6 - Project Portfolio

- Registry: every repo -> owner persona, standards score, deploy story, docs compliance.
- GitHub claim-consistency is a STANDING weekly invariant.
- Docs control plane applies to every repo: prd/ spec/ adr/ analysis/, ONE TODO, ONE INDEX.

### L7 - Platform & Machine

- Windows-first purge: WSL paths, systemd assumptions, stale /cdp docs.
- TUI hardening: fullscreen renderer, statusline, GPU terminal opt.
- Always-on-PC health for the daemon.
- SQLite everywhere with WAL.

### L8 - Frontier

- mojuco (adversarial sim-verify + sim-to-real calibration) and artifixer
  (opacity-masked generation) generalized as OS-wide patterns.
- Latent/vector path: every inter-agent edge declares transport=text_json today.
- Learning-card emitter: any session that ships work using a concept files a card.
- Agent contracts + reputation: each standing persona has a contract and accrues a track
  record.
- Closed-loop recalibration: settled outcomes -> learned adjustments -> config -> next cycle.

---

## 4. Deep Work Protocol

Grounded in the July-2026 literature sweep. Four findings drive everything:
(1) long-task failure is EXECUTION failure; (2) visible self-reflection is mostly theater;
(3) same-context ensembles cannot exceed their correlated-error floor;
(4) homogenization is measured and prompt-resistant.

The protocol - every rule has a native mechanism and a stick:

| # | Rule | Native mechanism | Sticks via |
|---|---|---|---|
| 1 | Spec-as-spine: no substantive build without spec + acceptance table | Plan mode -> docs/prd; UserPromptSubmit hook injects active-spec pointer | hook + docs-control-plane rule |
| 2 | Fresh-context resumption: thrashed session -> write handoff, restart | Stop/PreCompact hook writes handoff | hook file + progress artifacts in repo |
| 3 | External verifiers at every boundary | PostToolUse test hooks; /verify, /run | hooks + production-means-smoked rule |
| 4 | HTN-lite: every subgoal carries postcondition + check command | Plan-mode template; TaskCreate metadata | task-bus convention + planning skill |
| 5 | Wide-then-curate for taste: 5 candidates; operator picks | AskUserQuestion with previews; docs/taste.md | creative-brief skill + taste.md file |
| 6 | Defixation: name the obvious solution and forbid it first | creative-brief skill (excavate-before-building) | skill + memory rule |
| 7 | Slop lint as GATE on prose deliverables | Stop-hook / review pass; humanize + shoval-voice | hook, not suggestion |
| 8 | Fanout for breadth with designed information asymmetry | Agent tool + Workflow; /model [1m] escalation | hive-mind rule + L3 admission criteria |
| 9 | Typed memory: decisions / episodes / procedures / taste | auto-memory dir structure; curator cron | memory taxonomy + cron |
| 10 | Compaction never decides what survives | PreCompact hook | hook file |
| 11 | Long horizon = the LOOP, not the session | CronCreate / /schedule; initializer+coder pattern | cron jobs + artifacts |
| 12 | Aspect-split verification: parallel single-aspect verifiers | Workflow pipeline templates | .claude/workflows in repo |

Cross-cutting: depth is ENFORCED by structure (hooks, gates, files, crons), never
REQUESTED from the model.

---

## 5. Native-feature map

| Native feature | Layer(s) | Use | Sticks via |
|---|---|---|---|
| Hooks | L0,L2,L4,L5 | kernel gates, recall, toasts, verifiers | dot-claude/hooks + settings.json |
| Skills (frontmatter auto-invocation) | L0,L5,L8 | creative-brief, review aspects, voice gates | dot-claude/skills, owned per persona |
| Plan mode + plan files | L0 | spec-as-spine entry | plansDirectory + prd tables |
| Task bus | L0,L2,L3 | acceptance checklists, postconditions, cross-session state | task conventions in CLAUDE.md rule |
| Workflows / ultracode | L0,L5 | loop-until-dry, adversarial verify, aspect panels | .claude/workflows templates |
| Subagents | L3,L5 | asymmetric fanout, fresh-eyes review | admission criteria rule |
| CronCreate + /schedule + /loop | L3,L4,L5 | daily digest, PR watcher, curator, self-improvement | registered jobs |
| Monitor + background tasks | L4 | gws reply watcher, CI watches | armed per session by convention |
| PushNotification + Notification hook toast | L4 | approvals rail | settings.json hook |
| Remote Control + phone app | L3,L4 | concierge front door | remoteControlAtStartup + convention |
| Memory (auto-memory dir + MEMORY.md) | L2 | typed memory taxonomy | memory files + curator cron |
| CLAUDE.md hierarchy + .claude/rules | L1 | governance, authority order | this repo's dot-claude deployed |
| MCP (lazy, per-session) | L4 | gws, playwright, onesignal (dormant) | mcp-activation skill; default-off |
| GitHub Actions claude-code-action | L5 | always-fresh PR review | .github/workflows in each repo |
| /model + effort + [1m] | L3,L8 | depth escalation for coupled design work | model-selection rule |
| AskUserQuestion previews | L0 | wide-then-curate picks | creative-brief skill |
| SendUserFile / DesignSync | L4 | artifact delivery | per-task |

---

## 6. Build sequence

- **P0 (now):** repo relocation done; July-state sync done; governance ADRs + Windows-path
  purge; push to GitHub.
- **P1:** daily digest push + task-bus conventions + SessionStart recall rewire.
- **P2:** a2a ⇄ GitHub PR fabric (watcher, dual review, agreement gate, provenance).
- **P3:** scheduler consolidation + standing personas + concierge phone convention.
- **P4:** WhatsApp copilot (triage/drafts/coaching) + learning-card emitter.
- **Continuous:** weekly self-improvement, skills triage, portfolio invariants, capability
  honesty matrix.

---

## 7. Acceptance criteria

| # | Criterion | Status |
|---|---|---|
| 1 | claude-setup repo = canonical, relocated, July state synced, pushed | in progress |
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
| 13 | Always-fresh PR review workflow on every source repo | DONE 2026-07-23 (22 repos) |
| 14 | Deep Work Protocol hooks live | TODO (P1) |

---

## 8. Supersession table

| Predecessor | Disposition |
|---|---|
| CLAUDE-CODE-MASTER-PLAN-2026-05-03 (+ skills triage/scatter) | Superseded. Alive: dotfiles-repo idea, skill-pair merges, hook checklist. |
| 2026-05-13 hive-adoption + 2026-05-17 systemd map | Superseded. Alive: bead bus semantics, evidence-to-close, TTL sweep. |
| 2026-06-14 agent-orchestration-rewire | Superseded. Alive: admission criteria, budget profiles, context packs. |
| 2026-06-25 local-intent-control-plane | Superseded as plan; intent ledger + authority order + confidence gates absorbed into L0/L2. |
| 2026-06-28 mojuco/artifixer plans | Superseded as plans; primitives absorbed into L0/L8. |
| 2026-07-07 gap analysis + 2026-07-08 suggestions | Absorbed (G1->L5 weekly loop, G2->L0 gates, G3->L2 recall/routing, G4->L5 eval gates). |
| 2026-07-09 harness-maturity-plan | Completed historically; shim discipline carried into L5. |
| Cowork session 2026-07-20 | Decision record only (local beats cloud-bridge for logged-in surfaces). |

---

## 9. Pending operator decisions

1. Global default model: set to opus[1m] by operator 2026-07-29. Effort level stays
   contradictory on purpose (rule says high, live runs xhigh, nobody has measured).
2. API key in תזכורת לעצמי - rotate. Still unconfirmed since 2026-07-24.
3. PR-fabric opt-in repo list.
4. WhatsApp copilot cadence (2x daily proposed) + coaching retro frequency.
5. dot-agents deploy target: `~/.agents` absent on this machine. Deploy or archive.
6. dot-codex vs dot-agents merge decision (affects 45 forked skills).
7. `dot-claude/settings.json` oracle: third drift checker for settings vs payload.
