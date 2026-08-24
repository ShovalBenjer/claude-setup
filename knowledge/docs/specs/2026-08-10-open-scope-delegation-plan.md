---
PRD: prd/autonomy-ecosystem.md
Ticket: SETUP-OS, AUTO
Status: active
---

# How the five open items get worked, and by whom

Written 2026-08-10 on instruction: "plan how you give 1-5 to efficient subagents to do
them, write it down in todolist." The five items are the ranked open scope from
`docs/analysis/2026-08-09-session-scope-ledger.md`.

This is a spec rather than five TODO rows because the boot surface shows six rows out of
133 and a five-worker plan does not compress to six lines. TODO.md carries one row that
points here.

## The two rules this plan runs under

The loop may act, inside the boundary in `~/.claude/rules/the-loop-may-act.md` (operator
decision, 2026-08-10). It may not merge, deploy, post outward, silently change the live
tree, delete what it did not create, or spend money.

Workers default to `claude-sonnet-5` via `CLAUDE_CODE_SUBAGENT_MODEL`, set this session
after finding that subagents had been inheriting the `opus-5[1m]` lead. Each worker
prompt below states a compact return shape. That is the deliberate answer to the
measured context problem, where 82 percent of usage came from subagent-heavy sessions:
a worker reads widely and returns a bounded report, so the breadth costs its context
rather than the lead's.

## What does not fan out, and why

Item 3, rebasing PRs 42, 47, 52 and 53, is the worst shape for a fan-out. Each is
`DIRTY` against main with 26 to 34 commits, so the work is conflict resolution, which is
a judgement about which side wins rather than a mechanical transform. Two workers in one
tree also collide on the index. If it is delegated at all, it is one worker per PR under
`isolation: "worktree"`, and even then the lead reviews every resolved conflict.

Items 2 and 5 collide with each other. A3 archives and moves directories under the repo
root while S3 lints `tools/`. Run concurrently, one rewrites what the other measures.
They are sequenced: A3 and A4 land and are committed, then the lint burn-down starts
from the tree that resulted.

Item 1 keeps its shape in the lead. The operator has just made the propose-or-act call,
and the design that follows from it is not something to discover in a worker's summary.
Its pieces do delegate.

## The assignment

| # | Item | Who | Model | Isolation | Returns |
| --- | --- | --- | --- | --- | --- |
| 1 | Autonomous loop | lead holds the shape; 3 workers on pieces | sonnet | none | see below |
| 2 | A3 archive and merge, A4 dead path | engineering-firm, 1 worker | sonnet | none | diff summary, gate verdict |
| 3 | 4 stale PRs | 1 worker per PR, or the lead | sonnet | worktree | conflict list plus resolution rationale |
| 4 | Context usage investigation | evidence-clerk, 1 worker | sonnet | none | 40-line measurement report |
| 5 | Style enforcement on `tools/` | qa-lab, 1 worker | sonnet | none | error census, then a burn-down branch |

### Item 1, decomposed

The loop needs three parts and they are independent enough to run at once:

1. **The trigger.** What wakes it. `CronCreate` exists, `tools/selfimprove/scan.py`
   already ranks what to pick up. Worker produces a wiring proposal naming the cadence
   and what it reads, not an implementation.
2. **The action allowlist, in code.** The boundary rule is prose; the loop needs a
   machine-readable form so an action outside it fails rather than relies on judgement.
   This is the same shape as `hookgate`, which denies force-push independent of what the
   model believes. Worker produces the allowlist and its oracle.
3. **The report row.** Every run leaves a row saying what it did and which side of the
   boundary each action fell on. Worker extends the existing ledger shape rather than
   inventing one.

The lead assembles these and writes the ADR.

### Item 4 is not just a measurement

The context question has a known partial answer already on disk: growth in this session
was structural, from long CI log greps, full file diffs read back, and background agent
reports. The worker's job is to turn that into a number per source across the 1218
transcripts in `~/.claude/projects`, and to say which sources are compressible. A finding
that names no fix is half the deliverable.

## Sequencing

```
now:        1a 1b 1c  |  4        (independent, parallel)
after 1:    2 (A3, A4), then 5    (2 and 5 collide, so 5 waits)
when asked: 3                     (needs a call on whether the drafts survive at all)
```

Item 3 is deliberately last. Three of those four PRs are drafts, the oldest has not moved
since 2026-08-06, and rebasing 34 commits of work the operator may no longer want is
effort spent before the question "do we still want this" has been asked.
