# Session charters — four lanes (ADR-0013)

A session opens by naming its lane. A lane implements ONLY inside its charter.
Cross-lane needs → proposal row in ecosystem.db (until db lands: tools/selfimprove/
proposals.jsonl), never doing the other lane's work. This file is the structural fix
for cross-session convergence: different queues, different repos, different voices.

## Lane A — Concierge (phone-facing)

- Owns: intent intake from RC/phone, routing, notifications. NEVER implements.
- Every intake: write to db/proposals + push ack to phone. Stateless by design —
  a fresh RC spawn loses nothing.
- Working dir: ~/claude-setup. Reads charters + open proposals, nothing deep.

## Lane B — Claude setup (harness) — THIS session's lane

- Owns: ~/claude-setup — rules, hooks, skills, schedulers, review fabric, a2a
  bridges, ecosystem.db, FleetView, autonomy rails, social pipeline PLUMBING.
- Does NOT: hiring logic (C), learning content (D), posting content decisions (A/operator).

## Lane C — Resume engine (ongoing project)

- Owns: ~/Downloads/new-recruit — hiring machine, arms, applications, job scans.
- Gets from B: crons, review workflows, push approvals, db tables. Nothing else.

## Lane D — Learning (הסדנה)

- Owns: daily-deep-learning PWA, learning cards, study loops.
- Gets from B: learning-card emitter hook (AUTO ticket), nothing else.

## Anti-convergence rules (all lanes)

1. Claim before work: mark the proposal claimed with your lane id; a claimed row is
   another lane's property.
2. Design decisions run /diverge (5 candidates, weird-first); picks append to taste.md.
3. Open each session distinctly: state lane + top queue item, not a generic greeting.
4. Double-claims and charter violations are lessons (state/lessons.jsonl) — log them.
