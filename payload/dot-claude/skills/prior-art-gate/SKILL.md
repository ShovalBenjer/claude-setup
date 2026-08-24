---
name: prior-art-gate
description: "Simpsons did it already. Before claiming anything is novel, missing, unsolved or a gap, run a prior-art search and log it. Blocks unsourced novelty claims. Triggers on /prior-art-gate, 'is this novel', 'nobody has built', 'there is no benchmark', 'gap in the literature', or whenever a claim of absence is about to be written down."
---

# Prior-art gate

**Purpose:** stop confident claims of absence. A claim that something does not
exist is an empirical claim about the world, and it is the easiest kind to get
wrong, because the evidence for it is invisible by construction.

Named after the South Park bit: you cannot propose an original plan without
someone pointing out the Simpsons did it already. Better to be that someone
yourself, before you build on the assumption.

## When it runs

- Before writing any sentence asserting novelty, absence, or an unsolved gap.
- Before a curriculum unit teaches that something is an open problem.
- Before a research direction is chosen on the grounds that nobody has done it.
- Automatically, via `hooks/prior_art_gate.py` on Stop.

## Protocol

1. **State the claim as a falsifiable sentence.** "No benchmark evaluates X over
   Y" is checkable. "X is under-explored" is not; sharpen it or drop it.

2. **Run at least three searches with different vocabulary.** Fields name the
   same problem differently. Use the academic term, the practitioner term, and
   the product term. One search that returns nothing is not evidence.

3. **Look for the four not-a-gap signals**, in decreasing strength:

   | Signal | What it means |
   |---|---|
   | A survey paper exists | Settled. There was enough work to survey. Claim is dead. |
   | A curated awesome-list exists | Crowded. The field has enough artifacts to index. |
   | A recurring workshop exists | Incubating, not absent. It has a community. |
   | Three or more benchmarks share a name for the problem | Named problems are not gaps. |

4. **If any signal fires, the novelty claim is refuted.** Say so plainly, name
   what you found, and retract. Do not narrow the claim to rescue it in the same
   breath. If a narrower gap genuinely survives, state it separately and label
   it a hypothesis requiring its own check.

5. **Log the search.** Record the exact queries used and the date, next to the
   claim. An absence claim without a logged search is an assumption wearing a
   fact's clothes.

## Output

Append to the artifact that carries the claim:

```
PRIOR ART, checked YYYY-MM-DD
  queries: <the exact strings used>
  found:   <survey / awesome-list / workshop / benchmarks / nothing>
  verdict: REFUTED | SURVIVES
  residue: <the narrower claim that survives, if any, labelled hypothesis>
```

## Worked example, 2026-07-27

Claim written: "no current benchmark tests an agent over a multi-day session
with persistent memory."

One search refuted it: LoCoMo, LongMemEval, BEAM, MOMENTO, Memora, MemoryArena,
STALE, PersistBench, StreamMemBench and more, plus a survey, "Always-On Agents"
(arXiv 2606.30306), and a taxonomy paper. Survey signal fired. **REFUTED.**

Residue, labelled hypothesis: memory benchmarks test recall across sessions,
long-horizon benchmarks test task completion; an agent doing sustained *work*
across days may still be thin. Needs its own check before anyone believes it.

## Relationship to other checks

- `/heidegger-reflect` asks what was concealed after the fact. This asks what is
  already known before the claim is made. Reflection catches it late; this
  catches it early.
- `completion_gate` blocks completion claims without executable evidence. Same
  shape, different target: that one guards "it works", this one guards "it does
  not exist".
