# Out-of-distribution output

The default output is the distribution's mode: the same UI, palette, copy, and
structure every other model instance on earth produces from the same brief.
Mode collapse is measured and prompt-resistant (2-8x diversity loss that "be
creative" does not recover; arXiv:2510.01171), so distinctiveness has to come
from process, not exhortation. Two levers work: sampling the tail explicitly,
and curating with a human taste corpus. This rule wires both into every
session.

1. The first idea is the mode, and the mode is forbidden as a final answer.
   Any UI, design, naming, copy, or visualization decision runs /diverge:
   five candidates with stated p_conventional, at least two below 0.3, the
   operator picks. A default that survives the comparison is allowed; one
   that was never compared is not.
2. Anchor to a real reference, never to latent memory: picks in
   docs/taste.md, the project's DESIGN.md, named galleries such as
   gameuidatabase, or the operator's own corpora. Name the anchor inside the
   artifact so the grounding is auditable.
3. Ban known modes by name in the brief: system-font and Inter/Roboto stacks,
   purple gradients on dark, the cream-and-serif house style, cookie-cutter
   component layouts. The frontend-design and dataviz skills carry the
   current avoid-lists; load them before the first line of UI or chart code.
4. Visual work is direction-first: propose two to four named directions, the
   operator picks one, and only then build. Lock the approved result into
   DESIGN.md so the next session inherits a decision instead of a vibe.
5. Prose has a native out-of-distribution anchor: the operator's fitted
   idiolect (voice-metrics, n=35,472 messages, measured 2026-07-29). Nobody
   else's model produces that distribution. Outbound text gets voice-metrics
   where it applies, and tools/slop_lint.py always.
6. Every pick lands in docs/taste.md with the one-line reason. /diverge reads
   the ledger before sampling, so taste compounds across sessions instead of
   resetting; the research position is that a human-curated corpus is the
   state of the art, because no automated taste model works yet.
7. The clamp: out-of-distribution is grounded distinctiveness, not novelty
   for its own sake. prior-art-gate still blocks unsourced novelty claims,
   and a tail candidate that loses to the simplest correct option on measured
   grounds loses.
