# CLAUDE OS — Single Source of Truth

Status: ACTIVE (living document, the spine)
Date: 2026-07-23
Owner: Shoval Benjer. Maintainer: the Claude-setup session.
Repo: github.com/ShovalBenjer/claude-setup — canonical home of the OS; `dot-claude/`,
`dot-codex/`, `dot-agents/` are the deployable payload (July-2026 state, on top of the
May-2026 work export in commit 910dec2).

This file MERGES and SUPERSEDES every prior setup plan. Predecessors remain as
history/reference only; none is authoritative. See the supersession table at the end.

---

## 1. Mission

A personal Claude Operating System: everything Shoval captures (WhatsApp, docs, specs,
prompts) becomes gated, evidenced action across his ventures, with Shoval reduced to an
approval surface, running on the Claude subscription at near-zero marginal cost.

Three client ventures (each its own session/repo; the OS serves all):
1. **Hiring machine** (new-recruit) — P(hire) optimization, offer by ~end Sept 2026.
2. **Learning platform** (הסדנה / daily-deep-learning) — closing the gap between
   building AI-natively and actually knowing it.
3. **The OS itself** (this repo) — rails, gates, review fabric, notification fabric.

---

## 2. The Layers

### L0 — SDLC Kernel (the operating discipline; under everything)
Origin: Shoval's 2026-07-23 feedback ("small patches + fast done ≠ my intent"),
Forge Loop, local-intent-control-plane, orchestration-rewire.

- **Intent contract first.** Substantive task → first artifact is an acceptance
  checklist extracted from Shoval's plan/context (task bus). Judged against THAT.
- **Loop, don't hand back.** Workflows with a separate adversarial done-verifier
  (mojuco pattern: one refuter, refute-by-default). Full time/token budget; speed
  is only a virtue on explicit quick fixes.
- **Done has a format.** Verification evidence (command + output) + intent-coverage
  statement (covered / uncovered + why). No coverage table = not done.
- **State machine legality** (from mojuco/artifixer plan): no GENERATED→SHIPPED
  without JUDGED+VERIFIED; no close without evidence; zero-opacity content is
  killed, never softened. Enforced in hooks, not prose.
- **Confidence gates** (intent-plane): ≥0.90 autonomous; 0.70–0.90 work + explicit
  proof gate; <0.70 ask or spawn reviewer.

### L1 — Governance & Identity
- One reconciliation ADR series: Codex = independent reviewer only (executor role
  dead per 2026-07-20); model policy per model-selection.md actually enforced in
  settings (Sonnet default; Fable/Opus deliberate) — PENDING SHOVAL (current global
  default is fable[1m]); LoopCV verdict unified (KEEP DEMOTED).
- Secrets: rotate the API key found in WhatsApp (PENDING SHOVAL); `.env`/credentials
  never read/echoed/committed; PII never enters embedding indexes (pii-handling).
- Cost: subscription-window backoff on all cron fleets; external metered APIs get a
  hard monthly cap + pre-run projection (the $1.36 Apify lesson, generalized).
- **Capability honesty matrix** (from IVR-sensors + SOTA-v4 audit): the OS maintains
  a table of what each rail actually verifies vs claims. Stub functions and
  always-pass checks are defects by definition.

### L2 — Memory, Continuity & Comms Copilot
- **Task bus as spine**: all sessions read/write tasks with owner + evidence + deps.
- SessionStart recall rewired to Windows paths: inject intent digest + candidate
  skills (gap-analysis Tier-0, the highest-leverage single move).
- Auto-memory + weekly curator cron (replaces dead WSL timers).
- Intent ledger (`~/.intent/`: events.jsonl + intent.db) — capture prompts as SDLC
  artifacts; authority order: raw prompt > spec > verified evidence > repo state >
  summary > vector similarity.
