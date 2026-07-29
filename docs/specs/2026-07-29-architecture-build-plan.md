# Architecture build plan, merged 2026-07-29 (plan of record)

One structured plan merging: TODO.md (all sections as of this evening), the
2026-07-29 specs (deterministic-preflight, intent-traceability,
prompt-to-ticket-lifecycle, trace-model, decision-rules), the session retro,
the long-context critique response, the channel matrix, open lessons and the
prior handoff's risk list. Detail lives in the tickets; this file is the map.
Rendered copy for review: the "Claude OS build" artifact, same date.

Design constraint named by the operator: HIS review is the throughput limit
and his satisfaction is a threshold. Every phase below is shaped to spend
operator attention only where a machine cannot: consolidated decision queue,
falsifier-dated experiments, fewer junk artifacts reaching review.

## Layer map (live / building / decision)

- INTENT: prompt-ticket capture LIVE; resource ledger LIVE (0.2% noted
  coverage baseline); preflight SPEC awaiting /diverge; decision-rules,
  prompt-to-ticket, trace-model specs drafted (transcript-format risk
  L-2026-07-29-e bounds them to hook payloads).
- ENFORCEMENT: gate 12 domains + selftests + mutation specs LIVE; Stop hooks
  LIVE (handback, prior-art, ship-gate). Building next: advice-without-
  artifact, lane-enforcement, waiver-falsifier execution, stack-lint oracle,
  selftest-ledger isolation. Open defect: panel.py prose-vs-code, third
  waiver, expires 2026-08-12, operator decision.
- STATE: append-only ledgers LIVE (claims, lessons, bus hash-chained,
  gate-runs, handback, api-usage, prompt-tickets, sessions tap). Building:
  ecosystem.db (AUTO-06) which unblocks work-claims (AUTO-04) and FleetView
  (AUTO-19); RT-1 confidence-outcome pairs; RT-2 human approval ledger.
- OBSERVABILITY: statusline + per-session tap LIVE (which-terminal solved,
  cost per session recorded). Building: FleetView v0 over the tap, stack via
  repo-stack-reasoning then /diverge; P-DASH alternative: evaluate adopting
  CCC (amirfish1) instead of building, excavate-before-building rule.
- JUDGES: LIVE with real-completion proof: OpenRouter, NVIDIA NIM, Gemini
  (public-only rule), Codex (paid), GitHub Models. Probes queued: Groq,
  Cerebras. Parked: qwen-code (login-locked; family covered in pools).
  Azure paid runtime pre-existing. Long-context models join via pools.
- MODELS: fable-5 default is an EXPERIMENT, falsifier due 2026-08-05
  (handback, restarts, refusals, throttling vs opus at 2x price); live
  xhigh effort contradicts the rule's high default, same decision date.
- LANES: B/C/D/E live, A retired 2026-07-29 (test-enforced). Cross-lane runs
  through bus + proposal rows (exercised today B to C). Mechanical lane
  check ticketed.
- CONTENT: case-ledgers.pages.dev LIVE, old URLs 301, learning PWA clean;
  custom domain optional decision; syndication stays draft-first
  (AUTO-12/13/14); the-bench v5 draft committed, revert offer open.
- DISCOVERY: sweep rebuild ticketed (six measured gaps, OpenReview needs the
  CDP browser); Amir/CCC watch baselined in memory, queue-study ticketed.

## Phases

Shipped 2026-07-29, evidence in the retro: lane A retirement (8/8 tests),
NVIDIA channel (9/9 live), Cloudflare split (Actions run green, both sites
verified serving), statusline + tap, repo-stack-reasoning and preflight and
plan docs, retro + K3 response, judge fleet repairs (gemini, codex,
gh-models), resume-session diagnosis + bus steering, gate PASS on the final
tree after every write batch.

Sprint to 2026-08-05 (decision day), lane B order of work:
1. Oracle batch, each with selftest + mutation spec: advice-without-artifact
   in completion_gate; lane-enforcement check; waiver-falsifier execution;
   stack-lint domain; selftest-ledger isolation.
2. ecosystem.db bootstrap (AUTO-06), then FleetView v0 on the sessions tap,
   in parallel with the CCC adopt-vs-build evaluation (P-DASH); whichever
   wins, the tap is the data contract.
3. Discovery sweep rebuild; Groq + Cerebras probes with measured quotas;
   gemini-review workflow consuming the stored secret (AUTO-10 remainder).
4. AUTO-18: register daily digest 07:03 + weekly self-improve as S4U tasks,
   observe one unattended fire. Doc catch-up rows (P0): ADR-0007 Codex-out
   line, WSL path purge, PRD status sync.

2026-08-05: read the fable falsifier against the opus baseline; keep or
revert the default; set effort per the same data; re-measure handback rate
and idle minutes against the 31% / 940-min baseline.

2026-08-12: panel.py waiver expires; execute whichever the operator chose
(lexical pass or retirement to /code-review).

After: preflight pilot on one activity class (post /diverge), RT-3/4/5,
persona review economy (#19), migration activation backlog (91/186),
AUTO-09/11/15/17/20, WhatsApp copilot and learning-card emitter (P4, with
lanes C/D), dolt/cross-machine sync when a private store exists.

## Operator decision queue (the entire ask on Shoval, consolidated)

1. panel.py: lexical pass or retire; needed before 2026-08-12.
2. fable default and effort level: decision lands with 08-05 data, no read
   needed before that.
3. claude-setup PR cut: the tree interleaves sessions; say when to cut and
   what to exclude, or delegate the split to a clean-room session.
4. voice-metrics preservation: WhatsApp LID in keys, commit or keep live-only.
5. DECIDE row: which undeployed work-enforcement hooks to adopt.
6. case-ledgers custom domain, optional; the-bench v5 draft keep or revert.
7. API-key rotation confirmation (P0 row from 07-24, never confirmed).
8. CCC verdict after the evaluation lands: adopt, fork, or build FleetView.

## The bottleneck, treated as a design input

Human review does not scale with agent count; the plan attacks its cost from
both sides. Reduce demand: preflight and the advice gate stop non-deliverables
from reaching review; falsifier-dated experiments replace open-ended debates.
Raise supply value: one decision queue instead of scattered asks; FleetView
and the statusline make session state legible at a glance; RT-2's approval
ledger makes rubber-stamping measurable and RT-1's calibration pairs are the
only path to safely widening the autonomous band below operator review.
Baseline to beat, measured: about 940 idle minutes per operator week and a
31% handback share; re-measure on 2026-08-05. The operator's own steering is
already measured cheap: five mid-turn redirects today, zero lost work.
