# Where our system stands against everything we researched

Point-in-time comparison, 2026-07-29. Inputs: the 43-source compile-once research,
the 10-component prior-art audit run today (roughly 70 named alternatives), the
epistemic-governance essay the operator supplied, and the learning-platform
handoffs from 2026-07-27.

Written plainly on purpose. Terms are defined the first time they appear.

---

## Words I have been using without explaining

- **Gate**: one program, `tools/gate/gate.py`, that refuses to say "done" unless
  every check passes. It is the thing that keeps blocking my messages.
- **Domain**: one of the twelve things the gate checks. `unit` is tests, `review`
  is code review, `prior_art` is the build-vs-buy audit, and so on.
- **Oracle**: any check that decides right from wrong. A test, a linter, the
  review panel. The word matters because editing an oracle can make it stop
  catching things, so this repo requires your approval before I touch one.
- **Fingerprint**: a hash of the whole working tree. It exists so a "pass" earned
  ten edits ago cannot be quoted as if it still applied.
- **Mutation testing**: deliberately breaking the code to confirm the tests go
  red. A test that never fails is decoration.
- **Prior-art record**: a written answer to "what else could do this job, and why
  are we still writing our own."
- **Lane**: which of four jobs a session is doing. B is this harness.
- **Conformal prediction**: a way to make a model abstain with a guaranteed error
  rate, instead of trusting a confidence number it made up.
- **Metamorphic testing**: checking correctness with no answer key, by changing
  the input in a way that must not change the answer, and seeing whether it did.

---

## The headline

Three independent sources arrived at the same warning, and it is aimed at this
system's stated purpose.

`CLAUDE-OS.md` section 1 defines the mission as everything becoming "gated,
evidenced action across his ventures, with **Shoval reduced to an approval
surface**."

- The automation-bias literature says approval under volume decays into
  rubber-stamping, while the record still shows a human decided.
- The epistemic-governance essay says outsourcing reflection to a reliable system
  erodes the human's own capacity to verify it, and calls this the
  performance-reasoning trade-off.
- Our own state files cannot tell us whether this is already happening, because
  nothing records an approve-or-reject decision.

So the system's goal, its measured risk, and its blind spot are the same thing.
That is the most important finding in this document.

---

## Where we are genuinely ahead

These are not flattering guesses. Each is something the research says is rare and
that we demonstrably have.

**Evidence bound to a tree hash.** The prior-art audit searched hard for this and
found one close match, `MPIsaac-Per/claude-code-loop-patterns` pattern 04, which
validates evidence by a 30-minute time window instead. A time window lets a proof
survive edits it never covered. Our fingerprint does not. I fixed a real defect in
it today, where the gate hashed its own output ledger and could therefore never
pass.

**Falsifiability as a separate job.** We run mutation testing over nine specs and
require every planted bug to turn a selftest red. Most projects never check that
their checks can fail.

**Artifacts that state their own limits.** `panel.py` writes its coverage boundary
into its own output, so "the review passed" cannot be misread as "a human would
have no objection." Almost no published evaluator does this.

**Expiry on frozen records.** All prior-art records carry a `recheck_after` date
and expire like a waiver. The research's schema-drift finding is exactly that a
frozen, once-approved artifact keeps running while quietly going wrong.

---

## Where the field is ahead of us, with names

Today's audit compared ten of our components against roughly seventy real
alternatives. Eight of ten verdicts were **split**, meaning part of our code
should go.

| Ours | What beats it | Evidence |
| --- | --- | --- |
| `skills_sync.py`, 692 lines | plain `diff -rq` | It was run. It reproduced all three of our buckets and caught a difference ours misses, because we only hash `SKILL.md`. |
| `tools/dolt`, 787 lines | nothing needed | Zero callers, and its remote is public-only, which blocks both stated purposes. |
| `tools/bus`, 1011 lines | Claude Code's native agent-teams Mailbox | First-party, push-delivered, zero install. Blocked today by one documented limit: one team per session. |
| `completion_gate.py` | `nizos/probity`, MIT | A maintained tool for the same job. |
| ~705 lines of `dot-claude/bin` | gitleaks, Presidio, simonw/llm, Datasette, the ElevenLabs SDK | Each replaces a piece we hand-wrote. |
| record validation in `tools/map` | check-jsonschema | And it exposed a real hole: `recheck_after` is only date-checked for directories that currently owe a record. |

Above all of these sits something outside the audit's scope, which the operator
found himself: **`github.com/Sdraugel/albert`**, an autonomous multi-agent harness
for Claude Code with a live console. That is prior art for the entire repository,
not for any component in it, and our gate never asked about it because the audit
is scoped per directory.

---

## What we are missing entirely

Each of these is named by the research and absent here, verified by running the
check rather than by looking.

**Calibration.** `CLAUDE-OS.md:45` gates autonomy at a confidence of 0.90.
Nothing on disk has ever recorded a claimed confidence next to a verified
outcome, so that number has never been checked. The literature says self-reported
model confidence sits between 80 and 100 regardless of accuracy, which would make
that gate decorative. Filed as RT-1.

**Rejection rate.** Three architecture decisions rest on you approving something.
No ledger records an approve-or-reject, so rubber-stamping would be invisible.
Filed as RT-2.

**Metamorphic testing.** `grep -ril metamorphic tools/` returns zero
implementations. We have mutation testing, which asks "can this check fail," and
nothing that asks "did the answer change when it must not have." Filed as RT-5.

**The entrance guard.** Every hook we run fires at exit. `UserPromptSubmit` is
wired nowhere, yet a shipped skill's description claims it triggers from there.
From the learning handoff, still unbuilt.

**A mechanism-claim gate.** We gate claims of absence and claims of completion.
Nothing gates "here is a method." Also from the learning handoff, still unbuilt.

**Shared budget visibility.** One fan-out consumed an entire session's search
budget and every later agent ran degraded, silently. Still no guard.

---

## Where the handoffs already agree with us

Worth recording, because it means two independent lines of work converged.

The learning handoff said **a critic must flag, not fix**, citing a pipeline that
silently replaced a teacher's answer with a critic's rewrite whenever the rewrite
was longer than twenty characters. Our `panel.py` returns findings and never
substitutes text. That is the correct shape and we already have it.

It also said **one independent critique beats multi-agent debate** at lower cost.
Our two-model agreement gate is that shape, not a debate.

---

## The uncomfortable synthesis

Our strongest asset is that this system can refuse. The gate is real, it blocks,
and I have spent this entire session unable to talk my way past it. Most harnesses
described in the research cannot do that.

Our deepest weakness is that we cannot tell whether the human on the other end of
those refusals is still reading them. Every measurement we have is about the
machine. The one number that would tell us whether the governance is real, the
rejection rate, has never been collected.

The essay's phrase for this is the performance-reasoning trade-off: the better the
system gets, the less the human exercises the judgment the system depends on. This
harness is unusually good at producing evidence, which means it is unusually
capable of producing that trade-off.

---

## Residual risk in this document

The comparison table is derived from records written by ten subagents earlier
today. I read their summaries and spot-checked the two strongest claims, `diff
-rq` and the zero-caller finding in `tools/dolt`. I did not independently rerun
every alternative's evaluation, and none of the ten records has been reviewed by
anyone but its author, which is the same self-annotation weakness we flagged in
our own skill fixtures.

The epistemic essay's numeric claims are its own and remain unverified.