- **WhatsApp communications copilot** (Shoval-granted scope 2026-07-23): read ALL
  groups + 1:1s via CDP (tools/whatsapp/, proven 2026-07-22 against role=grid DOM);
  (a) twice-daily triage digest (who waits, asks, deadlines), (b) drafted replies in
  Shoval's WhatsApp voice (style corpus from his own sent messages;
  `~/.claude/style-corpus/shoval-whatsapp-voice.md`), (c) periodic reaction-coaching
  retro. Draft-only — the send path is deliberately unbuilt. All local; PII out of
  any index; incremental per-chat cursor.

### L3 — Orchestration
- One scheduler topology: native local cron (browser/ledger/WhatsApp work), cloud
  routines (public-source work), WSL systemd retired.
- Standing personas with real cadence: Mayor/concierge, Hiring operator, Portfolio
  reviewer, Curator → become named agents the day standing agents release.
- Phone RC = concierge-only front door: loads task bus + digest, dispatches, never
  works in-call.
- Subagent admission criteria (orchestration-rewire): spawn only when parallel,
  risky, specialist, or context-isolating; default 0, max 4 even in ultracode;
  every spawn gets fresh context pack + budget + output contract. ultracode is a
  budget profile, not "max everything".
- Hive bead bus retained where multi-session work needs atomic claim/close
  (SQLite BEGIN IMMEDIATE; TTL sweep; evidence_url required to close).

### L4 — I/O
- Inbound: WhatsApp copilot (L2), Gmail via gws (recruiter replies → outcomes;
  alerts → discovery), GitHub/ADO events, phone RC voice.
- Outbound: **one daily digest push** (approvals pending, PR verdicts, hiring
  funnel, learning streak, ops health) + immediate push for P0 + Windows toasts
  (Notification hook → dot-claude/hooks/notify-toast.ps1, wired 2026-07-22).
  Push-beats-pull (Executive MCP research); digests carry `_provenance`.
- Outward posts (Jira, LinkedIn, email, PR comments beyond agreement gate) are
  drafted, never auto-sent.
- Browser fleet: ONE owner process for automation Chrome (port 9224, profile
  `~/.claude/automation-chrome-profile`); phases serialize through the task bus.
- OneSignal: NOT part of the personal loop (native push won). Reserved for
  Shoval-owned apps' users (learning-platform Web push; Kith Expo when unparked).

### L5 — Quality Fabric
- **a2a ⇄ GitHub PR review sync**: cron PR watcher over opt-in ShovalBenjer repos →
  two independent reviews (Claude /code-review + Codex via a2a-codex-call.sh) →
  agreement gate (both confirm → post `gh pr review` comment with `_provenance` +
  audit.jsonl traceback; disagree → digest for Shoval). Prompts per the PR-review
  best-practices doc: OWASP/CWE anchors, evidence-or-"possible issue", ≤15-line
  fixes, tiered severity.
- The fabric reviews the OS's own changes (this repo's PRs) — dogfooding.
- Eval gates (promptfoo/deepeval) non-blocking until trusted; deterministic checks
  ALWAYS before LLM judges (intent-plane pyramid).
- Weekly self-improvement loop: skills fired vs never, hooks errored, intents
  without proof, proposed diffs — applied only on approval.
- Skills estate: every skill owned by a persona or archived; unwired = defect;
  the six redundant pairs from the May triage merged.
- **Validity discipline** (Wiley grilling): any scorer the OS ships (fit-score,
  mojuco judges) needs ground-truth calibration, stratified checks, test-retest
  stability, and documented weight derivation — or it is labeled a heuristic.

### L6 — Project Portfolio
- Registry: every repo → owner persona, standards score, deploy story, docs
  compliance. Active: new-recruit, הסדנה, claude-setup. Dormant with wake
  triggers: Kith (Apple fee → OneSignal Expo path ready), SQLTok demo (Shoval
  deploy), Gastown portfolio repos (PR fabric covers), seekapa legacy (archived).
- GitHub claim-consistency is a STANDING weekly invariant (profile/READMEs vs the
  resume claims table), not a one-time sweep.
- Docs control plane applies to every repo incl. this one: prd/ spec/ adr/ analysis/,
  ONE TODO, ONE INDEX.

