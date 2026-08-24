---
name: wayfinder
description: Draw the map before picking work. Names the destination, the fog, and the frontier across TODO.md, claims, selfimprove and Zion.
disable-model-invocation: true
---

# Wayfinder

Four surfaces already answer "what should I work on" and they disagree: `TODO.md`,
`state/claims.jsonl`, `tools/selfimprove/scan.py`, and the Zion board. This picks
one destination from all four and states what is still **fog**.

Reachable by hand only. It costs no context load and is listed in `skillmap`.

## The four positions

**Destination** is the one outcome this session moves toward, written as an
observable state rather than an activity. "The gate certifies a committed tree"
is a destination; "work on the gate" is not.

**Fog** is what is unknown, and it has a sharpness test that decides where the
boundary sits: can you state the question precisely *right now*, without
answering it? A sharp question is on the frontier and claimable. A question you
cannot yet phrase is fog, and the work is to sharpen it, not to solve it.

**Frontier** is open, unblocked, and unclaimed. All three, checked against
`state/claims.jsonl` rather than assumed. A row someone else claimed is not
frontier however available it looks.

**Settled** is closed and never reopens. Recording a thing as settled is what
stops the same question being re-derived every session, which is the cost the
fog-of-war measurements keep finding.

## Steps

1. **Read the four surfaces and write down where they disagree.**
   Completion: every disagreement named with both values, for example a TODO row
   marked done whose artifact is absent. Agreement is also a finding; say so.

2. **Sort each open item into frontier, fog, or settled** using the sharpness
   test above.
   Completion: every open item carries exactly one position, and each fog item
   carries the question it is waiting on.

3. **Pick one destination and claim it.**
   Append the row to `state/claims.jsonl` before starting, with a falsifier that
   an independent reader could run. One destination per session.
   Completion: the claim row exists and its falsifier names a command.

4. **State the mode.** HITL when the operator's judgement is inside the loop
   (taste, spending, publishing, replacing live content). AFK otherwise.
   Completion: mode named, and for HITL the specific decision named with it.

5. **Record what moved to settled**, with the evidence that settled it.
   Completion: each settled item names the command or artifact, so the next
   session inherits a decision rather than a vibe.

## Reading each surface

`TODO.md` carries intent and goes stale fastest; a `[x]` means someone believed
it, not that it holds. Treat a checked row as a claim to verify.

`state/claims.jsonl` is the only authority on who holds what. Append-only, so
the last row for an id wins.

`tools/selfimprove/scan.py` ranks by its own heuristic. Useful for surfacing
what you forgot, weak evidence about priority.

The Zion board (`ShovalBenjer/claude-setup` issues, project 3) holds the epics.
Reading board columns needs the `read:project` scope, absent from the current
token, so treat column state as fog until `gh auth refresh -s read:project` runs.

## When the map is wrong

A destination that turns out to be fog mid-session is the normal case. Move it
back to fog, write down the question that was not sharp, and pick again. The
record of a wrong turn is worth more than a clean map, because it names a
sharpness failure that will otherwise repeat.
