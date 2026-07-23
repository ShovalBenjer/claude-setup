# ADR-0008 — Persona reputation is computed from external ground truth ONLY

Status: Accepted (2026-07-23)

## Context
The persona review economy allocates work by reputation and hires/fires personas on
it. Reputation is only meaningful if its signal is real. The research is decisive:
LLM personas voting on each other form a martingale (errors ~60% correlated, no
information gained); self-assessment does not deepen quality; verifier quality, not
count, is the bottleneck. A reputation built on peer/self votes is theater.

## Decision
A persona's reputation is computed ONLY from external ground truth: (1) did a finding
reproduce under a deterministic check; (2) did the operator accept or dismiss it;
(3) escaped defects — bugs later caught (by CI, prod, or another confirmed reviewer)
in code this persona reviewed and passed. Personas NEVER rate personas. The two
review models in the agreement gate count as independent only because they are
different models with different evidence, never a same-model panel.

## Consequences
+ Reputation tracks real quality; PIP/firing/allocation decisions are grounded.
+ Forces investment in cheap external verifiers (the actual quality lever).
- Reputation updates lag (escaped defects surface later); allocation must tolerate
  delayed, noisy signal (Thompson sampling does, by design).
- Requires the operator's accept/dismiss to be captured as data on every posted finding.
- A persona with too little volume has an unreliable score; new recruits get a
  probation window before firing eligibility.