### L7 — Platform & Machine
- Windows-first purge: WSL paths, systemd assumptions, stale /cdp + reground docs.
- TUI hardening (TUI research): fullscreen renderer, statusline, GPU terminal opt.
- Always-on-PC health for the daemon (power settings, wake, Chrome ownership).
- SQLite everywhere with WAL; survives reboots.

### L8 — Frontier
- mojuco (adversarial sim-verify + sim-to-real calibration) and artifixer
  (opacity-masked generation: high=byte-faithful, low=marked interpolation,
  zero=kill) generalized as OS-wide patterns (they map to Workflow adversarial
  verify + grounding veto).
- Latent/vector path: every inter-agent edge declares transport=text_json today;
  swappable to embedding/latent later without topology redesign (L0→L1→L2 honesty:
  no false claims of latent comms on closed models).
- **Learning-card emitter**: any session that ships work using a concept files a
  card (concept, where used, mastery dimensions) to the learning platform queue —
  the bridge from AI-native building to actually knowing it. Aligns with the
  Living Codex design (mastery = Recognize/Explain/Apply/Connect/Challenge; spaced
  recall; no guilt mechanics).
- Agent contracts + reputation (Perplexity brainstorm): each standing persona has a
  contract (scope, SLA, acceptance, proof) and accrues a track record the router
  can use. Adversarial internal agent periodically fuzzes the others' assumptions.
- Closed-loop recalibration (CONCEPTS/MatchIQ): settled outcomes → learned
  adjustments → config → next cycle, no human dial; claims ledger discipline —
  every load-bearing claim in the OS maps to an enforcing test.

---

## 3. Build Sequence

- **P0 (now):** repo relocation ✅; July-state sync ✅; this document ✅; governance
  ADRs + Windows-path purge; push to GitHub.
- **P1:** daily digest push + task-bus conventions + SessionStart recall rewire.
- **P2:** a2a ⇄ GitHub PR fabric (watcher, dual review, agreement gate, provenance).
- **P3:** scheduler consolidation + standing personas + concierge phone convention.
- **P4:** WhatsApp copilot (triage/drafts/coaching) + learning-card emitter.
- **Continuous:** weekly self-improvement, skills triage, portfolio invariants,
  capability honesty matrix.

## 4. Acceptance (PRD table)

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

## 5. Supersession table

| Predecessor | Disposition |
|---|---|
| CLAUDE-CODE-MASTER-PLAN-2026-05-03 (+ skills triage/scatter) | Superseded. Alive: dotfiles-repo idea (this repo), skill-pair merges, hook checklist. Dead: $HOME-worktree move, Seekapa phases, Kilocode conversion. |
| 2026-05-13 hive-adoption + 2026-05-17 systemd map | Superseded. Alive: bead bus semantics, evidence-to-close, TTL sweep. Dead: systemd timers, ADO webhooks, work rigs. |
| 2026-06-14 agent-orchestration-rewire | Superseded. Alive: admission criteria, budget profiles, context packs, eval ladder. Dead: Codex-as-runtime. |
| 2026-06-25 local-intent-control-plane | Superseded as plan; the intent ledger + authority order + confidence gates are absorbed into L0/L2. |
| 2026-06-28 mojuco/artifixer (work-general + personal-autonomy + work-general-setup) | Superseded as plans; primitives absorbed into L0/L8; personal-autonomy resume loop lives in hiring-machine v2 (sibling). |
| 2026-07-07 gap analysis + 2026-07-08 suggestions | Absorbed (G1→L5 weekly loop, G2→L0 gates, G3→L2 recall/routing, G4→L5 eval gates). |
| 2026-07-09 harness-maturity-plan | Completed historically; shim discipline carried into L5. |
| Cowork session 2026-07-20 | Decision record only (local beats cloud-bridge for logged-in surfaces). |

## 6. Pending Shoval decisions

1. Global default model change (fable[1m] → sonnet per own rule) — config edit awaits OK.
2. API key in תזכורת לעצמי — rotate.
3. PR-fabric opt-in repo list.
4. WhatsApp copilot cadence (2x daily proposed) + coaching retro frequency.
