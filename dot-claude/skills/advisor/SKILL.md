---
name: advisor
description: "Fast confidence-restoring research pass for when Claude (or the user) is NOT confident about an external, current, or SOTA question. Spawns a scoped web-research sub-agent, restricts to trusted same-day sources (peer-reviewed / official / primary), and returns a dated recommendation with confidence and citations. Triggers on /advisor, 'get advice', 'what's the SOTA', 'is this still true', 'am I confident', 'check current best practice', 'latest release of X', 'not sure, look it up', or whenever the model's own confidence on an external fact is low. SKIP for local state (use reground), simple 1-2 search lookups (use WebSearch), debugging (standard tools), or a full multi-phase cited report (use deep-research)."
model: opus
---

# Advisor

A fast, cited second opinion for the moment you are NOT confident about the outside
world. It answers ONE question against current, trustworthy sources and hands back a
dated recommendation you can act on. It is the external-facing counterpart to
`/reground` (which grounds you in local state).

## When to use

- Your own confidence on an external or factual question is low: "is this still the
  SOTA?", "did that API change?", "which library is current?", "is this claim true?".
- The right decision depends on current best practice or a recent release, not on the
  repo in front of you.
- You are about to build on an assumption about the outside world that you cannot
  verify from the codebase.

## When NOT to use

- Local/state uncertainty (branch, spec, artifacts): use `/reground`.
- A fact you can settle in one or two searches: just use WebSearch.
- Debugging local code: standard tools.
- A comprehensive, long-form cited report: use `/deep-research` (advisor is the quick
  pass, not the 20-page deliverable).

## Grounding (why it works this way)

- Trigger discipline: Anthropic, "Trustworthy agents in practice" (2026-04-09) -- an
  agent should "know when to stop and ask for clarification when it's uncertain, or
  when it's about to make a mistake," and pause rather than assume. Advisor is that
  pause turned into an action.
- Research mechanics: Anthropic, "How we built our multi-agent research system"
  (2025-06-13) -- a lead spins up 3-5 subagents in parallel, effort scales to
  complexity ("simple fact-finding requires just 1 agent with 3-10 tool calls"), and a
  citation pass attributes every claim to a source.

## Procedure

1. **Frame ONE question.** Write the single thing you are unsure about and what a good
   answer unblocks. If you have several, run the most decision-blocking one first.
2. **Stamp the day.** Anchor to today's actual date (the injected `currentDate`, or
   `date -u +%F`). The answer must reflect that exact day, so recency is mandatory.
3. **Spawn the research pass.** Use the Agent tool (`general-purpose`, or the
   `deep-research` skill for a wider question) with WebSearch + WebFetch. Scale effort
   to complexity: a quick check is 1 agent / 3-8 searches; a wide or critical question
   is 3-5 parallel subagents, each on a distinct sub-angle. Do not fan out for a simple
   fact.
4. **Restrict to trusted sources (hard rule).** Accept only:
   - Tier 1: peer-reviewed journal articles (verify DOI + publisher), official primary
     docs (the vendor / standards body that owns the thing), primary data.
   - Tier 2: moderated preprints (arXiv/bioRxiv -- check the `journal-ref`/`doi` fields
     to see whether a peer-reviewed version exists), conference papers, and engineering
     posts from the primary source (the team that shipped it).
   - Reject: content farms, undated SEO blogspam, AI-generated aggregators, unverifiable
     secondary summaries, forum hearsay presented as fact.
   - For an academic claim, currency/retraction check via Crossref
     (`api.crossref.org/works/<DOI>`) or the Retraction Watch database. Do not trust a
     model's own retraction judgment (2026 studies show generic AI tools miss retracted
     literature).
5. **Force that-exact-day recency.** Put an explicit date or version in the query;
   prefer sources showing a visible publish/updated date; for fast-moving topics use the
   search "past day / past week" filter but CROSS-CHECK the page's own dateline (engine
   "recent" filters reflect crawl time, not publish time). If nothing current exists,
   say so plainly -- do not pad with stale sources. (Perplexity Sonar's model of this is
   a `recency=hour|day|week|month` param plus domain allow/block; approximate it with
   WebSearch `allowed_domains` + a date string + a byline check.)
6. **Verify.** Two or more independent trusted sources per load-bearing claim. Flag any
   single-sourced or contested point.

## Output (short, dated, decision-grade)

```text
ADVISOR -- <YYYY-MM-DD>
Question: <the one question>
Bottom line: <recommendation> | confidence: high|medium|low | why: <one clause>
Evidence:
- <URL> (<publish/updated date>, tier 1|2) -- <the one fact it supports>
- <URL> (<date>, tier) -- <fact>
- <URL> (<date>, tier) -- <fact>
Caveats: <what is contested, stale, single-sourced, or unverifiable>
Next action: <one concrete step>
```

## Rules

- No em-dash, no emoji, no AI-slop register. Every claim carries a source.
- State confidence honestly. If the trusted-source bar cannot be met, return
  "insufficient trusted evidence, do not build on this yet" rather than guessing.
- Keep it tight. This is advice, not a report. If it grows past a page, you wanted
  `/deep-research`.
- If the recommendation feeds a stakeholder decision, gate it through `/decision-grade`
  or `/LTMD` before shipping.

## Relationship to neighbors

- `/reground` -- internal/local state. `/advisor` -- external/world state.
- `/deep-research` -- the heavy multi-phase cited report; advisor is the fast pass.
- `/decision-grade`, `/LTMD` -- turn an advisor recommendation into a decision-grade one.
