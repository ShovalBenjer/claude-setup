# Decision rules: when to use what

Status: proposed. Written 2026-07-29 for lane B (claude-setup).

Five rules. Each one exists because this repository already contains the
machinery to enforce it and does not yet state the condition under which it
should fire. Nothing below asks for new infrastructure. Every rule names the
file it attaches to.

The governing constraint on this document is the operator's own standing lesson:
excavate before building. So each rule ends with WIRES TO, naming an artifact
that exists today, and where a rule needs something that does not exist, it says
so in place and points at the TODO row that already tracks it.

## How to read a rule

Every rule has four parts, and the fourth is the one that makes it a rule rather
than an opinion.

- TRIGGER. The observable condition that makes the rule apply. If you cannot
  observe it in the moment, the rule is unusable.
- TEST. Something a session can apply in under a minute, without running
  anything. Questions with yes or no answers.
- COUNTER-CASE. The situation where following the rule produces a worse outcome
  than ignoring it. A rule with no counter-case has not been thought about.
- WIRES TO. The file, command, or ledger row that makes the rule checkable.

## The evidence these rules are built on

Measured from `state/gate-runs.jsonl` on 2026-07-29 by parsing the file, not by
reading a summary. 968 rows spanning 2026-07-25T07:43:07 to 2026-07-29T03:29:32.

Composite verdicts across all 968 rows: FAIL 455, PASS 264, PARTIAL 249.

Most of those rows come from the gate's own selftest and mutation scratch repos.
Filtering to the three real projects (`new-recruit` 57, `claude-setup` 32,
`daily-deep-learning` 28) leaves 117 rows, and those rows carry the finding:

| Domain | PASS | FAIL | WAIVED | N/A |
|---|---|---|---|---|
| build | 91 | 0 | 0 | 0 |
| docs | 91 | 0 | 0 | 0 |
| security | 85 | 7 | 2 | 0 |
| review | 71 | 21 | 2 | 0 |
| types | 42 | 4 | 47 | 0 |
| unit | 23 | 14 | 55 | 0 |
| pipeline | 15 | 16 | 62 | 0 |
| codemap | 11 | 3 | 0 | 0 |
| prior_art | 2 | 11 | 0 | 0 |
| a11y_ux | 0 | 11 | 8 | 72 |
| e2e | 0 | 13 | 8 | 72 |
| perf | 0 | 0 | 0 | 90 |

Read the top and the bottom of that table together. On real projects, `build`
passed 91 times out of 91 and `docs` passed 91 out of 91. `e2e` appears in 93 of
those rows and has passed zero times. `a11y_ux` has passed zero times. `perf` has
passed zero times.

Across all 968 rows, `e2e` is the single most frequent blocking domain, 247
times, ahead of `review` 116, `pipeline` 111, `unit` 109, `a11y_ux` 106.

That is the shape of the problem in one table. The domains a command can decide
pass routinely. The domains that require something to drive a running artifact
have never once been satisfied. Ninety-one changes were built and documented.
None of them was ever verified against a running application.

Generation scaled. Verification did not. The rest of this document is about not
making that worse.

One caveat on the table, stated because the rule against overclaiming applies
here too: `e2e` at zero passes does not distinguish "ran and failed" from "no
command was ever configured". `UNCOVERED` is a distinct status in `gate.py` and
it appears 502 times across all 968 rows, though zero times in the 117
real-project rows. The honest claim is the narrow one: on real projects, the
e2e domain has never reported a pass. Why it never did is a separate question
this document does not answer.

---

# Rule 1: deterministic code by default, agent only where the pass condition cannot be written in advance

## TRIGGER

You are about to decide whether a piece of work gets done by code you write once
or by a model invoked each time.

## TEST

Three questions. Answer them before writing anything.

1. Can I write the pass condition down right now, before seeing any output?
2. Given the same input, will the verdict be the same every time?
3. If it says pass, can I name what that pass does not cover?

Three yes answers means deterministic. Write the check.

Any no answer means the work needs a model, and then a second rule binds
immediately: **the model's output must land in a deterministic check.** The
model proposes. Code disposes. A model output that nothing validates is not a
verification step, it is a longer way of asserting.

## Why this is the rule here, not a preference

