---
description: Reconcile this session against measured repo state before planning or claiming scope. Runs the inventory sweep and reports what is stale, refuted, unread, or drifted.
argument-hint: [lite|full] [optional focus]
---

# reground

Re-establish ground truth from disk and from the ledgers, not from memory and not
from what a doc asserts.

Rewritten 2026-07-29. The previous body dispatched to a SKILL.md under a Linux home
directory from another machine, a path that has never existed here, and the command
was not deployed to `~/.claude/commands` at all, so typing `/reground` produced
nothing. The literal path is left out of this file on purpose: writing it down would
make this document itself a dead-pointer hit in `tools/audit/pointers.py scan`, which
is the L-2026-07-29-d class where recording a fix reads as the defect. The session
that found this had just
presented a "full scope" plan built from `TODO.md` plus its own working memory,
having read none of the sources below (lesson L-2026-07-29-h).

## Run these. Do not skip one because you think you know its answer.

```bash
cd ~/claude-setup

python tools/bus/bus.py log | tail -25   # cross-lane history; does NOT consume
python tools/bus/bus.py inbox            # unread for THIS lane; advances a cursor
python tools/selfimprove/scan.py         # ranked backlog
python tools/refute/refute.py run        # every claim's own falsifier (slow)
python tools/audit/skills_sync.py check  # repo-vs-live drift
python tools/audit/pointers.py scan      # hooks and skills that are dead paths
python tools/map/codemap.py check        # directory purposes and map freshness
python tools/gate/gate.py status         # whether THIS tree has ever been gated
git status --short                       # who else is writing this tree
```

Then read, because a plan is wrong without them:

- `CLAUDE-OS.md` layer map and supersession table
- `docs/charters.md` for your lane, `state/claims.jsonl` for what is already claimed
- `state/lessons.jsonl` open rows. These are failure CLASSES: check whether the thing
  you are about to build repeats one
- `TODO.md` in full, including sections other sessions appended today

## Reporting rules

- `inbox` ADVANCES A CURSOR, so reading consumes. Capture what it returns in the same
  turn, or use `log`, which does not consume.
- A broken verifier is not a pass. The claim stays unknown, and unknown is a finding.
- Name the sources swept AND the ones skipped. A scope claim with no coverage
  statement is the defect this command exists to prevent.
- This command reads. Do not modify files, commit, push, call cloud APIs, or start
  services from it. Fixes are a separate decision with a separate approval.

## Focus argument

If `$ARGUMENTS` is non-empty, run the sweep anyway, then prioritise matching TODO
rows, lessons, claims, bus messages and specs in the report. `lite` may skip
`refute.py run` and `skills_sync check`, the two slow ones, and must say in the
report that it skipped them.
