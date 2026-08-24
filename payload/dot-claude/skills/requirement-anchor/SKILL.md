---
name: requirement-anchor
description: Extract a compact requirement-of-record + answer-map from a spec (PDF/eml/md/verbal) and gate read-before-build. Triggers on "/requirement-anchor", "anchor the requirement", "what is the real ask", "what are we actually building", "before building", or before producing any report/deliverable whose spec hasn't been anchored this session. SKIP when an anchor already exists for this deliverable in the current session and no new source has appeared.
model: sonnet
---

# Requirement Anchor — read before building

## When to invoke

- User said `/requirement-anchor` or "anchor the requirement" or "what is the real ask"
- A spec doc (PDF/eml/md/txt) was just shared or mentioned
- A new deliverable is requested and no anchor exists yet this session
- A previously built deliverable is being revised and the scope might have drifted

## Why this exists

The recurring failure mode is **build-before-reground**: shipping artifacts (reports, dashboards,
workbooks, agents) that don't map to the actual ask — built on the wrong corpus, wrong metrics,
wrong stakeholder — so reviewers ask "how did you get this / what does it mean" and the work
reads as noise. An anchor forces the question: *what is the real ask, in writing, before the
first line of code or query runs?*

Modeled on the CJA anchor at
`projects/campaign-analysis/docs/CJA-REQUIREMENT-OF-RECORD.md`.

## Protocol

### 1. Locate the source

Read the spec in full before producing anything. Source priority:
1. Named PDF / eml / md file — read it explicitly with Read tool; note page range if > 20 pages
2. Inline paste in chat
3. Verbal / reconstructed — extract from the conversation and flag as `[reconstructed — no written spec]`

If the source is a PDF, read pp.1–10 first; then read the section headings of the rest to decide
which pages add new requirements (don't dump the whole PDF into output).

If the source is an `.eml`, treat embedded screenshots as primary framing — review visually before
extracting requirements from HTML body text.

### 2. Produce the anchor

Output a block structured as follows. Aim for < 60 lines total. Concision beats completeness —
the anchor is a working reference, not a transcription.

```markdown
# <Deliverable name> — Requirement-of-Record

> Source: <file path or "[reconstructed]">, <date/version if known>.
> Sponsor: <name + role>. Owner: <name>. DRI for data: <name>.

## 0. Contract (non-negotiable)

| Rule | Decision | Why |
|---|---|---|
| … | … | … |

Include: canonical data source, deprecated sources to avoid, PII handling rule,
output format (decision-grade vs dashboard-dump), confidence labeling policy,
"one pipeline" constraint if applicable.

## 1. Business questions → answer map

| # | Question | Metric / method | Source | Answerable now? |
|---|---|---|---|---|
| 1 | … | … | … | Yes / Partial / No |
…

Mark each row: **Yes** (data on disk), **Partial** (needs a join / API call), **No** (model not built).
Do NOT invent answers — the anchor must reflect what's actually possible.

## 2. Data model & corpus locations

One paragraph: join key, core tables, on-disk paths for canonical dataset.

## 3. Data reliability rules

Bullet list: known quality issues, self-reported vs verified fields, exclusion rules
(weekends, recycled leads, false-labeled rows), any field semantic that differs from
what the name implies.

## 4. Output format contract

What shape does the answer take? (number + provenance + interpretation + owned action = LTMD gate)
Name any existing builder/script that must be extended rather than forked.

## 5. Open items (<date>)

Bullet list of unresolved gaps: missing data, unbuilt models, untranscribed spec pages,
portal/portal-access blockers. Each item is either answerable now or needs a human-gated
action — flag which.
```

### 3. Gate the build

After producing the anchor, state explicitly:

- Which business questions are **answerable now** (proceed)
- Which are **partial** (state what join/call is needed before proceeding)
- Which are **DIRECTIONAL only** (flag in the deliverable, do not present as ACTIONABLE)
- Which need a **human-gated action** — stop, add to the needs-you queue, do not build past them

Do not proceed to build any artifact until this gate is stated.

### 4. Anchor persistence

If an anchor file path is known or writable (e.g., `docs/<project>-REQUIREMENT-OF-RECORD.md`),
write the anchor there. Otherwise output it inline and note where it should be saved.
Do NOT create the file at `$HOME` — the HOME-as-repo anomaly means any write there is
potentially inside the axia-seekapa-cs-agents worktree.

## Output rules

- **No placeholder rows.** Every row in the answer map must be either real (extracted from the spec)
  or explicitly marked `[TODO — not yet transcribed]`. Never invent a question the spec doesn't ask.
- **Honest status.** If the spec says "Q12 needs a model not yet built", the anchor says `No`.
  Do not mark it `Yes` because the LLM could approximate it.
- **One anchor per deliverable per session.** If the user asks for a second deliverable from the
  same spec, re-use the anchor; don't re-run the full protocol — just state which questions from
  the existing anchor apply.
- **PII rule.** If the spec or data source contains real names/emails/phones, note it in section 0
  and flag the pseudonymisation step as a gate before any output.
- **Confidence labels.** Mark every metric either ACTIONABLE (commit budget) or
  DIRECTIONAL (guide investigation only). Metrics whose source is unverified, reconstructed,
  or derived from self-reported platform data are DIRECTIONAL by default.

## Anti-patterns

- Anchoring after the first query/code has already run (defeats the purpose — stop, regenerate)
- Writing the anchor from memory without reading the source file
- Including "nice to have" questions the spec doesn't ask
- Calling a partial metric ACTIONABLE because the join "should be easy"
- Forking an existing pipeline script rather than extending it (mention the canonical one explicitly)

## Integration with Forge Loop

This skill satisfies the **SPEC** axis (axis 1 of 8). The anchor file at
`docs/superpowers/specs/` counts as the spec if it references the source and includes the
answer map. A plan without an anchor passes PREMORTEM but fails SPEC — both must be present.

Path A step order:
```
1. /reground
2. /requirement-anchor  ← fires here, produces anchor + build gate
3. /plan + /premortem   ← only after anchor gate states "proceed"
4. TDD
5-8. (rest of Path A)
```