`tools/review/panel.py` is the worked example, and its own docstring makes the
argument better than a principle would:

> A persona is a named set of checks over the lines this change ADDED, each with
> a pattern, a reason a reader would accept, and a severity. That is narrower
> than a human reviewer and it is honest about being narrower.

The `review` domain needed a security reviewer. The tempting build is an agent
prompted to act as one. What shipped instead is 32 pattern checks across 5
personas, because the checks were nameable in advance. Question 1 answered yes,
so the work became code.

The scale that buys is in the artifacts. `state/reviews/` holds 6 records; the
largest covers 46,789 added lines across 243 files against those 32 checks. No
agent reads 46,789 lines cheaply. The deterministic check does it every run, at
the same cost, with the same verdict.

Question 3 is answered in the artifact itself. Every record carries a
`coverage_boundary` string stating the panel sees added lines only and not
pre-existing code, so a pass cannot be read as "a human would have no
objection".

Where a pattern genuinely cannot see, the panel does use a model, and the model
is fenced. `validate_findings` (`tools/review/panel.py:472-500`) drops any
finding citing a file and line the change did not add, returns the drop count,
and `build_note` writes that count into the artifact. The docstring names why:
"an invented file:line is the normal failure mode of a model backend." That is
rule 1's second half implemented literally.

## COUNTER-CASE

Deterministic checks are blind to the category nobody thought to write, and they
fail silently in exactly that mode.

The proof is in this repo. Thirteen of the hooks in `dot-claude/hooks/` are
45-byte files whose entire content is a Linux path that does not exist on this
machine. Every ordinary deterministic check over them passed. The file exists.
It is readable. It is referenced by config. `tools/audit/pointers.py` was written
to catch this class and its docstring states the trap plainly: "a hook that
cannot run fails open, a skill that is a path just never gets loaded, and a
document that names a dead path reads exactly like a document that names a live
one."

That check only got written after a human noticed the category. Category
discovery is the work a model is actually good at and a pattern is definitionally
bad at, because a pattern encodes a category that someone already named.

So the counter-case is: **for reconnaissance, for "what are we not checking",
for reading an unfamiliar tree and proposing what could be wrong, use an agent.**
Then freeze what it finds into a pattern, and from that point the pattern owns
the category. Agent for discovery, code for enforcement. Inverting that gives
you either a pattern that cannot find anything new, or an agent re-deriving the
same 32 checks at cost, differently each time.

Second counter-case, narrower: when the deterministic check would take longer to
write than the total remaining lifetime of the thing it checks. A one-off
migration run once does not earn a pattern.

## WIRES TO

`tools/gate/gate.py:86-89` (`DOMAINS`), `tools/gate/gate.py:100`
(`ALWAYS_REQUIRED`, every domain except perf), `tools/review/panel.py:472-500`
(`validate_findings`), `tools/audit/pointers.py`.

The gate already encodes the strict half of this rule and states it in its own
header: "a domain counts as covered only when a command exits zero, or when a
named artifact exists for the current commit. Anything else is UNCOVERED, and
UNCOVERED fails."

---

# Rule 2: a contract, not a call, when the caller cannot detect a wrong answer from the output alone

## TRIGGER

You are handing work to something that is not you: a subagent, the review panel,
an external judge, another lane, a scheduled job.

## TEST

Two questions.

1. Will a machine consume this output, or will I read it myself?
2. If the callee did the wrong thing but returned something well-formed, would I
   notice?

Read it yourself and you would notice: just call it. Machine consumes it, or you
would not notice: you need a contract.

A contract here means three specific clauses, all of which already exist
somewhere in this repo and none of which is a schema for its own sake:

- **Identity.** What exactly was this produced against. `state/reviews/<sha>.json`
  is keyed by commit sha, so a review names the commit it reviewed.
- **Freshness.** Is it still valid. `gate.py` computes a 16-hex tree fingerprint
  and refuses a green run recorded against a different tree than the one being
  claimed done. A pass earned ten edits ago cannot be quoted.
- **Boundary.** What a pass does not assert. The panel's `coverage_boundary`
  field. Without this clause a narrow pass gets read as a broad one, which is the
  most common way a green check misleads.

