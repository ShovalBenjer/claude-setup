---
name: decision-grade
description: "Claim-level linter/gate that extends LTMD. Rejects any report or deliverable where any claim lacks: a number with provenance (query/source), an interpretation (what it means for the decision), and ONE owned+dated action tagged ACTIONABLE or DIRECTIONAL. Returns a per-claim verdict table, a document-level pass/fail, and the minimal diff to make it decision-grade. Triggers on /decision-grade, 'is this decision-grade', 'can we ship this', 'gate this report', before shipping a stakeholder deliverable."
model: opus
---

# decision-grade — claim-level linter

Extends LTMD's document-level test down to **individual claims**. A document can pass LTMD
(has an owned action at the end) and still mislead, because the supporting claims may be
unnumbered, unsourced, or uninterpreted. This skill audits each claim atomically.

## When to use

- Before shipping a report, deck, or analysis to any stakeholder.
- When the user says "/decision-grade", "is this decision-grade", "can we ship this", "gate this report".
- After /LTMD passes — LTMD gates the document, this skill gates the claims inside it.
- When a claim has a number but no query behind it, or a source but no "so what".

## SKIP when

- The content is code, config, or a test — not a stakeholder deliverable.
- The content is already a raw data dump explicitly labeled as an appendix.
- The user says "skip decision-grade" or "no gate" explicitly.

## The four-part claim contract

Every claim in a stakeholder document must satisfy all four, or it fails:

1. **NUMBER** — a quantified value (%, $, count, rate, ratio, time). Directional prose without
   a number ("conversion improved") is not a claim, it is an opinion.

2. **PROVENANCE** — the query or source that produced the number. Minimum: table name + filter,
   SQL snippet, dashboard name + date, or a named export file. "Internal data" is not provenance.

3. **WHAT-IT-MEANS** — one sentence stating the business interpretation for this decision.
   "Recall is 0.74" is not what-it-means. "At 0.74 recall we miss 1 in 4 churn signals before
   the retention window closes" is.

4. **ACTION** — ONE owned, dated action, tagged one of:
   - `ACTIONABLE` — can execute now, owner named, deadline set.
   - `DIRECTIONAL` — not executable yet (missing data, pending approval, or blocked), but
     explicitly named as such with the blocker stated.

   A claim with two actions is a claim that hasn't been decided yet — split it.

## Verdict labels

Per claim:
- **PASS** — all four parts present.
- **NO-NUMBER** — opinion or proxy without a quantified value.
- **NO-PROVENANCE** — number present but query/source missing.
- **NO-INTERPRETATION** — number + source but "what does this mean for us" is absent.
- **NO-ACTION** — number + source + interpretation but no owned+dated action.
- **AMBIGUOUS-TAG** — action present but not tagged ACTIONABLE or DIRECTIONAL.

Document-level:
- **DECISION-GRADE** — every claim passes.
- **NOT-DECISION-GRADE** — one or more claims fail. List which, with the specific missing part.

## Output shape

Produce this, in order:

### 1. Document verdict (one line)
`DECISION-GRADE` or `NOT-DECISION-GRADE — N claims fail (list: claim IDs or short labels)`.

### 2. Claim table

| # | Claim (shortened) | Number | Provenance | Interpretation | Action | Verdict |
|---|---|---|---|---|---|---|
| 1 | "Conversion rate fell..." | 12% → 8% | ✓ SQL: cohort_funnel WHERE... | ✓ | ACTIONABLE ✓ | PASS |
| 2 | "Engagement improved" | ✗ | — | — | — | NO-NUMBER |

Use ✓ / ✗ per cell. If a part is present but weak, use ✓? and note why below the table.

### 3. Repair diff (only for failed claims)

For each failing claim, one concrete patch — the exact sentence or data point to add — not
a general instruction. Example:

> Claim 2 — add: "Engagement (session depth) rose from 2.1 to 3.4 pages/visit (source:
> GA4 export 2026-06-08, segment: paid-social). Action: DIRECTIONAL — validate against
> server-side events before acting; owner: [analyst], blocker: GA4/server reconciliation
> pending by 2026-06-15."

### 4. ACTIONABLE vs DIRECTIONAL summary

List all ACTIONABLE items (executable now) and all DIRECTIONAL items (blocked, with blockers)
so the decision-maker sees at a glance what is ready vs what needs pre-work.

## Rules

- Audit every numbered claim, not a sample. If the document has 30 claims, the table has 30 rows.
- A number cited without a date is weak provenance — flag it ✓? and note "date missing".
- "Owner: team" is not an owner. A name or a role tied to one person is.
- A deadline of "soon" or "next quarter" is not a deadline. A calendar date or sprint ID is.
- Confidence bands and what-if ranges count toward NUMBER if present; their absence should be
  flagged in the interpretation cell for any forecast claim.
- Do not rewrite the document. Produce the repair diff; the author applies it.
- No emojis in the table. Plain ✓ / ✗. Bottom-line first.

## Relationship to LTMD

LTMD asks: "Does this document produce a dollar-valued owned action?" — one test, document-level.
decision-grade asks: "Does every claim that supports that action hold up under scrutiny?" — four
tests, claim-level. Run LTMD first; if it fails, fix the document shape. Run decision-grade after;
if it fails, fix the evidence layer. A document that passes both is shippable.
