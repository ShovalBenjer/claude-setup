---
name: feature-investor
description: Grade a feature, epic, or product concept against a strict 2026 SOTA investment bar with numeric scores, hard rules, and a go/no-go verdict. Use when deciding whether something is worth building, continuing, or investing engineering weeks in.
---

# Feature Investor

Use this skill to grade a feature, epic, or product concept against a strict 2026 SOTA bar before you invest engineering weeks in it. Output is one-page: numeric scores, hard rules, verdict.

## When to invoke

- A new spec, epic, or PR labeled `feature` is drafted.
- The Weekly Engineering Update routine runs and lists newly-shipped or proposed work.
- Before the night-mode autonomous run picks up an "investigate X" task longer than a day.
- Any time the user says "is this worth building" or "should I keep going on this".

## Inputs

The skill accepts any of:

- A spec markdown file path
- A short concept paragraph
- A commit-cluster (e.g. last 30d of a repo) for retroactive scoring
- An epic / work-item link

## Scoring axes (0-100 strict scale)

1. **Market demand** — is willingness-to-pay validated, or are you assuming demand?
2. **IP / copyright safety** — do you own the data/content/code you build on, or is it a licensing landmine?
3. **Regulatory safety** — does this enter regulated territory (finance, medical, legal, employment, advice) without compliance plumbing?
4. **CAC realism** — is acquisition cost modeled on contribution margin, or wishful thinking?
5. **Retention / churn** — does the user have a reason to stay past month three?
6. **Product moat** — `data | distribution | network | brand | regulatory | none`. None = race to the bottom.
7. **Reliability ceiling** — is plain RAG / wrapper-on-LLM enough, or does production demand more?
8. **Revenue realism** — does the ARR projection have evidence, or is it template math?
9. **Technical feasibility** — buildable in the time you actually have?
10. **Distribution channel viability** — does the chosen channel (B2B prop firm, app store, marketplace, direct) survive the next 18 months of platform/regulatory shifts?

Aggregate score = weighted mean. Default weights: IP 1.5x, regulatory 1.5x, moat 1.5x, retention 1.2x, demand 1.2x, others 1.0x.

## Hard rules (override numeric score)

- **Commoditization risk >= 8** AND **moat == none** -> verdict: `drop`. You will lose to OpenAI/Anthropic/Google's next quarterly release.
- **IP score < 30** -> verdict: `drop` or `pivot to licensed/original corpus`. Copyrighted source data on a commercial product is a startup-killer.
- **Regulatory score < 35** AND product touches finance/medical/legal advice -> verdict: `pivot to tooling` (analytics, journaling, internal training) not advice.
- **LTV >= 7** AND moat in `[data, distribution, regulatory]` -> verdict: `invest` even at high effort.
- AI-wrapper product with no proprietary data, distribution, or workflow integration -> auto -3 LTV.
- Hebrew/Arabic/Levant market vertical (sales/compliance/QA training, regulated call center) -> +2 LTV (your verticals).
- B2B internal-training tool for an existing customer -> +2 retention.

## Verdict categories

- `invest` — clear path, build it.
- `pivot` — same problem, different shape (e.g. analytics not advice; original corpus not licensed text).
- `hold` — score is borderline; revisit in 60 days with stronger evidence.
- `drop` — fundamental flaw (IP, regulatory, no-moat).
- `open-source-and-share` — buildable but not commercializable; ship as OSS for credibility.

## Output template

Write to `~/.claude/docs/FEATURE_INVESTOR_<slug>_<date>.md`. Append an event to `~/.codex/agent-control/events.jsonl` with kind `feature.scored`.

```markdown
# Feature Investor — <name>

Date: <YYYY-MM-DD>
Aggregate: <NN>/100   Verdict: <invest|pivot|hold|drop|open-source>

## Scores
| Axis | Score | Why |
|------|-------|-----|
| Market demand | NN | one line |
...

## Hard rules tripped
- (list any that fired)

## Bottom line (3 sentences)
<the strict version, no flattery>

## What could work instead (if pivot/drop)
- option 1
- option 2
- option 3
```

## Worked example — Trading-Mentor concept (April 2026)

Inputs: `~/vibe-coder-slop/Understanding-{1..5}.pdf.json` (forex book OCR) + audit PDF.

Verdict: `drop` (or `pivot to original-corpus tooling`).

Scores: market 45, IP **20** (copyrighted book corpus), regulatory **25** (FINRA-adjacent), CAC 30, retention **20** (retail-trader churn), moat 35 (RAG-over-book is replicable), reliability 55, revenue 30, tech 55, channel **20** (prop-firm shakeout). Aggregate **34/100**.

Hard rules tripped: IP < 30 -> drop; regulatory < 35 in finance -> pivot-to-tooling; moat == none-meaningful -> drop reinforced.

What could work instead: licensed B2B broker training; original chart-pattern simulator; analytics/journaling product (not advice).

This worked example is the canonical reference for what a "drop" verdict looks like. Re-use the structure for new evaluations.

## Anti-patterns to flag automatically

When a user feeds the skill any of the following, raise a preflight warning:

- Multiple PDFs of unrelated content as "architecture context" (the vibe-coder-slop pattern: 45MB of book-OCR JSON dumped as if it were a spec)
- "It's like X but with AI" without a moat claim
- Revenue projections without a comparable benchmark
- "Just add disclaimers" as the regulatory plan
- Architecture diagram with no input/output schema

## Notes

- The skill draws explicitly on lessons from the 2026-01-15 claude-orchestration `AUTOMATION_GAP_ANALYSIS.md`: infrastructure existence is not the same as a working product.
- The skill reads the user's repo trust tiers from `~/.codex/agent-control/repos.toml` and applies +1 retention to features extending owned-clean repos with existing customers.
- The skill does not auto-act. It writes the verdict and stops. The user decides.