## Why the boundary clause is the load-bearing one

Identity and freshness stop stale evidence. The boundary clause stops something
harder: a correct result being read as a stronger result than it is.

This is a live gap, not a hypothetical. `gate.py run` evaluates its domains
independently and prints one composite `VERDICT`. Per-domain boundaries are
documented. The composite one is not. `TODO.md` RT-3 already tracks exactly this:
print which domains were N/A and why, and what a PASS does not assert. The
strings needed already exist in `quality-contract.json`.

Given the table at the top of this document, that gap has teeth. A composite PASS
on a real project today is consistent with e2e never having run, a11y_ux never
having run, and perf being not-applicable. The parts are honest. The join is not.

## COUNTER-CASE

A contract that nothing writes to, and nothing checks, is worse than no contract,
because it reads from the outside exactly like coverage.

`state/claims.jsonl` holds 3 rows. One of them is `_seed`. Its identifiers have
zero overlap with `tools/selfimprove/proposals.jsonl`, which is rewritten whole
on every scan, so a claim can reference a proposal id that no longer exists. The
ceremony is present. The coverage is not. That is the same failure mode as the
45-byte hooks in rule 1, one level up: a channel that looks wired and is not.

So the counter-case is: **do not add a contract you will not add a check for.**
The disqualifying question is "what command detects a violation of this
contract, and who runs it". No answer means write the call, not the contract.

The contrast is instructive. `state/claims-verify.jsonl` (26 rows) and
`state/refutations.jsonl` (287 rows) join on `C-0NN` and that join works, because
`tools/refute/refute.py` executes the verification command and records the
result. One contract in this repo is load-bearing because something runs it.

## WIRES TO

`state/reviews/<sha>.json` (identity), `gate.py` tree fingerprint (freshness),
`panel.py` `coverage_boundary` (boundary), `TODO.md` RT-3 for the missing
composite boundary.

---

# Rule 3: conformal prediction only for a scored decision over an exchangeable population where you need a guaranteed error rate on what you accept

## TRIGGER

All three of these hold at once. Not two.

1. **The decision is scored.** There is a real-valued score, not a boolean
   predicate. If the thing already returns pass or fail, stop here.
2. **Exchangeability roughly holds.** Your calibration items and the future items
   are drawn from the same pool, and their order carries no information. If the
   population is drifting, the guarantee is void, not approximate.
3. **You need a bounded error rate on the accepted set.** You are going to act on
   accepts without review, so the question "how often is an accept wrong" has to
   have a number attached, and that number has to hold without assuming a model
   family.

Two out of three is not a partial case for conformal. It is a different problem.

## TEST

Three questions, in this order. The first one eliminates almost everything.

1. **Does the thing already return pass or fail?** If yes, stop. You have a
   predicate, not a score, and there is nothing to calibrate.
2. **Do I have a stored history of `{score, verified_outcome}` pairs for this
   decision?** If no, stop and go collect it. A guarantee needs a calibration
   set, and a score nobody has ever checked against an outcome cannot produce
   one.
3. **Would I act on an accept without looking?** If no, the guarantee buys
   nothing, because you are reviewing anyway.

Question 1 eliminates every deterministic gate in this repo. Question 2
eliminates the one remaining candidate today, which is why this rule is
currently blocked rather than actionable.

## Where this applies in this harness: exactly one place

`CLAUDE-OS.md:45-46` states the operating rule: "Confidence gates
(intent-plane): >=0.90 autonomous; 0.70-0.90 work + explicit proof gate; <0.70
ask or spawn reviewer."

That is a scored decision (a confidence), over a population (turns), where the
accept action is "proceed without asking". All three triggers fire. It is the
one place in this system where conformal machinery is the right shape.

And it cannot be applied yet, for a reason that must come first. Nothing on disk
has ever recorded a claimed confidence next to a verified outcome. The reliability
curve for that 0.90 threshold has never been computed and currently cannot be.
`TODO.md` RT-1 tracks precisely this: log `{claimed_confidence, action,
verified_outcome}`.

