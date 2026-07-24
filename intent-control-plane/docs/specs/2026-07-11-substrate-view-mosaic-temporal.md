---
prd: intent-control-plane
ticket: none (internal platform brain)
status: active
created: 2026-07-11
---

# Spec: substrate (Temporal / DBOS) + view (Mosaic) adoption, in full

From the 2026-07-11 comparison of temporal.io, the Geektime Temporal-vs-n8n piece, and
emergent-inc/mosaic against our system. Conclusion up front: adopt neither now. Both are clean
swap-in upgrades for two layers we built thin on purpose (Layer 2 durability; the view). This spec
records exactly when each becomes worth it and the tasks each would take, so the decision is not
re-litigated from memory.

## Substrate: Temporal / DBOS vs our transitions.py

Where we are: `transitions.py` is a ~150-line allow-list state machine over sqlite, DBOS-style
"durability as a library over your DB." Its honest limit is that durability means RE-RUN the slice,
not crash-resume mid-pass. That is fine at single-operator/one-machine scale and cheap.

Adopt-triggers (any one flips the decision):
- A swarm pass must survive a crash mid-flight and resume EXACTLY (not re-run).
- Workers must run across MACHINES with recovery.
- A workflow must SUSPEND for hours/days waiting on a human and resume deterministically.
- We go multi-tenant / fleet (a team product, not one operator).

Tasks if/when triggered (in order):
1. Define a durable-execution interface behind `transitions.py` (advance / current-state / compensate)
   so the backend is swappable without touching Layers 3-4. This is the cheap insurance to do EVEN
   NOW: keep the seam clean so a later swap is a backend change, not a rewrite.
2. First upgrade = DBOS (Postgres, a library not a server): keeps ops light, adds real crash-resume +
   replay. Prefer over Temporal until cross-machine or long-suspend is actually needed.
3. Only then Temporal (server + workers + deterministic-workflow constraint): reserve for genuine
   cross-machine fleet, long-suspend human gates, saga/compensation at scale. Note its constraint
   (workflows deterministic, side effects only via Activities) matches our checkpoint-before /
   side-effects-after-keep discipline already, so the port is conceptual-compatible, just heavier.

Do NOT: adopt Temporal for a single-operator local harness. That is fleet tax for a one-person job.

## View: Mosaic vs our command-center

Where we are: the view is our weakest layer (the `harness-command-center` web scaffold + the
streaming `gastown-spawn`). Mosaic (emergent-inc) is a serious answer to the exact "watch the agents,
take over any pane" problem, native Swift on libghostty, live multi-user pane sharing + takeover,
agents as first-class. It is early (v0.0.7, 70 stars) but very active.

Hard blocker: Mosaic is macOS-only (Swift / AppKit / libghostty). The operator is on WSL2 / Linux, so
it cannot run here. It also solves a different problem than our core, it is the VIEW and human
takeover, it does not grade, evolve, or bandit-route agents.

Tasks / options (pick one when the view is worth investing in):
1. Accept the gap for now (recommended near-term): the streaming `gastown-spawn` log + `/workflows`
   are enough to watch runs; the view is not the current bottleneck.
2. If we invest, rebuild `harness-command-center` as the Linux/web equivalent and copy the RIGHT
   Mosaic features, live agent/pane stream, watch + TAKE-OVER a running agent, room-based session
   sharing, agents-as-first-class, NOT a static dashboard. The takeover capability is the thing worth
   copying.
3. Evaluate a Linux-capable alternative or a web front-end over the Claude Agent SDK stream.

Decision recorded: near-term option 1; if the view becomes the bottleneck, option 2 copying
live-watch + takeover specifically. The learning layer (grade/evolve) stays ours regardless; Mosaic
would be a front-end TO it, never a replacement.
