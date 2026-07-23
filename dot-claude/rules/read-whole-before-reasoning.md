# Read content whole before you reason over it (no silent truncation)

Global rule. Applies to every project and session. A correctness gate on how
content enters context. Companion to the bash-optimization tool policy in
CLAUDE.md (rtk-first, modern CLI tools like sed/mlr/head/tail).

## Trigger

Whenever you are about to read something you will then DRAW A CONCLUSION FROM: a
Jira ticket or its comments, a spec, a PDF/eml, a doc, a CRM payload, a production
resource scan, a diff you will review. Not shape-known scans where you already
know the structure (counting lines, first line of `git status -sb`, a grep for
existence).

## The rule

1. For content you reason over, read it WHOLE. Use the Read tool, or the
   `jira-read` skill for tickets (it flattens the full ADF: description, all
   comments, attachments, with no truncation), or a full API fetch.
2. Do NOT sample with a truncating filter (`sed -n`, `head`, `tail`, an `mlr`
   row limit, a byte cap) and then make a claim about the whole. A filter that
   drops rows silently produces a confident wrong answer, which is worse than an
   error, because nothing signals that content is missing.
3. Truncating filters are fine for known-safe scans: counting, first/last line, a
   grep for whether X is present. Never for "what does this say", "what are all
   the items", or "is X present" over content you have not fully read.
4. If you must cap for size, state what you capped and that the tail is unread.
   Never report a truncated read as full coverage.

## Why this exists

2026-07-08, Widgora / DEV-5062. A `sed` truncation of the Jira comments dropped
DEV-5076 (Market Overview + Quote Cards handoff) entirely and led to two wrong
production claims: "17 widgets" (prod actually had 43) and "the Arabic widgets do
not exist" (they did). The `jira-read` skill already flattens the full comment
thread with no truncation; the `sed` shortcut bypassed it. Reading the attached
screenshots plus a full prod scan corrected both mistakes. The bash-optimization
habit of truncating to save tokens is a scan tool, not a reading strategy for
content you will reason over.

## Enforcement checklist

- [ ] Content I will conclude from was read whole (Read / jira-read / full fetch).
- [ ] No `sed`/`head`/`tail`/row-cap feeding a claim about the whole.
- [ ] Any size cap is stated explicitly, with the unread remainder named.
