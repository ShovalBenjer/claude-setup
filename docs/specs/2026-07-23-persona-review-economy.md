---
PRD: Claude OS
Ticket: SETUP-OS #19
Status: active
Depends: ADR-0004 (agreement gate), ADR-0008 (reputation signal), ADR-0005 (enforcement)
Date: 2026-07-23
---

# Spec — Persona Review Economy (a dynamic labor market of reviewers)

## Goal
Turn the Gastown persona registry from static prose roles into a LIVE labor market:
review personas hold contracts, earn reputation from real outcomes, are allocated
work by reputation, get PIP'd when they decay, fired when they stay bad, and new
specialists are recruited when a defect class keeps escaping. This is the slow
feedback loop of the OS (CLAUDE-OS.md §2d) and the L5/L8 realization of the
Black-Mirror agent-contracts research, disciplined by ADR-0008.

## Why this shape (grounded, not cosplay)
Multi-agent failure is a contract problem, not a capability problem (MAST, 1,642
traces). Scaling DISTINCT aspect-verifiers beats scaling candidates (Multi-Agent
Verification). Reputation is only real if its signal is external (ADR-0008). So the
market is: many single-aspect reviewers, each contracted, each scored by ground
truth, allocated by Thompson sampling.

## Entities

### Persona contract (one YAML per persona under dot-claude/personas/)
```
id: reviewer-boundary-contracts
aspect: boundary            # single aspect: correctness|security|boundary|simplicity|perf|slop|tests
model: sonnet               # or codex via a2a (model diversity is required, not optional)
scope: "IO edges, proxies, (de)serialization, typed DTOs"
allowed_tools: [read, grep, gh-pr-diff]
forbidden: [approve_own, write, deploy]
output_schema: {verdict, findings:[{severity,file,line,claim,evidence,fix}]}
probation: true             # new recruit; not fire-eligible until N>=20 scored findings
status: active              # active|pip|fired
```

### Reputation record (SQLite, one row per persona, updated by the fast loop)
```
persona_id | n_findings | confirmed | dismissed | escaped_defects
           | precision (confirmed/(confirmed+dismissed))
           | escape_rate (escaped/reviewed_prs)
           | reputation (Beta posterior mean, see below) | last_updated
```

## Mechanics

### 1. Allocation (fast loop) — Thompson over personas
For each PR, per aspect, sample each candidate persona's reputation from its
Beta(confirmed+1, dismissed+1) posterior; allocate the review to samples above a
floor. High performers get first pass probabilistically; low-volume/new personas
still get exploration draws (Thompson handles the explore/exploit tradeoff with no
hand-set epsilon). "Constantly marketed" = the digest shows the current leaderboard.

### 2. Scoring (ADR-0008) — external ground truth only
On every posted finding, the operator's accept/dismiss is captured (a reaction or a
`gh` label). `confirmed` / `dismissed` update precision. Separately, an ESCAPED
DEFECT (a bug later caught by CI/prod/another confirmed reviewer in a PR this persona
passed) is the harshest negative, updating escape_rate. Personas NEVER score personas.

### 3. PIP (slow loop) — quarantine + remediate
A persona whose reputation drops below the PIP threshold (e.g. precision < 0.5 over
its last 20 findings, or escape_rate rising) goes `status: pip`: pulled from live
allocation, run against a SANDBOX eval set (past PRs with known-good findings), its
prompt narrowed or retrained. Re-admitted to `active` only after passing the sandbox
set. (Research analogue: White Bear quarantine — remediate, then re-verify.)

### 4. Firing (slow loop)
A persona that fails PIP remediation twice, or stays below threshold past probation,
is `status: fired`: deactivated, its contract + record archived (never deleted —
audit). Firing is proposal → operator approval (destructive; ADR-0005).

### 5. Recruitment (slow loop) — coverage-gap driven
The weekly loop clusters escaped defects by aspect/pattern (the mojuco coverage-
cluster taxonomy). When a cluster has repeated escapes and no persona owns it, draft
a NEW persona contract targeting exactly that gap, seed its prompt from the escaped
examples, admit on probation. The market grows to fit the live threat surface.

## Integration
- Runs inside the agreement gate (ADR-0004): the two decorrelated models are drawn
  from the persona pool per aspect; agreement still required to auto-post.
- Reputation + audit live in the OS observability store (audit.jsonl + reputation.db).
- The FIRST live two-Claudes review (test PR #1) is the seed data point.

## Premortem (5 failure modes)
1. **Reputation theater** — signal degrades to peer/self votes. Mitigation: ADR-0008
   is a hard gate; the scorer literally has no persona-vote input field.
2. **Cold-start firing** — a good persona fired on 3 noisy early findings. Mitigation:
   probation window (N>=20 scored) before fire-eligibility; Thompson explores low-N.
3. **Operator-labeling fatigue** — accept/dismiss not captured, so no signal.
   Mitigation: one-click reaction labeling; unlabeled findings age out as neutral,
   never as negative.
4. **Escaped-defect attribution error** — blaming a persona for a bug outside its
   aspect/scope. Mitigation: escapes attributed only within the persona's declared
   scope; cross-aspect escapes hit the recruitment loop, not an individual.
5. **Market collapse to one persona** — Thompson over-exploits a single high scorer,
   coverage narrows. Mitigation: per-aspect allocation (one market per aspect, not
   global), minimum-exploration floor, recruitment when a cluster goes uncovered.

## Acceptance
- [ ] Persona contracts exist as files; reputation.db schema created.
- [ ] Scorer captures confirmed/dismissed/escaped from real PR outcomes (ADR-0008).
- [ ] Thompson allocator picks reviewers per aspect per PR.
- [ ] PIP quarantine + sandbox re-admit works on one seeded low performer.
- [ ] Firing is proposal+approval; archive retains record.
- [ ] Recruitment drafts a new persona from a real escaped-defect cluster.
- [ ] Leaderboard appears in the daily digest.
