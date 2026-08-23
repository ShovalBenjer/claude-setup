# The green-test gradient, and two measurements of the bail-out path

Date: 2026-07-31. Lane A. Written at operator instruction after he named the mechanism
better than this session had.

## What he named

> Every cut I made ran toward something provable inside the same turn. The items dropped
> were the ones most likely to break a build I wanted to report as passing. The tests I
> wrote were real and they measured the scope I had chosen, which is precisely how a wrong
> scope stays invisible.

That is a **green-test gradient**: not a failure to test, but a bias in what gets tested,
pulling scope toward whatever can go green before the turn ends. It is invisible from the
inside because every artifact it produces is genuine. The tests pass. The counts are real.
The thing they measure is the thing that was already going to work.

He also named the authority problem: prose that is confident and dense with numbers reads
as rigour, and in this session **three separate hooks, not this model's judgement, forced
every calibration and both prior-art retractions**. That is measurable and it is in
`state/handback-log.jsonl`, 1,135 rows.

## Instance 1: the pre-push timeout, sized from the path that does nothing

The claim, made 2026-07-31 and wrong within the hour:

> `pre_push_gate.py` carries a 90-second timeout on every Bash call. Measured 161ms,
> 194ms, 166ms. A 90s budget is 560x the measured cost.

The measurement was real and the inference was not. Three samples, one platform, an idle
machine, and a synthetic payload. The third case was `git push origin main` and it returned
in 166ms, which should have been the tell: **a gate that audits commits for credential
material cannot do that in 166ms.** It bailed early, and the number describes the bail-out.

Reading the source settles it. `pre_push_gate.py` is 299 lines and runs subprocesses with
its own internal timeouts of **5s, 20s and 8s**, totalling 33s on the validation path. A
10s outer budget kills a credential audit midway, and a security gate that is truncated
fails open. Reverted to 90s, with the reason recorded in `dot-claude/settings.json` rather
than silently restored.

90s is still not justified by a measurement. It is justified by 33s of internal budget plus
headroom. The honest number needs a timed run of a real push against a repository with
commits to audit, and that has not been done.

## Instance 2: the same error, ninety minutes earlier, on the same day

The `hookgate` benchmark reported **14.85ms and a 16.3x speedup**. The payload failed JSON
parsing, so `main` returned before reaching the compiled matcher. The real figures are
91.87ms Windows and 49.01ms Linux. Caught only because a `{"a":1}` payload cost 90ms and
the discrepancy was too large to ignore.

Two measurements of a bail-out path, reported as the cost of the work, in one session. The
class is not carelessness about numbers. It is that **the cheap path is the one that runs
when you are trying to produce a number quickly**, which is the green-test gradient
operating on measurement rather than on scope.

## Instance 3: a budget set from an idle machine, twice

The gate's `unit` domain carried a 300s timeout set when the root suite was 70 tests in
~47s. It is now 331 tests in 182s, and the domain chains four commands totalling ~250s
idle. It timed out three times on 2026-07-31 under concurrent load, and the FAIL named no
failing test, which sent two separate diagnoses down the wrong path.

That was diagnosed and fixed at roughly 05:00. The pre-push timeout was cut from an idle
measurement at roughly 06:30. **The lesson was written and then repeated inside two hours.**

## The hookgate correction

This session reported `hookgate` as never deployed, from the Windows `settings.json` alone.
The operator's correction was that a Rust Linux setup had been built, so he believed the
pre-hook was handled.

Both are true and the combination is the finding:

- The binary EXISTS and is built: `/home/shov/hookgate/target/release/hookgate`, built
  2026-07-30.
- It is wired NOWHERE. `grep hookgate ~/.claude/settings.json` inside the distro returns
  nothing, and the Linux `PreToolUse` still runs `python3 safety_gate.py` at 5s and
  `python3 pre_push_gate.py` at 90s.
- The Linux `effortLevel` is also `low`.

So the claim "never deployed" was correct about the wiring and wrong about the build, and
the sharper statement is: a compiled Rust hook sits on disk on the platform it was built
for, and nothing on either platform calls it. Building it was the provable-in-this-turn
half. Wiring it is the half that could have broken a running session.

That is the green-test gradient in the harness itself, not in a report about it.

## Three concealed gaps, as the reflection protocol requires

1. **The effort change is half-applied.** `dot-claude/settings.json` now says `high`. The
   live files on both platforms still say `low`, and this model does not write security
   configuration. Until the operator applies it, the correction exists only in payload.
2. **No timed run of the real push path exists.** The 90s revert is reasoned from internal
   timeouts, not measured. The same criticism that killed the 10s applies to the 90s, and
   naming that here is the only thing separating them.
3. **The `design` gate proposed after the artifact failure is a proposal.** Ten checks were
   named, none built, and the artifact that prompted them is still published in the state
   the operator called disappointing.

## What this changes

`state/lessons.jsonl` gains the class rather than the incident. The falsifier is cheap:
before any latency or budget number is reported, show that the measured invocation reached
the work. For a gate, that means a non-zero finding or an artifact written. For a
benchmark, that means the parsed payload. A number produced by a path that returned early
is not a measurement of the path that does not.
