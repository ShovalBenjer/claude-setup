---
PRD: Claude OS
Ticket: SETUP-OS #22
Status: active
Depends: ADR-0004 (agreement gate), ADR-0005 (enforcement over prose), ADR-0006 (one scheduler topology), ADR-0008 (reputation from external truth), ADR-0009 (SLM swarm); specs 2026-07-23-persona-review-economy, 2026-07-23-slm-swarm
Supersedes: the dead WSL intent.db observability path (CLAUDE-OS §L2)
Date: 2026-07-24
---

# Spec — FleetView: a superior command center over the Claude OS

## Goal

Build a Windows-native, self-improving control surface for the Claude OS that takes
everything valuable from `amirfish1/claude-command-center` (CCC, MIT) and layers it on
what CCC has no concept of: the PR-review fabric, the model-agnostic persona review
economy, the SLM swarm, hook enforcement, typed memory, and the three-speed
self-improvement loop (CLAUDE-OS §2d). Working name: **FleetView**.

The single differentiating rule, stated once: **CCC is an observability + spawn UI over
raw sessions. FleetView is that PLUS a control plane whose top panel is the OS proposing
its own next work.** CCC shows you what your sessions are doing. FleetView shows you what
the OS decided to do next, why, and asks for one approval. The dashboard is where the
"getting better by itself" becomes visible and one-click-approvable, not a hidden cron
side effect.

We do NOT fork or vendor CCC. We adopt exactly one of its architectural ideas (on-disk
`.jsonl` session state as source of truth) and build our own thin surface over our own OS
state, CCC-style session state, AND self-improvement proposals.

## Non-goals

- Not a rewrite of CCC in our repo. No copied Python file, no copied HTML.
- Not owning execution. Like CCC, FleetView ATTACHES to sessions (reads `.jsonl`); it
  never becomes the thing that runs Claude Code. Execution stays in the harness.
- Not a cloud service. Local-loopback only, single operator, Windows-native. No auth
  server, no multi-tenant, no hosted dashboard (repo-topology: this is a folder in the
  OS umbrella, `tools/fleetview/`, one path-triggered nothing since it never deploys).
- Not a framework build. One Python file (stdlib + our existing sidecars) + vanilla JS
  HTML, matching CCC's zero-framework discipline. Bloat is a defect (ponytail).

## 1. Prior art we are measuring against

CCC (`amirfish1/claude-command-center`, MIT): a local dashboard for parallel AI-coding
sessions (Claude Code, Codex, Cursor, Antigravity, Kilo, Kimi). Reads
`~/.claude/projects/*.jsonl` as source of truth (attaches, does not own execution);
Kanban (Backlog to Planning to Working to Review to Testing to Verified); spawn/resume
headless sessions; installs `post-tool-use.py` + `stop.py` hooks; GitHub issue
integration (start-from-issue, verify-closes-it); cost/usage tracking (plan windows,
rate limits, per-session attribution); cross-session coordination (group-chat,
sibling-ask synchronous RPC, persistent peer sessions); a 12-skill orchestration pack
(pair-verify, standup, second-opinion, bug-race, docs-drift, release-audit); full-text +
semantic transcript search; auto-fix-deploys (polls Vercel, spawns `/fix-deploy` on prod
errors); single Python file + vanilla JS HTML, JSON sidecars in
`~/.claude/command-center/`; Mac-first (some Windows degradation), local-loopback only.

It is a genuinely good observability + orchestration UI. Its ceiling: it has no review
economy, no reputation, no enforcement, no SLM tier, and no self-improvement loop. Its
coordination is peer RPC between equal sessions; ours is a governed, scored, self-pruning
market. That gap is the whole opportunity.

## 2. Feature-extraction table (every CCC feature: what we take, how ours is superior)

