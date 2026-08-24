---
name: to-questionnaire
description: Turn a decision you can't fully answer into a questionnaire for someone else to fill in.
disable-model-invocation: true
---

# to-questionnaire

Turn something the user can't answer alone into a questionnaire: a Markdown document
handed to one person to fill in async, or filled out together in a meeting. The
recipient holds knowledge the user lacks; the questionnaire pulls it out of them.

The estate-specific case this exists for: a plan blocked on operator decisions. The
accepting-architectures rule produces named blocks awaiting an answer (the 2026-08-12
open-model plan has waited on blocks A to E since it was written); rendering those
blocks as one questionnaire gets five answers in one sitting instead of five sessions.
When the recipient is the operator, each question carries the recommendation and what
changes if he answers the other way, per that rule's register: he is deciding, not
approving.

Grill the send, not the subject. Interview the user only about the send, which they can
always answer:

1. **Who is it going to?** Role, expertise, relationship. Fixes tone and how much
   context the document must carry. For the operator, the answer is standing: senior,
   fast reader, wants the argument and the cost of being wrong, not a summary.
2. **What do you need back?** The specific decisions or facts the user cannot resolve
   alone. Done when there is a concrete list of what the user must walk away able to do.
3. **Write it** to `to-questionnaire-<slug>.md`, most-important-first (async means one
   pass), one idea per question, an answer stub under each, a one-line "why this
   matters" only where a question could be misread. Sections: Purpose, From/To/How
   answers are used, Context (one paragraph), How to answer (deadline, partial answers
   welcome), themed question sections, a closing "anything we didn't ask?".

Adapted 2026-08-23 from mattpocock/skills `productivity/to-questionnaire` (MIT).
Delta record: docs/analysis/2026-08-23-pocock-skills-delta.md.
