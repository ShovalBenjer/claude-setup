# What the compile-once research says about THIS harness

Point-in-time analysis, 2026-07-27. Source report: `~/Documents/
TextToWorkflow_CompileOnce_Research_20260727/report.md`, 43 sources, 38 URL
verified, 0 suspicious.

The research was commissioned to ground six challenge questions against an
external architecture talk. Five of its findings land on this repository harder
than they landed on the talk, because this repository makes the same claims with
less measurement. Every "today" line below was verified by running the command
beside it, not by reading a doc.

---

## T1. The confidence gate in the spine is uncalibrated, and probably inert

**Research.** Verbalized LLM confidence is pervasively overconfident, with values
concentrated in the 80 to 100 per cent band regardless of actual accuracy, and
2026 work finds this survives instruction tuning and alignment. Conformal
abstention is the alternative that carries a distribution-free error guarantee on
the accepted set.

**Today.** `CLAUDE-OS.md:45` states the operating rule: "Confidence gates
(intent-plane): >=0.90 autonomous; 0.70-0.90 work + explicit proof gate; <0.70
ask or spawn reviewer." It is restated at `CLAUDE-OS.md:268` as an axis of
dynamism. Nothing in the tree records a predicted confidence next to a verified
outcome, so the reliability curve for those thresholds has never been computed
and cannot be.

**Why it matters here.** If the number being thresholded is a model's own
estimate, and that estimate lives in the 80 to 100 band almost always, then
">=0.90 autonomous" is not a gate. It is a description of the default path
wearing the costume of a gate. This is the exact defect class the repo already
hunts: `tools/audit/pointers.py` exists because a hook that cannot run fails open
and reports nothing, and this is the same failure one level up in the stack.

**Smallest honest first step.** Log the pair. Every time a session acts under
that rule, append `{claimed_confidence, action_taken, verified_outcome}` to a
ledger. After enough rows the reliability curve is computable and the thresholds
become either evidence or a discarded hypothesis. Do not tune the numbers before
measuring them.

## T2. The human gates are unmeasured, so nobody can tell if they still work

**Research.** Approval under volume decays into rubber-stamping. Reviewers anchor
on early recommendations, apply lower scrutiny as the queue grows, and eventually
treat the system output as the default, while the paperwork still records a human
choice. The standard diagnostic is the rejection rate, plus independent sampling
of approvals.

**Today.** The approval gates are load-bearing across three ADRs: 0005
enforcement over prose with approval-gated self-modification, 0012 autonomy ships
only via the PR gate, 0014 social publish behind a phone-approval gate.
`state/gate-runs.jsonl` holds 753 recorded runs. `state/refutations.jsonl`
records machine verdicts of HELD or REFUTED. No ledger in `state/` records a
human approve-or-reject decision, so the rejection rate on the human gates is not
computable today.

**Why it matters here.** The whole autonomy design rests on "it proposes, Shoval
disposes". If the disposal is approval at a rate near 100 per cent, the design is
running open loop and reads as governed. That is worse than no gate, because the
record shows a decision that did not happen.

**Smallest honest first step.** One append-only decision ledger, and one number
on the daily digest: approvals, rejections, ratio, over the trailing period. A
ratio that has never seen a rejection is the finding.

## T3. Per-check guarantees do not compose into an end-to-end guarantee

**Research.** In multi-stage pipelines, per-stage conformal guarantees do not
compose. Standard methods assume exchangeability within a stage and cannot
account for prediction sets propagating downstream, so stacked stages land below
target joint coverage. Pipeline-aware methods derive thresholds backward from the
final stage.

**Today.** `tools/gate/gate.py run` evaluates 12 domains independently and prints
a single `VERDICT`. The repo is unusually honest about the parts: `.github/
workflows/ship-gate.yml` has a header enumerating what each job does and does not
cover, and `docs/QUALITY-CONTRACT.md` records a dated known-gaps list. What is
missing is at the join: a green verdict is a conjunction of narrow per-domain
claims, and reads to a human as "this change is safe".

