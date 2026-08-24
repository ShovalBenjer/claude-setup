---
name: diverge
description: Anti-convergence for any design/creative/architecture decision. Forces verbalized sampling (candidates WITH conventionality probabilities) so output does not collapse to the obvious/mode. Deep Work Protocol rule 5-6, ADR-0005.
---

# /diverge — break output convergence

Output convergence (mode collapse) is a MEASURED failure of LLMs, not a vibe:
homogenization studies show 2-8x less diversity than humans, and it is prompt-
resistant. The research-backed fix is Verbalized Sampling (arXiv:2510.01171):
elicit a DISTRIBUTION of candidates with their probability of being the conventional
choice, then deliberately mine the low-probability tail. This command enforces it.

Use before committing to any non-mechanical decision: an API shape, a design, an
architecture, a naming, a plan, a piece of copy. Do NOT use for mechanical edits.

Procedure (do all steps, do not shortcut to one answer):

1. **Name the default.** State the obvious/first-association solution explicitly, and
   the 2-3 hard constraints from the REAL context (existing vocabulary, excavated
   artifacts — the excavate-before-building rule). The default is now forbidden as the
   final answer unless it survives step 4.

2. **Verbalized sampling.** Produce 5 distinct candidates. For EACH, give:
   - the candidate (one line),
   - `p_conventional`: your estimated probability (0-1) that this is the typical/expected choice,
   - the one thing it does better than the default.
   Order them by `p_conventional` ASCENDING (weird first). At least 2 must have
   p_conventional < 0.3 (genuinely non-obvious) or you have not diverged.

3. **Defixation check.** For the 2 lowest-p candidates, ask: what constraint made this
   look wrong, and is that constraint real or inherited? Kill inherited constraints.

4. **Operator picks.** Present the 5 with an AskUserQuestion (previews where visual).
   The operator chooses; do not choose for them on a taste decision.

5. **Record taste.** Append the pick AND the one-line reason to `docs/taste.md`
   (create if absent). Future creative tasks read it — this is how the personal taste
   model accumulates (the research says no automated taste model works yet; the human-
   curated corpus is the state of the art).

Output: the 5-candidate table, the AskUserQuestion, and the taste.md append. Never a
single un-sampled answer.