| # | CCC feature | What we take | How FleetView is superior (the layer it rides on) |
|---|---|---|---|
| 1 | `~/.claude/projects/*.jsonl` as source of truth; attach, don't own | The pattern wholesale. Session truth = on-disk `.jsonl`, read-only. | We UNIFY three truth stores in one reader: session `.jsonl` (CCC-style) + our OS state (task bus, `audit.jsonl`, `reputation.db`, memory) + self-improvement proposals. CCC sees sessions; we see the whole control plane. Replaces the dead WSL `intent.db`. |
| 2 | Kanban (Backlog to Planning to Working to Review to Testing to Verified) | The column model as a familiar spine. | Our columns are BOUND to the SDLC kernel state machine (CLAUDE-OS §L0): no card enters Verified without evidence (command+output) + intent-coverage; illegal transitions (GENERATED to SHIPPED without JUDGED+VERIFIED) are refused by the same hook that guards the harness, not by UI honor system. The board reflects an enforced state machine, not a whiteboard. |
| 3 | Spawn/resume headless sessions from the UI | The spawn/resume affordance. | Spawns route through our subagent admission criteria (§L3: parallel/risky/specialist/isolating, default 0, max 4) and carry a fresh context pack + budget + output contract. A FleetView spawn is a governed dispatch, not a bare `claude -p`. Model tier is chosen by policy (model-selection.md), not hardcoded. |
| 4 | Installs `post-tool-use.py` + `stop.py` hooks | The idea of dashboard-driven hook install. | Our hooks already exist and ENFORCE (kernel-anchor, slop gate, SessionStart recall, notify-toast; ADR-0005). FleetView does not install CCC's hooks; it VISUALIZES the ones we own and surfaces hook-error events as first-class dashboard signals (a hook that errored last week is a red card, feeding the weekly loop). |
| 5 | GitHub issue integration (start-from-issue, verify-closes-it) | Start-from-issue and closes-verification. | We wire it to the PR-review fabric: an issue-started session's PR is auto-reviewed by the agreement gate (ADR-0004) with two decorrelated models drawn from the persona pool. "Closes it" is verified by live-smoke where applicable (production-means-merged-and-smoked rule), not just by the issue-close webhook. |
| 6 | Cost/usage tracking (plan windows, rate limits, per-session attribution) | The full cost panel. | Attribution extends to the SLM tier and the review economy: per-session Claude cost PLUS per-deployment Foundry cost (foundry-deployment-per-project naming makes it readable) PLUS "kept-local" router savings (§L5 SLM use 2). The panel shows the subscription-window backoff state and the metered-API monthly cap projection ($1.36 Apify lesson), so cost is a governed budget surface, not a meter. |
| 7 | Cross-session coordination (group-chat, sibling-ask sync RPC, persistent peers) | Sibling-ask synchronous RPC as a transport primitive. | CCC's peers are equal. Ours is the persona review economy (spec 2026-07-23): a sibling-ask is scored, contracted, reputation-weighted, decorrelation-constrained. A session asking a sibling for a second opinion is routed to the current best-reputation persona for that aspect (Thompson), not to whatever peer is idle. Coordination becomes a governed market. |
| 8 | 12-skill orchestration pack (pair-verify, standup, second-opinion, bug-race, docs-drift, release-audit) | The skill CONCEPTS, re-homed to our owners. | Each maps to an owned Gastown persona and an existing skill: pair-verify to QA Lab agreement gate; standup to the daily digest; second-opinion to the review economy; docs-drift to docs-control-plane sweep; release-audit to Release Bureau + prod-deploy-rules. We do not import 12 loose skills; we route the six that earn their place and mark the rest unwired (hive-mind rule). Aspect-verifiers are single-aspect (Multi-Agent Verification), not a debate swarm. |
| 9 | Full-text + semantic transcript search | Both search modes. | Semantic search runs on the LOCAL SLM tier (§L5 use 1/7: local embed + retrieval), not a paid API; results are a routing/recall aid, never proof (latent-vector-workflows safety rule). Search is scoped to typed memory (decisions/episodes/procedures/taste) as well as raw transcripts, so you retrieve distilled procedure, not just chat. |
| 10 | Auto-fix-deploys (polls Vercel, spawns `/fix-deploy` on prod errors) | The poll-then-autonomously-spawn pattern. | Generalized beyond Vercel to our deploy surfaces (Azure Functions, Cloudflare Pages, GitHub Actions). A spawned fix is a governed dispatch that must pass the agreement gate and live-smoke before its PR can auto-post; it never force-pushes or deploys without the destructive-op approval gate. The trigger is a signal into the self-improvement loop, not a fire-and-forget. |
| 11 | Single Python file + vanilla JS HTML, JSON sidecars, no framework | The whole stack discipline. | Same constraint, our sidecars: reads `~/.claude/command-center/`-equivalent under `~/.claude/fleetview/` PLUS our existing `audit.jsonl`, `reputation.db`, task bus, memory dir. Ponytail pass mandatory after the contract holds (boundary-contracts point 8). |
| 12 | Mac-first, some Windows degradation; local-loopback only | Local-loopback only. | Windows-NATIVE, not degraded: native cron (ADR-0006, not systemd), PowerShell notify-toast + native phone push (ADR-0003), Windows paths throughout (§L7 purge). The platform CCC treats as second-class is our first-class target. |