**Why it matters here.** The gate's own coverage boundary is documented per
domain and nowhere at the composite. This is the cheapest possible fix and the
easiest to skip.

**Smallest honest first step.** Print the joint claim beneath the verdict, in the
gate's own voice: which domains were N/A and why, what a PASS does not assert.
The strings already exist in the contract.

## T4. Self-annotated fixtures are the BIRD defect, at smaller scale

**Research.** Annotation error rates measured at 52.8 per cent on BIRD Mini-Dev
and 62.8 per cent on Spider 2.0-Snow. Rank correlation between uncorrected and
corrected evaluation fell from Spearman 0.85 to 0.32. The leaderboard ordering
tracked the annotation errors more strongly than it tracked correctness.

**Today.** `python tools/skilleval/run.py scan` reports PASS on 5 graded skills
with 42 uncovered. The fixtures for those 5 were written by the same author as
the skill descriptions they grade, and no independent pass has audited them.
`run.py`'s own docstring already concedes it measures a weaker mechanical
property than model routing, which is the right kind of honesty about the metric
and says nothing about the labels.

**Why it matters here.** A grader is bounded above by its labels. Expanding from
5 fixtures to 47 without auditing the labels scales the defect rather than the
coverage.

**Smallest honest first step.** Record fixture provenance (who wrote it, when,
against which description version) and have one independent pass over the
existing 5 before writing the next 42.

## T5. Mutation testing is here, metamorphic testing is entirely absent

**Research.** Metamorphic testing reveals faults where there is no oracle, by
asserting relations between inputs and outputs. For text-to-SQL, a two-stage
metamorphic approach detects hallucination with recall above 89 per cent and
precision of 54 to 72 per cent using no reference query at all.

**Today.** `grep -ril metamorphic tools/ docs/` returns exactly one hit, in
`docs/analysis/2026-07-25-claude-mastery-research-prompt.md`, which is a research
prompt rather than an implementation. The repo has the sibling technique and uses
it well: `tools/audit/mutate.py` runs 9 specs and requires every mutation to turn
its target's selftest red.

**Why it matters here.** The two answer different questions. Mutation asks "can
this check fail at all". Metamorphic asks "is the output still consistent when I
transform the input in a way that must not change the answer". The repo has
several checks with no oracle where the second question is answerable today:
renaming one directory must change exactly one row of the codemap; reordering
diff hunks must not change the panel's findings; replaying an identical bus
message must be idempotent.

**Smallest honest first step.** One metamorphic relation on `codemap.py`, since
its transformation is trivially constructible and its expected invariance is
exact.

---

## What this repo already gets right, confirmed by the research

Stated because a transfer document that only finds faults is not calibrated.

- **Expiry on frozen artifacts.** All 17 records in `docs/prior-art/` carry
  `recheck_after` and expire like a waiver. The research's schema-drift finding
  is precisely that a frozen, once-approved artifact keeps running deterministically
  while quietly becoming wrong, and the standard fix is an expiry or a drift
  trigger. This repo already built that for one artifact class.
- **Falsifiability as a first-class job.** The separation of "does the code work"
  from "would we find out if it did not" into two CI jobs matches the research's
  central distinction between capability and detection.
- **Naming the coverage boundary.** `panel.py` writes its own limits into its
  artifact, so "the panel passed" cannot be read as "a human would have no
  objection". Most published evaluators do not do this.

## What does not transfer

The conformal machinery is for scored decisions over an exchangeable population.
Most gates here are deterministic predicates with no distribution, and wrapping a
predicate in a coverage guarantee would be cargo cult. T1 applies specifically to
the confidence-gated routing rule, not to the ship gate.

The text-to-SQL accuracy numbers say nothing about this repository. They are
included in the source report for the meeting they were commissioned for.

## Rows this produces

Filed to `TODO.md` under a new heading rather than left in prose here, per the
docs-control-plane rule that analysis is point-in-time and TODO is the single
ticket list.
