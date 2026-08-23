---
name: wait-what
description: "Stop. That last message did not land: re-pitch it."
disable-model-invocation: true
---

# wait-what

The operator's last-message interrupt. When invoked, the previous assistant message
failed: too long, too high, or built on context the operator does not share. Do not
defend it, summarize it, or apologize for it. Re-pitch it.

The re-pitch:

1. One sentence of context: what question the failed message was answering.
2. The answer itself, in the register the `explain-simply` skill measures (short
   sentences, common words, the numeric limits live there, not here). Name the actual
   things: the file, the number, the issue, never "the changes" or "the system".
3. What, if anything, is being asked of the operator, as its own final line. If
   nothing, say nothing is.

Hard rules: no new information that was not in the failed message, no bullet wall
rebuilt as a shorter bullet wall, and shorter than the message it replaces or it has
failed twice.

Why this exists as its own trigger when explain-simply already exists: explain-simply
fires when the operator asks for an explanation; this fires when a message already
shipped and missed. The ticket corpus carries the hand-typed versions: "explain to me
more simply you wrote a lot and i dont follow along" (PT-4c928a82ba4a), "what left you
tlaking to high for me" (PT-1cfc012d87e4), "note that everything you did here i dont
understand" (PT-a66b82775130).

Adapted 2026-08-23 from mattpocock/skills `productivity/wait-what` (MIT), which
re-pitches in ASD-STE100 against a CONTEXT.md; this version routes into the
explain-simply limits instead, so there is one measured definition of "simple" in the
estate. Delta record: docs/analysis/2026-08-23-pocock-skills-delta.md.