The ordering is not negotiable. **You cannot conformalize a score you have never
measured.** RT-1 first, then ask whether conformal applies. The literature that
produced RT-1 says self-reported model confidence sits in the 80 to 100 band
regardless of actual accuracy, which if true here would make the 0.90 gate inert
rather than protective. If that is what the data shows, the fix is a better score
or a different mechanism, not a coverage guarantee wrapped around a number that
carries no signal.

The storage seam for RT-1 already exists and needs no schema change:
`eval_results.details_json` in `intent-control-plane` accepts an arbitrary JSON
blob, and `eval_cmds._record(base_dir, eval_type, status, details)` writes any
dict. A `{"claimed_confidence": ..., "action": ..., "verified_outcome": ...}` row
stores today under a new `eval_type`. The blocker is not schema. It is that
`~/.intent` does not exist on this machine.

## Where it does NOT apply, which is most of this repo

Most gates here are deterministic predicates with no score and no distribution.
`expired()` at `gate.py:730` is a date comparison. `secret_scan` is a regex.
`docs_touched` is a set membership test. Wrapping any of these in a coverage
guarantee is cargo cult, and this repo has already written that finding down: see
the "What does not transfer" section of
`docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md`. This
rule is that finding turned into a trigger condition; it is not a new claim.

There is a second, sharper exclusion that matters more in practice. **Conformal
gives you a guarantee about a rate over a population. It never tells you anything
about the item in front of you.** A gate whose job is to stop this specific
credential from being committed is not a rate problem, and a 90 per cent coverage
guarantee on secret detection would be an unambiguous regression against a regex
that either matches or does not.

Note the direction of the fence in `panel.py:456-462`: the credential scan runs
over every line before any blinding, "so filtering can never remove a key from
its own leak check", and a non-empty leak set means send nothing at all. That
ordering is a hard predicate deliberately placed ahead of the probabilistic path.
Do not soften it.

## The composition failure, stated precisely

Per-stage conformal guarantees do not compose into an end-to-end guarantee.

Two separate mechanisms break, and they break for different reasons:

1. **Conjunction.** Twelve domains each guaranteed at 90 per cent do not yield a
   90 per cent joint guarantee. The joint degrades toward the product of the
   per-stage rates. Calibrating each stage to the target you want at the end
   guarantees you miss it.
2. **Exchangeability collapse downstream.** Stage two's input is stage one's
   output, which has been filtered by stage one's acceptance rule. Filtered data
   is not exchangeable with the original population. So the assumption that
   licensed stage one's guarantee is already false at stage two, and it gets
   worse with depth.

The mitigation named in the research is pipeline-aware calibration: derive the
thresholds backward from the final stage rather than setting each stage
independently.

This is not abstract for `gate.py`, which runs its domains and prints one
`VERDICT`. Anyone tempted to attach per-domain statistical guarantees should read
the composite verdict problem as the same defect RT-3 already describes in
deterministic form.

Exchangeability is also fragile here for an environmental reason. The prior-art
survey observed 5 distinct Claude Code CLI versions in a 21-day window, and the
tree changes on every commit. A calibration set drawn from last week's turns may
not be exchangeable with this week's. Any conformal deployment needs a
recalibration cadence and a drift check, or the guarantee silently expires the
way an unrenewed waiver does.

## COUNTER-CASE

The rule as stated says "you need a guaranteed error rate on accepts". The
counter-case is when you think you need that and you do not, because a cheap
sound verifier exists.

If you can afford to verify every accepted item, verify every item. A statistical
guarantee over a subset is strictly weaker than checking all of them, and it
costs a calibration set, an exchangeability assumption, and a recalibration
schedule. Buy the guarantee only when verification is genuinely unaffordable at
full coverage.

That is the direct handoff to rule 4, and it is the more common situation in this
harness.

## WIRES TO

`TODO.md` RT-1 (must land first), `CLAUDE-OS.md:45-46` (the only qualifying
decision), `eval_results.details_json` (storage, no schema change),
`docs/analysis/2026-07-27-research-transfer-uncertainty-and-oracles.md` (the
existing scoping finding this rule formalizes).

---

# Rule 4: cheap proposer plus strict verifier, whenever checking an answer costs less than producing it

## TRIGGER

Both of these hold:

1. Verifying one candidate costs materially less than generating one.
2. The verifier is sound: it does not accept a wrong answer.

## TEST

