# Architectures and plans are accepted block by block, never wholesale

Global rule. Binds every project and session. Born 2026-08-05, when a complete
hiring-engine architecture was delivered as one finished picture with three
diagrams, four tables, and roughly forty numbers. The operator's response: "There
are a lot of numbers and mini decisions that need to be reasoned. Iterate block by
block, reason over it, and ask me questions to ensure I accept."

## The failure this prevents

A finished architecture is not a proposal, it is a fait accompli wearing a
proposal's clothes. Every diagram encodes decisions that were never put to
anyone: which arm to start with, what a number means, which of two contradicting
documents won, what got left out. Presenting them together buries each one in the
others. The operator can say yes to the whole and still not have agreed to any
part of it, which is how a plan gets "approved" and then re-litigated in
implementation.

The tell is volume. If a deliverable carries more decisions than a person can
hold at once, the acceptance it gets is a vibe, not a decision.

## The method

1. **Decompose before presenting.** Split the architecture into blocks that can
   each be accepted or rejected independently. A block is one subsystem, one
   data flow, one measurement, or one contested choice. If two things cannot be
   accepted separately, they are one block.

2. **One block at a time. Stop and wait.** Do not present block two before block
   one is accepted. Do not batch every question into a list at the end; a list at
   the end is the same fait accompli with a questionnaire stapled on.

3. **Each block carries five things, in this order:**
   - **What it is**, in one or two sentences.
   - **The numbers, with the command that produced each.** A number without its
     provenance is not evidence, and this is where an architecture most often
     smuggles a guess.
   - **The decisions inside it**, named. Including the ones that look like
     description. "Discovery runs daily" is a decision about cadence.
   - **What was rejected**, and on what grounds. A block with no rejected
     alternative was not designed, it was transcribed.
   - **The question**, singular where possible. What would change if the operator
     answered the other way.

4. **Ask with the question tool, not with prose.** A question buried in a
   paragraph reads as commentary. Offer the real options, including the one the
   author does not favour, and say which is recommended and why.

5. **Record acceptance per block, with its date.** An accepted block is closed:
   do not reopen it in a later session without new evidence. An unanswered block
   stays open and visible rather than being quietly implemented under an assumed
   answer.

6. **Do not implement past an open block.** Work that depends on an unanswered
   question waits. Work that does not depend on it proceeds, and the report says
   which is which.

## What counts as a block worth stopping on

- A number that drives a choice (a threshold, a floor, a cap, a rate).
- Any place two sources disagree and one was picked.
- Anything marked broken, missing, or unknown, because the operator may know why.
- An ordering decision (which arm first, which phase first).
- Anything outward-facing, or anything spending money.
- A deliberate omission. What was left out is a decision and usually an invisible
  one.

## What does not need a block

Mechanical consequences of an already-accepted block. If the cadence is accepted,
the cron expression is not a separate question. Splitting those out is padding,
and padding trains the operator to skim, which defeats the whole rule.

## The register

Reason out loud before asking. The operator is deciding, not approving: he needs
the argument, the counter-argument, and what it costs to be wrong, not a summary
and a yes/no. State the recommendation and the reason for it; a question with no
recommendation is work handed back.

Where a block's evidence is thin, say so in the block rather than in a caveat at
the end. `VERIFIED`, `STAGED`, `ASSUMED`, inline, per the calibrated-claims rule.

## Companion rules

`calibrated-claims` (evidence class on every claim), `docs-control-plane` (where
the accepted architecture lands), `repo-stack-reasoning` (the whole-repo model
that a block is reasoned inside), `premortem` (failure modes before code).
