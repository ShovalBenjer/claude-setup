---
PRD: Claude OS
Ticket: SETUP-OS #19
Status: proposed
Depends: ADR-0004 (agreement gate), ADR-0008 (reputation signal), ADR-0005 (enforcement)
Date: 2026-07-23
Corrected 2026-08-17 glue pass: header said `active`; all 7 rows in the
Acceptance section below are unchecked and no reputation.db, contract file,
or allocator code exists on disk (`find . -iname "*reputation*"` returns only
the ADR; `state/` carries no persona-contract or reputation ledger). This was
the sweep's example of a lying active header with nothing built.
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

## Three-way separation (personas are NOT bound to models)
The load-bearing design decision: **a persona is a model-agnostic ROLE, not a model.**
Three independent things:
1. **PR type** — what kind of change this is (frontend / data-pipeline / infra / CI /
   docs / security-sensitive). Determines WHICH personas activate.
2. **Persona** — a review ROLE/LENS: an aspect + scope + prompt + reputation. Owns the
   WHAT. Any model can enact it. Never names a model.
3. **Model** — an interchangeable ACTOR (Claude, Gemini free, DeepSeek/OpenRouter free,
   local SLM) assigned to enact a persona at review time. Owns the HOW. Swappable.

So "security-reviewer" is a persona that Claude enacts on one PR and Gemini on the next;
you never hardcode "Gemini = the security guy." Model diversity (ADR-0004 decorrelation)
is achieved by ASSIGNING DIFFERENT MODELS to the activated personas per PR, not by
baking a model into a persona.

## Entities

### Persona contract (model-agnostic; one YAML per persona under dot-claude/personas/)
```
id: reviewer-boundary-contracts
aspect: boundary            # single aspect: correctness|security|boundary|simplicity|perf|slop|tests|a11y
applies_to_pr_types: [data-pipeline, infra, backend]   # which PR types activate this lens
scope: "IO edges, proxies, (de)serialization, typed DTOs"
prompt_ref: prompts/boundary.md    # the lens; NO model named anywhere
allowed_tools: [read, grep, gh-pr-diff]
forbidden: [approve_own, write, deploy]
output_schema: {verdict, findings:[{severity,file,line,claim,evidence,fix}]}
probation: true             # not fire-eligible until N>=20 scored findings
status: active              # active|pip|fired
```

### Two reputation records (persona reputation and model reputation are SEPARATE)
Separating them answers "is the ROLE wrong or is the ACTOR weak?"
```
persona_rep:  persona_id | confirmed | dismissed | escaped | precision | reputation
model_rep:    model_id   | confirmed | dismissed | escaped | precision | reputation
pair_rep:     (persona_id, model_id) | ...   # optional: is Gemini-as-security good?
```
A persona with a bad prompt gets PIP'd (fix the LENS). A model that reviews weakly gets
down-weighted (used less), independent of any persona.

## Mechanics

### 0. PR-type routing (which personas activate)
On PR open/push, classify the PR type from cheap signals — changed file paths/ext
(.tsx -> frontend; pipeline dirs -> data; .github/workflows -> CI; Dockerfile/bicep ->
infra), blast-radius width (tools/graph/blast_radius.py), diff size, secret-adjacent
patterns. The type selects the persona set via `applies_to_pr_types`. Only relevant
lenses run (less cost, less noise). A frontend PR gets {a11y, ui-consistency,
correctness}; a data-pipeline PR gets {boundary, correctness, security}.

### 1. Model assignment + allocation (fast loop)
Two-stage, keeping persona and model separate:
- **Persona allocation** — Thompson over the ACTIVATED personas' `persona_rep`
  posteriors (Beta(confirmed+1, dismissed+1)); exploration draws keep new lenses alive.
- **Model assignment** — assign an interchangeable model to each chosen persona,
  weighted by `model_rep`, with a hard DECORRELATION constraint: the personas whose
  findings will be compared in the agreement gate MUST be enacted by DIFFERENT model
  families (Claude vs Gemini vs DeepSeek). Same-model pairs don't count as independent
  (ADR-0004/0008). Free models (Gemini/OpenRouter free tiers) are first-class actors.
"Constantly marketed" = the digest shows both leaderboards (top personas, top models).

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

## 5. Tracer-bullet slices (added 2026-08-17 glue pass, none built)

1. **Contracts on disk.** `state/persona-contracts.jsonl` exists with one row per
   persona (aspect, scope, reputation seed). Falsifiable: `wc -l
   state/persona-contracts.jsonl` returns the same count as
   `gastown-company-registry.md`'s persona list, and a schema check rejects a row
   missing `aspect`.
2. **Scorer wired to one real signal.** A PR merge or revert appends one row to
   `state/persona-scores.jsonl` keyed by persona and PR sha, sourced from
   ADR-0008 ground truth (not self-report). Falsifiable: after the next merged PR
   with a review comment, the row exists within one gate run.
3. **Thompson allocation for one aspect.** Pick reviewers for exactly one aspect
   (e.g. security) by sampling reputation, not by static assignment. Falsifiable:
   `tools/review/panel.py run` names a different persona than the prior run at
   least once across 5 PRs with the same aspect active, or logs why not.
