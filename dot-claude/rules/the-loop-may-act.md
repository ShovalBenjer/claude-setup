# The autonomous loop acts, inside a named boundary

Global rule, set 2026-08-10 by explicit instruction. The operator was asked whether an
autonomous loop should PROPOSE or ACT, and answered "act".

## Why this file exists rather than a line in a plan

A one-word answer to a binary question carries a decision but no scope. Two days earlier,
in this same estate, "push, merge etc" was read as standing merge authority and a PR was
merged on green CI, which is why `merges-are-the-operators.md` exists. Recording "he said
act" without a boundary reproduces that failure with more surface area, because a loop
runs when nobody is watching.

So the answer is written down together with what it does not authorise. A future session
reading this gets both halves or neither.

## The loop MAY, without asking

- Run the gate, the oracles, and their selftests.
- Regenerate anything generated: `docs/CODEBASE-MAP.md`, `docs/DOCMAP.md`, prior-art
  freshness, ledger rows.
- Fix a red check on a branch it owns, and push that branch.
- Open a pull request, and rebase or merge main INTO its own branch.
- Append rows to `state/*.jsonl`.
- Write analysis under `docs/analysis/` and specs under `docs/specs/`.
- Read anything, including gitignored trees, using the methods `hidden-trees.md` names.
- Spawn subagents inside these same limits.

## The loop MAY NOT, ever, without a per-action answer

- **Merge a pull request.** `merges-are-the-operators.md` is unchanged by this rule and
  outranks it. Green CI authorises nothing.
- **Deploy, or touch production.** `production-means-merged-and-smoked.md` still binds.
- **Post outward**: a GitHub issue, discussion, review comment, a Jira comment, a message
  on any platform. A draft is work; sending it is the operator's.
- **Change the live `~/.claude` or `~/.codex` tree** without saying so in the same turn.
  The trees are payload in the repo and configuration on disk, and a silent live edit is
  invisible to every check the repo owns.
- **Delete or overwrite** anything it did not create in that same run. Including a ledger
  rewrite, a force push, a branch deletion, a `git reset --hard`.
- **Spend money**, or authorise a service that will.

## The reporting obligation that makes the boundary checkable

Every autonomous run leaves a row naming what it did and which side of the line each
action fell on. A loop whose actions are only visible in their effects is a loop nobody
can audit, and the operator's stated reason for wanting one is leverage, not mystery.
`calibrated-claims.md` applies unchanged: a run that could not measure something says so.

## What would change this rule

The operator widening or narrowing a specific item, named. Not an inference from a
general instruction, and not a session that went well. This file is the record; a
conversation is not.

Companion rules: `merges-are-the-operators` (who presses the button),
`production-means-merged-and-smoked` (what shipping means),
`calibrated-claims` (how a run reports), `accepting-architectures` (block by block).