## 3. What CCC lacks that we add (our differentiators, surfaced in the UI)

Each of these is invisible in CCC and becomes a first-class dashboard surface here.

1. **PR-review fabric panel.** Always-fresh review on 22 repos (DONE 2026-07-23), two
   independent reviews to an agreement gate (ADR-0004) with `_provenance` + `audit.jsonl`
   traceback. FleetView shows: open PRs, which personas/models were drawn, agree/disagree
   verdicts, and the ones escalated to the operator. CCC has GitHub issue links; it has no
   review verdict surface at all.

2. **Persona + model leaderboards.** The review economy (spec 2026-07-23) made visible:
   two leaderboards (top personas by aspect precision, top models by reputation), plus
   PIP/fired status, plus coverage-gap alerts ("aspect X has escaped defects and no
   owning persona"). This is the "constantly marketed" surface the economy spec calls for.
   Personas are model-agnostic roles; the board shows role vs actor separation explicitly.

3. **SLM triage panel.** Router (§L5 use 2) kept-local vs escalated counts, cost saved,
   schema-fail escalations, and flywheel status (S1-S3 trace collection, adapter
   eval-vs-held-out). CCC has cost tracking; it has no cheap-first tier to track.

4. **Enforcement panel.** Live hook health (ADR-0005): which hooks fired, which errored,
   which gates blocked an illegal transition this week. A gate that silently stopped
   enforcing is a defect (capability-honesty matrix, §L1); this panel makes stub/always-
   pass checks visible. CCC installs hooks; it never reports whether they still bite.

5. **The self-improvement loop, surfaced (the headline; see §5).** The medium loop
   (weekly) and slow loop (PIP/fire/recruit) proposals rendered as approvable cards at the
   TOP of the dashboard. This is the single feature that makes FleetView a control plane
   and not a dashboard.

6. **Phone push integration.** Native push (ADR-0003) + Windows toast already wired
   (DONE 2026-07-22). FleetView's approve/dismiss actions mirror to the phone: a proposed
   next-work card can be approved from the phone RC concierge front door (§L3), so the
   operator is an approval surface even away from the PC. CCC is PC-loopback only, no push.

## 4. Architecture decision

### 4.1 Adopt: on-disk `.jsonl` state as source of truth (the one idea we take)

CCC's load-bearing correct decision is that session state lives in `~/.claude/projects/
*.jsonl` and the dashboard READS it, rather than owning a parallel execution DB that
drifts. We adopt this and it directly **replaces the dead WSL `intent.db`** observability
path (CLAUDE-OS §L2), which assumed a systemd/WSL runtime we retired (ADR-0006). The
lesson generalizes: observe the harness's own on-disk truth, do not maintain a shadow
execution store that goes stale (the exact failure production-means-merged-and-smoked
warns about: trusting a stale local graph).

FleetView's reader is a UNION over three on-disk truth stores, all read-only:

- **Session truth** (CCC pattern): `~/.claude/projects/*.jsonl` — live/paused/done
  sessions, tool calls, current phase.
- **OS state**: task bus (SQLite WAL, §L7), `audit.jsonl`, `reputation.db` (persona +
  model + pair reputation), typed memory dir, repo graph + blast-radius + branch-health
  SQLite (§L6).
- **Self-improvement proposals**: a new append-only `~/.claude/fleetview/proposals.jsonl`
  written by the weekly/slow loops (§5), each a typed proposal record with status
  pending/approved/rejected/applied.

### 4.2 Build our OWN thin surface (not CCC's)

A boundary contract governs the reader (boundary-contracts rule: this IS a boundary,
`.jsonl`/DB on disk to a rendered view). Concretely:

- Every inbound read (a `.jsonl` line, a DB row, a proposal record) is decoded into a
  named typed DTO. No raw `.jsonl` line is forwarded to the HTML as-is.
- The HTTP view returned to the vanilla-JS frontend is built from a named view type, not
  from raw bytes. Every parse error is handled; a malformed `.jsonl` line is logged and
  skipped, never rendered as garbage, never crashes the panel (fail-closed).
- The read layer is extracted into a named, testable client per store
  (`SessionStore`, `OSStateStore`, `ProposalStore`) with the five canonical boundary
  tests each (valid, malformed line, missing file/config, missing resource, timeout/lock).
- Errors cross to the frontend as typed error DTOs, not bare dicts.

Stack (matches CCC's discipline, our tools): ONE Python file
`tools/fleetview/server.py` (stdlib `http.server` + `sqlite3` + `json`, no framework, no
external server), ONE `index.html` (vanilla JS, no build step), sidecars under
`~/.claude/fleetview/`. Windows-native: launched by native cron / a startup script
(§L7 always-on-PC health), binds `127.0.0.1` only. Ponytail pass after the contract and
tests are green (boundary-contracts point 8).

### 4.3 Read-only to production stores; write only to its own sidecar

FleetView never mutates a production store (pii-handling non-negotiable #2 generalized):
task bus, `reputation.db`, `audit.jsonl`, memory are READ. The only thing FleetView
writes is proposal-status transitions in its own `proposals.jsonl` (operator approve/
reject) and a UI-preferences file. Approving a proposal does not let FleetView apply it;
it flips a status that the OS's own apply path (hooked, gated) then acts on. The
dashboard proposes and records the approval; the harness applies. (ADR-0005: the stick is
in the hook, not the UI.)

## 5. The self-improvement angle (the headline)

The top panel of FleetView is not sessions and is not a Kanban board. It is the
**Proposed Next Work** panel: the output of the OS's three-speed self-improvement loop
(CLAUDE-OS §2d), rendered as approvable cards, newest-highest. This is where "the system
gets bigger and better by itself" stops being an aspiration in a doc and becomes a thing
the operator watches grow and approves with one click.

What produces the cards (all already specified elsewhere; FleetView only SURFACES them):

- **Fast loop (per-PR):** reputation + Thompson routing updates. Not a card (too frequent);
  shown as the live leaderboard delta.
- **Medium loop (weekly self-improvement, §L5):** reads what happened — skills fired vs
  never, hooks that errored, intents shipped without proof, failure clusters — and
  proposes DIFFS to rules/hooks/skills/context-retrieval. Each diff is a card: the change,
  the evidence that motivated it (the errored hook, the escaped defect), and Approve /
  Reject / Explain. Approve flips the proposal status; the OS's gated apply path lands it.
- **Slow loop (as-needed):** recruit a new review persona for an uncovered defect cluster;
  PIP a decaying persona; fire one that failed remediation twice (firing is a
  destructive-op card, explicit per-action approval, ADR-0005 + authorization rule).

The card record (in `proposals.jsonl`) is typed:

```
{
  "id": "prop-2026-07-27-recruit-a11y",
  "loop": "slow|medium",
  "kind": "recruit-persona|pip-persona|fire-persona|rule-diff|hook-fix|skill-merge|retrieval-tune",
  "motivation": "3 escaped a11y defects in PRs #.. #.. #.., no owning persona",
  "evidence": ["audit.jsonl#L..", "gh pr #..", "reputation.db:escaped"],
  "proposed_change": "unified diff or new persona contract YAML",
  "blast_radius": "which repos/hooks/personas this touches (tools/graph)",
  "confidence": 0.0,
  "reversible": true,
  "status": "pending|approved|rejected|applied",
  "approved_by": null
}
```

The dashboard's promise, made concrete: over weeks, the Proposed Next Work panel should
show the OS recruiting reviewers to close its own coverage gaps, fixing its own errored
hooks, merging its own redundant skills, and tuning its own retrieval — each one an
approved card with an evidence trail in `audit.jsonl`. The operator's job shrinks to
reading motivation + evidence and clicking Approve. That visible shrinking IS the
self-improvement made legible. A week with zero proposals is itself a signal (the loop
stalled) and surfaces as an empty-panel warning, not silence.

Growth-by-itself guardrails (so "gets bigger" does not mean "sprawls"):
- Every proposal carries blast-radius (tools/graph, §L6) and a reversibility flag;
  irreversible/destructive ones require explicit per-action approval, never batch-approve.
- Proposals that would ADD surface (a new persona, a new hook) must name what they retire
  or why nothing is redundant (ponytail discipline as a proposal field), so the system
  grows in capability without growing in clutter.
- No proposal auto-applies. The apply path is gated by the same enforcement hooks the OS
  already runs; FleetView only records the approval.

## 6. Premortem (5 failure modes)

1. **Shadow-store drift (the CCC lesson inverted).** FleetView starts caching or
   maintaining its own copy of session/OS state "for speed," it drifts from the `.jsonl`/
   DB truth, and the dashboard confidently shows stale reality — the exact
   production-means-merged-and-smoked failure. *Mitigation:* FleetView holds NO durable
   copy of production state; every panel reads live on each request (or a request-scoped
   cache invalidated on file mtime). Its only writes are its own `proposals.jsonl` status
   and UI prefs. A test asserts no production-store write path exists.

2. **Dashboard becomes execution owner.** Under pressure to "just spawn from here," spawn
   logic accretes in the server until FleetView is the thing running Claude Code, and the
   attach-don't-own invariant (the reason CCC and we both read `.jsonl`) is lost.
   *Mitigation:* spawns are dispatches through the existing governed path (admission
   criteria + context pack + budget), not a subprocess owned by the server; the server
   records the dispatch and reads its resulting `.jsonl`. Contract test: killing FleetView
   leaves all sessions running.

3. **Approval theater / auto-apply creep.** The self-improvement panel, to feel
   "autonomous," starts auto-approving low-confidence or "obviously fine" proposals, and
   the operator-as-approval-surface invariant (ADR-0005) silently erodes — the system
   mutates its own harness unwatched. *Mitigation:* the apply path is hook-gated
   independently of FleetView; the UI can only flip status to `approved`, never `applied`;
   destructive proposals (fire-persona, rule-delete) require explicit per-action approval
   with no batch path; an audit row records who approved each applied change.

4. **Boundary rot at the reader (untyped middle layer).** The reader "just forwards"
   `.jsonl` lines and DB rows to the HTML, a malformed line crashes a panel or renders
   garbage, and a swallowed parse error hides missing sessions — the qc-insights
   passthrough defect (boundary-contracts §Why). *Mitigation:* typed DTOs both directions,
   every decode error handled, malformed line skipped-and-logged (fail-closed), the five
   canonical boundary tests per store client. No panel renders raw bytes.

5. **Windows-native regression to CCC's Mac-first degradation.** The build quietly assumes
   POSIX paths, systemd, or a `~` that resolves Mac-style, and FleetView becomes as
   degraded on Windows as CCC is — on the machine that is our ONLY target. *Mitigation:*
   Windows paths throughout (§L7 purge), native cron not systemd (ADR-0006), PowerShell
   toast + native push (ADR-0003), a smoke test that launches the server and hits every
   panel on this actual machine (production-means-smoked: generate-then-observe, not an
   idle assumption).

## 7. Acceptance checklist

- [ ] `tools/fleetview/server.py` (one file, stdlib only) + `index.html` (vanilla JS, no
      build step) exist; binds `127.0.0.1` only; launches under native cron / startup on
      this Windows machine.
- [ ] Reader is a read-only UNION over the three truth stores (session `.jsonl`, OS state,
      `proposals.jsonl`); no write path to any production store exists (test-asserted).
- [ ] Three named store clients (`SessionStore`, `OSStateStore`, `ProposalStore`), each
      with the five canonical boundary tests (valid, malformed, missing-config,
      missing-resource, timeout/lock); typed DTOs both directions; malformed lines skipped
      and logged, never rendered.
- [ ] Kanban columns bound to the SDLC-kernel state machine; an illegal transition is
      refused by the same hook that guards the harness, not by UI honor system.
- [ ] Sessions panel attaches to `~/.claude/projects/*.jsonl`; killing FleetView leaves
      all sessions running (attach-don't-own contract test passes).
- [ ] PR-review fabric panel shows open PRs, drawn personas/models, agree/disagree
      verdicts, and operator-escalated cases, with `_provenance`.
- [ ] Persona + model leaderboards render from `reputation.db` with role/actor separation,
      PIP/fired status, and coverage-gap alerts.
- [ ] SLM triage panel shows router kept-local vs escalated, cost saved, schema-fail
      escalations, flywheel S1-S3 status.
- [ ] Enforcement panel shows per-hook fired/errored/blocked-this-week; an errored hook
      renders as a red card that feeds the weekly loop.
- [ ] Cost panel attributes Claude + Foundry (per named deployment) + SLM kept-local
      savings; shows subscription-window backoff state and metered-API cap projection.
- [ ] TOP panel = Proposed Next Work: medium/slow-loop proposals as typed cards
      (motivation + evidence + blast-radius + reversibility) with Approve / Reject /
      Explain; Approve flips status only, never applies; destructive proposals require
      explicit per-action approval.
- [ ] Approve/dismiss mirrors to native phone push (ADR-0003); a proposal is approvable
      from the phone RC concierge front door.
- [ ] Empty Proposed-Next-Work panel for a week renders as a loop-stalled warning, not
      silence.
- [ ] Ponytail/simplify pass run after the contract and all boundary tests are green;
      no framework, no vendored CCC code, single Python file preserved.
- [ ] Live smoke on THIS machine: launch server, hit every panel, paste real HTTP output
      (generate-then-observe, not idle-query).