Two questions, answerable without measuring.

1. Can I check a candidate **without redoing the work that produced it**? If
   checking means re-deriving the answer, the inequality does not hold and there
   is no win available.
2. Can the verifier accept something wrong? If yes, you do not have a verifier,
   you have a filter, and a cheap proposer behind a filter produces plausible
   garbage at volume.

Both yes: propose cheaply, verify strictly, and let the proposer be wrong often.
Being wrong often is fine and is the entire point. The proposer's error rate
costs throughput. The verifier's error rate costs correctness.

Speculative decoding is the exact special case where the verifier is the
expensive model itself, checking a draft model's tokens in one batched forward
pass. `docs/adr/0009-slm-swarm-asymmetric-leaf-executors.md` records it at 2 to
3x with identical output, and calls it, with routing and cascades, one of the
robust asymmetric wins. Identical output is what soundness buys: the technique is
not a quality tradeoff, only a cost one.

## Where the inequality already holds here, and is already exploited

Excavation first. This harness has run this pattern for weeks without naming it.

- **`panel.py` `validate_findings`.** A model proposes findings. Checking one is
  a lookup: is this file and line in the set of added lines. Generation is a
  model call; verification is a dict membership test. Sound, because a finding
  citing a line the change did not add is definitionally invalid. Already wired,
  and the drop count is written into the artifact.
- **`tools/audit/mutate.py`.** Generating a mutant is a string substitution.
  Verifying it is running the target's own selftest and requiring red. The
  docstring states the standard: "A green selftest is unfalsified, not verified."
  Exit 0 only when every mutation was applied and caught; exit 2 when the
  baseline copy is not green, because then a "caught" cannot be attributed to the
  mutation. Nine specs live in `tools/audit/mutations/`.
- **`prior_art` and `codemap`.** Proposing that a directory owes a record is
  cheap. Verifying is checking a record exists and its `recheck_after` has not
  passed.

## Where the inequality holds and is NOT yet exploited

These are the recommendations, and both are wiring jobs, not new systems.

**First, and highest value: the corpus backfill, using `validate_findings`
unchanged in shape.**

The corpus survey found that of 537 unique item timestamps in
`distilled_raw.json`, 133 do not match any timestamp in the current
`corpus_inputs.json`, and of 168 unique rule `evidence_ts` values, only 59 exist
in the corpus. So roughly 242 extracted items and rules cite prompts that are not
there. (These counts are from the corpus survey, not re-measured by me.)

That is precisely the invented-citation failure `validate_findings` was built to
catch, in a different file. An extraction step that proposes "this prompt implies
this ticket" is a cheap proposer. Verifying it is a dict lookup against the
corpus keyed on `(ts, sha256(text))`, which the survey established is a workable
primary key given the single known `ts` collision. Every one of those 242 broken
references would have been caught at write time, and the drop count recorded, by
the check this repo already runs on review findings.

The rule that follows: **any extraction that produces a citation must validate
the citation against the source before the row is written, and must record how
many it dropped.** A silent drop count is the ambiguity `panel.py`'s mutation
spec exists to prevent; its "blinding becomes silent" mutation targets exactly
the case where the caller can no longer distinguish a filter that removed nothing
from one that stopped working.

**Second: the e2e domain, which blocks 247 runs and has never passed.**

Producing a UI flow is expensive. Checking an assertion against a rendered page
is cheap. The inequality holds cleanly, and the domain with the worst record in
the entire table is the one where it holds best. This is the largest unexploited
gap the numbers point at. Whether the fix is a recorded flow, a cheaper driver,
or a narrower contract is out of scope here; the point is that the asymmetry is
available and unused.

## COUNTER-CASE

Three, and the third is the one that actually bites in this repo.

1. **The verifier is not sound.** Then the whole thing inverts and a cheap
   proposer floods you with plausible passes. If `validate_findings` checked only
   that the file exists, and not that the line is in the added set, a model could
   cite any line in a large file and pass. The panel's mutation spec plants that
   exact class of break.
2. **Generation is already cheap.** Then the split is pure overhead. Do not add a
   proposer stage to something a regex already does in one pass.
