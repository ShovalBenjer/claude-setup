---
name: gemini-dialectic
description: Drive a real multi-turn conversation with Gemini via Claude in Chrome to brainstorm and plan, iterating until the position stabilizes (a measured stop condition, not a fixed round count or a vibe), then hand the stabilized candidates to /diverge and close with /heidegger-reflect. Use when the operator wants to think something through with another model rather than get a single answer, says "brainstorm this with Gemini", "multi-talk until we reach something", or "dialectic". Not for a single question with a single expected answer (use youtube-distill's one-shot pattern or a plain WebSearch instead).
---

# gemini-dialectic

A sustained back-and-forth with Gemini in a real Chrome tab, run until the
conversation's position actually stops moving, not until a round counter expires or
until it merely feels finished. Composes with two existing skills rather than
reimplementing what they already do: `/diverge` forces the stabilized output apart
into real candidates, `/heidegger-reflect` audits afterward whether the loop earned
its own conclusion.

## Why this is not youtube-distill with more steps

`youtube-distill` (dot-claude/skills/youtube-distill) is one round trip: one question,
one answer, distilled. This skill is a loop with state that persists across turns and
a real stop condition. Reuse its browser mechanics (`get_page_text`, not screenshots;
Gemini is read via a Chrome tab this session drives) but the shape underneath is
different, so it is a separate skill, not a flag on that one.

## The stop condition, and why it is not borrowed wholesale

Multi-agent LLM debate has real, dated prior art on when to stop (arXiv:2510.12697,
"Adaptive Stability Detection", 2025-2026): track a statistic round-to-round and halt
once it stays below threshold for two consecutive rounds, rather than running a fixed
round count. Their exact mechanism (a Kolmogorov-Smirnov statistic over a judge's
accuracy distribution) does not transfer here: this is an open-ended brainstorm, not
a graded judgment task, so there is no accuracy distribution to compute a KS statistic
against. What transfers is the *principle*, not the formula: measure something
concrete round-to-round, and stop on measured stability, never on a fixed count or on
"this feels done."

The concrete proxy for a brainstorm: after each Gemini reply, state in one sentence
what Gemini's position on the core question is right now. Compare it to the prior
round's one-sentence position.

- **Stable**: the position is the same claim in different words. Count it.
- **Moved**: the position added, dropped, or reversed a real claim. Reset the count.

Stop when stability holds for **2 consecutive rounds** (mirroring the paper's own
threshold, since two consecutive agreements is the minimum that rules out a single
lucky rephrase) or at **8 rounds**, whichever comes first. 8 is a ceiling against
runaway cost, not a target; the paper's own finding was most real debates stop between
round 2 and round 8, not that round 10 was ever worth reaching.

Log each round's one-sentence position and the stable/moved verdict as you go. This
log is the falsifiable record that the loop actually converged, not a claim of
convergence with nothing behind it (calibrated-claims.md).

## Procedure

1. **Frame before opening the tab.** State the actual question in one sentence and the
   two or three real constraints bounding it (excavate-before-building: what already
   exists that the question must not ignore). If the question is really "which of these
   options do I pick", stop here and run `/diverge` directly instead; this skill is for
   when the question itself is still being found, not when candidates already exist.

2. **Open Gemini in a fresh Chrome tab** (`tabs_create_mcp`, then `navigate` to
   gemini.google.com). Send the framing as the first message.

3. **Read the reply with `get_page_text`**, not a screenshot (cheap, exact, matches
   youtube-distill's own reasoning for the same choice). Extract Gemini's one-sentence
   position. This is a model's reading, not a source: nothing it says is quoted as
   fact without a way to check it, same discipline as youtube-distill's "pointer to go
   check, never evidence on its own."

4. **Respond with the sharpest disagreement or gap you actually have**, not a polite
   follow-up question. A dialectic that just asks "can you say more?" every round
   never moves; it has to push back on the specific weak point in what Gemini just
   said, or concede the specific point that was right and move to the next weak point.

5. **Repeat steps 3-4, updating the stability log each round.** Stop per the condition
   above.

6. **Hand off to `/diverge`.** The stabilized position (and the 1-2 genuinely
   unresolved disagreements the log surfaced, if any) becomes the "default" and the
   "real constraints" `/diverge` step 1 asks for. Do not let the Gemini dialogue
   itself pick the final direction: it produces the sharpened material, `/diverge`'s
   verbalized-sampling step and the operator's own pick are what actually decide.

7. **Close with `/heidegger-reflect`.** Run it against the whole exercise, not just
   the code that resulted. The honest-completion split is the right frame for a
   dialogue that might have stabilized on something wrong: WORKING = claims Gemini
   made that hold up on independent check; SCAFFOLDED = claims taken on Gemini's word
   with no independent check yet; MISSING = the disagreement that never actually
   resolved, named rather than quietly dropped.

## What this skill is not

Not a way to get a second opinion once and call it consensus (that is one round, use
youtube-distill's one-shot pattern or a plain question instead). Not a way to avoid
`/diverge`'s operator-picks-the-candidate step: this skill feeds that step better
material, it does not replace the pick. Not evidence: per
`dynamic-verification-trigger.md`, a named claim or attributed finding that surfaces
mid-dialogue still needs its own search-based check before it is repeated as fact,
the same bar as any other claim arriving from outside the immediate task.
