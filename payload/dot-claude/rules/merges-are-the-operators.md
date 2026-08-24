# The operator accepts merges, not the assistant

Global rule, set 2026-08-09 by explicit instruction: "after reviewers allow and their
github comments resolved from my end i accept merge, as a rule global also."

## The rule

A pull request is merged by the operator. Never by the assistant, and never because the
checks went green.

Green CI is a precondition, not an authorisation. The gate says the code is defensible;
it does not say the change is wanted, correctly scoped, or timed for now. Those are the
operator's judgements and merging removes his chance to make them.

Two conditions must both hold before he will look at it, and both are the assistant's job
to reach:

1. **Every reviewer has allowed it.** All required checks pass, and the review bots that
   comment (Claude Code Review, Gemini, Kilo, and any human reviewer) have finished.
   A pending reviewer is not an allowance.
2. **Their GitHub comments are resolved.** Each review comment is either fixed in a commit
   or answered on the thread with the reason it is not being changed. An unresolved
   comment left for the operator to read is work handed back to him.

Then say the PR is ready, name what the reviewers raised and how each was resolved, and
stop. He merges.

## What this does not change

- ADR-0012 still stands: work ships through a PR, never a push to the deploy branch. That
  rule governs how a change reaches main; this one governs who presses the button.
- `pre_push_gate.py` still asks on a push aimed at main or master. Belt and braces, and
  the two exist for different reasons: the hook stops a mechanical mistake, this rule
  reserves a decision.
- Pushing a feature branch, opening the PR, fixing what reviewers find, and re-pushing all
  remain the assistant's work and need no approval.

## Why it was written

2026-08-08. PR #55 was merged by the assistant after checks went green, on the strength of
the operator having earlier written "push, merge etc" in a list of things to do. That was
a reading of a general instruction as standing merge authority. The merge itself caused no
damage and the branch was sound, which is exactly why the correction is worth recording:
the rule is about who decides, not about whether that particular decision was right.

Companion rules: `production-means-merged-and-smoked` (merged is only the first of three
things "production" requires), `calibrated-claims` (a green run is evidence about the
tree, not about the decision).

## Widened 2026-08-12: standing auto-merge on reviewed-and-resolved

Operator instruction, this date, verbatim: "i auto merge if all reviewers which are
resolved" (clarifying his earlier per-PR wording "if reviewers approved and all
commenting resolved - merge"). On the operator's OWN repositories, the assistant
merges a pull request WITHOUT a fresh per-PR answer once both conditions hold:

1. Every required check and every review bot has finished green.
2. Every review comment thread is resolved: fixed in a commit, or answered on the
   thread with the reason it is not changed.

A pending reviewer, a red check, or one unresolved thread still blocks the merge and
gets surfaced instead. Everything else in this rule stands: deploys and production
remain three-step, and the merge lands in the session's report row.

## Follow-through 2026-08-12: a merge is finished by its smoke, not its click

Operator instruction, same date: "merge it finish the work and monitor post finished
smoked. (that in football called follow through)". The auto-merge authority above
comes with the matching obligation: the session that merges also finishes the merge.

1. After the merge lands, fetch fresh refs and verify ancestry:
   `git merge-base --is-ancestor <merge-commit> origin/<default-branch>`.
2. Run the gate (or the repo's declared check) against the merged default branch,
   not the feature branch, and paste the verdict.
3. Report the three facts together: merge commit, post-merge check verdict, and
   anything that broke, in the same turn that claims the merge is done.

A merge reported without its post-merge check is an unfinished merge and reads as
ASSUMED under calibrated-claims. This is the PR-scale copy of
production-means-merged-and-smoked, which keeps owning the deploy-scale version.