3. **Proposer and verifier share a failure mode.** This voids the inequality
   without looking like it. If both are the same model with the same blind spot,
   the verifier confirms rather than checks. This repo hit it and fixed it on
   2026-07-27: `panel.py` blinds the judge from `SKILL.md` files, because, in the
   mutation spec's words, "an external judge that can read the SKILL.md it is
   grading grades the description rather than the output, which is the same
   failure as marking your own homework." Before trusting any proposer/verifier
   pair, ask what they have in common. Independence is the property doing the
   work, not cheapness.

## WIRES TO

`tools/review/panel.py:472-500` (the existing implementation to copy),
`tools/audit/mutate.py`, `tools/audit/mutations/panel.py` (the soundness and
independence mutations), and the corpus backfill, which has no file yet.

---

# Rule 5: a self-improvement is admissible only if a measured defect triggered it, prior art did not already solve it, and it ships with its own falsifier

## TRIGGER

Anything that would change how this system works, including a new check, a new
tool, a new hook, a new schema, or a rewrite of an existing one.

## TEST

Four questions, in order. A no at any step stops the work.

1. **What row triggered this?** Name a line in `state/gate-runs.jsonl`,
   `state/refutations.jsonl`, `state/lessons.jsonl`, or the output of
   `tools/audit/pointers.py`. Not an idea, not a paper, not a feeling that
   something is untidy. A row.
2. **Does it already exist?** Run the prior-art gate. If a survey, a curated
   list, a recurring workshop, or three or more benchmarks sharing a name for the
   problem turns up, the novelty claim is refuted and the job becomes adoption,
   not construction.
3. **What turns it red?** A new check ships with a mutation in
   `tools/audit/mutations/` that breaks the behaviour it claims to guarantee and
   makes its selftest fail. No falsifier, no merge. A green selftest is
   unfalsified, not verified.
4. **What would make me remove this later?** Name the condition. A change with no
   removal condition is permanent by default, and this repo has already measured
   what permanent-by-default costs: `tools/dolt`, 787 lines, zero callers.

Step 2 is not advisory. `prior_art` is a real gate domain, dispatched at
`tools/gate/gate.py:716-717` through `codemap(project, spec, "prior-art")` and
registered in `BUILTINS` at `gate.py:719-725`. Across all 968 runs it has passed
23 times and failed 80. On real projects it has passed twice and failed eleven
times. It blocks.

## Why this is the anti-novelty clamp

The failure mode the operator is guarding against is building something new
because it is new. Step 1 removes the motive: novelty is not a reason, a measured
defect is. Step 2 removes the opportunity: if the field solved it, adopt.

The evidence that step 2 works is that it mostly says do not build. The
2026-07-29 prior-art audit compared ten components against roughly seventy named
alternatives and returned split verdicts on eight of ten, meaning part of our
code should go. A gate that mostly returns "buy" is a gate that is functioning.
The `skills_sync.py` result is the clearest instance: 692 lines, and plain
`diff -rq` was run, reproduced all three of its buckets, and caught a difference
ours misses because ours only hashes `SKILL.md`.

Records carry a `recheck_after` date and expire like waivers, which matters
because a prior-art answer rots. What was absent in May can exist in July.

## The clause that keeps this from becoming paralysis

Step 2 refuting a novelty claim does not automatically forbid building. Prior art
can exist and still not fit, and the escape hatch is: **name the excluding
constraint as a testable predicate, not a preference.**

The repo's own worked example is `tools/dolt`, where the audit's verdict was
"nothing needed" partly because its remote is public-only, which blocks both
stated purposes. Public-only is a checkable property. "I like ours better" is
not. Without this clause the gate becomes an argument for never building
anything, which is its own failure mode.

## The inverse clamp, which is the part that is easy to miss

The absence of a defect row is not evidence of health. It is equally consistent
with nothing measuring that area.

This is why step 1 cannot be the whole rule. `tools/audit/pointers.py` exists
because a hook that cannot run fails open and produces no failing row at all.
Thirteen dangling hooks generated exactly zero defect rows while being
completely broken.

So rule 5 carries a standing obligation that is not triggered by a row: **on a
fixed cadence, ask what is unmeasured rather than what failed.** That is the
excavate-before-building discipline as a loop instead of a one-off. Three
concrete unmeasured areas are already named and open: RT-1 calibration, RT-5
metamorphic testing (`grep -ril metamorphic tools/` returns zero
implementations), and the absent `UserPromptSubmit` entrance guard.

## The health metric for this rule is the rejection rate

A self-improvement loop whose proposals are never rejected is not a loop. It is a
conveyor with a signature block.

`TODO.md` RT-2 already states this in its sharpest form: "A ratio that has never
seen a rejection IS the finding." Three ADRs rest on human approval, and nothing
in `state/` records an approve-or-reject, so rubber-stamping would currently be
undetectable.

This is the one place where rule 5 measures the human rather than the machine,
and per the 2026-07-29 analysis it is the system's largest blind spot: every
existing measurement is about the machine, and the number that would show whether
the governance is real has never been collected.

## COUNTER-CASE

Two.

**Emergency.** If a credential is exposed or a gate is passing when it must fail,
fix it now and write the prior-art record afterward. A process that delays a
security fix for a literature search is wrong. The obligation is deferred, not
waived, and it needs an expiry like any other waiver, or it becomes the permanent
exception.

**Cost asymmetry at small scale.** For a change smaller than the record that
documents it, the four-step test costs more than it saves. The threshold this
repo already uses is durability: does this touch a check, a contract, or an
oracle. Yes means the full test regardless of diff size, because those are the
things that fail open. No, and it is a few lines, means ship it.

The failure mode to avoid is applying the full test to trivia while a 787-line
zero-caller tool sits in the tree unexamined. The gate is for load-bearing
changes.

## WIRES TO

`tools/gate/gate.py:716-717` and `:719-725` (the `prior_art` domain, already
blocking), `~/.claude/skills/prior-art-gate/SKILL.md` (the four not-a-gap
signals and the REFUTED / SURVIVES protocol), `tools/audit/mutate.py` plus
`tools/audit/mutations/` (the falsifier requirement), `tools/audit/pointers.py`
(the unmeasured sweep), `TODO.md` RT-2 (the rejection rate, not yet collected).

---

# The one-page version

| Situation | Rule | Decide by |
|---|---|---|
| Deciding who does a piece of work | 1 | Can I write the pass condition before seeing output? Yes: code. No: agent, and validate its output with code. |
| Handing work to something that is not me | 2 | Would I notice a well-formed wrong answer? No: contract with identity, freshness, boundary. Yes: just call it. |
| Tempted to attach a statistical guarantee | 3 | Is it scored, exchangeable, and does it need a bounded accept-error rate? All three or do not. |
| Something is expensive to produce | 4 | Is checking cheaper than producing, and is the checker sound? Both: cheap proposer, strict verifier. |
| Proposing to change the system | 5 | Which row triggered it, does it already exist, what turns it red, what would retire it. |

Rules 3 and 4 interact and the order matters. Ask rule 4 first. If a sound cheap
verifier exists, verify everything and skip the statistical guarantee entirely.
Reach for rule 3 only when full-coverage verification is genuinely unaffordable.

---

# What this document does not cover

Stated per the calibrated-claims rule, leading with the gaps.

- **No rule here has been executed.** This is a written standard, not a wired
  check. Nothing in `gate.py` currently enforces rules 1 through 4. Rule 5 is the
  only one with live enforcement, through the `prior_art` domain, and that
  enforcement covers step 2 only, not steps 1, 3, or 4.
- **Rule 3 is not actionable yet** and says so: RT-1 must produce data before the
  conformal question can even be asked.
- **The corpus figures in rule 4** (133 of 537, 109 of 168, 587 prompts, 537
  rules) are carried from the corpus survey and were not re-measured by me. The
  gate-run figures, the panel figures, the line counts, and every file and line
  reference were measured or read directly on 2026-07-29.
- **The e2e zero-pass finding is narrow.** It establishes that the domain has
  never reported a pass on a real project. It does not establish why.
- **No prior-art search was run for this document itself.** By rule 5 step 2
  that is a gap, and the honest label is that the five rules here are a synthesis
  of findings already in this repo plus standard practice, not a claim of
  novelty. Nothing in this document should be described as new. If any part of it
  is later written up as a contribution, it owes a prior-art record first.
