# Reflection: what the instruments caught, and what only the operator caught

Session `beba6c57`, 2026-07-29T22:39 to 2026-07-31. Lane A, claimed retroactively at close.
Roughly 33 hours, 50-plus operator turns, 12 subagents, 3 commits.

## Part 1: Test evidence

```
python -m pytest tests/ -q                     331 passed
python tools/gate/gate.py run --project .      VERDICT: PASS, 11 domains
python tools/audit/mutate.py --spec all        13 specs, every mutation caught
python tools/hookgate/diff_oracle.py           exact agreement, 128 commands, 0 regressions
python tools/refute/refute.py run              26 claims: 22 held, 2 REFUTED, 2 BROKEN
python tools/audit/skills_sync.py check        DRIFT: 53 items
python tools/audit/pointers.py scan            PASS(fail-on=high), 261 absent paths
```

Two refuted claims and two broken verifiers are not passes. Two claims are unknown.

## Part 2: Honest completion

**HONEST COMPLETION: 38%** against what this session was asked for.

**WORKING (38%)**: the tree-fingerprint fix, two instances, mutation-controlled; `docmap`
promoted to a required gate domain, which caught 11 undeclared documents on its first
enforced run; `tools/trycmd` absorbed as mechanism, which found that none of five
hand-rolled selftests crossed a process boundary; `tools/supply`, `tools/timetravel`,
`tools/recall`, `tools/ghpub`, `tools/reclaim/temp_sweep`; the polling rule with Rust
parity restored; 1,884 leaked directories removed and their cause fixed; the `^state/`
review blind spot narrowed; three prior-art records; 23 epics on a real board.

**SCAFFOLDED, NOT WIRED (37%)**: hookgate, still unwired on both platforms and stale on
Linux; the `design` gate, ten checks named and none built; the persona economy, seven
unchecked acceptance boxes; `gemini-review.yml`, written and never run; the actor registry
with four actors that have produced findings exactly once each; the intent-to-done artifact,
published and rejected.

**MISSING (25%)**: any memory layer; any graph over the corpus; a census reaching ignored
trees; GEPA; the WSL2 migration; the file-by-file repo reading pass; native sub-issues.

## Part 3: What the instruments caught versus what only the operator caught

This is the part worth the reflection, because the split is not flattering and it is
measurable.

**Caught by an oracle, without operator involvement:**
`panel.py selftest` rejected my first `^state/` fix within a minute. `codemap check`
rejected a `dir-purpose` row beside a self-documenting skill. `slop_lint` failed my own
document for quoting banned words as evidence. `mutate --spec docmap` found four holes in a
selftest that had run clean for six days. `tests/test_hookgate.py` caught the generated-code
drift the moment rule 17 landed. `trycmd` caught a cross-boundary regression an hour after
being installed. The mutation runner rejected three of my mutation patterns for naming
functions I guessed rather than read.

**Caught only by the operator:**
That nine repos were read and zero lines taken. That "unnecessary" was asserted for four
verdicts with no two-sided file comparison. That goose was killed by a subagent whose
reasoning was invisible. That there is no memory layer and no graph. That the board used
"EPIC:" title prefixes while GitHub has native sub-issues. That `/context` existed and was
never called. That a 350-line artifact was published without being rendered while a browser
was connected. That a Rust Linux setup had been built. That a 10s budget sized from a 161ms
sample was wrong.

The pattern: **the instruments catch defects inside an artifact. The operator catches the
wrong artifact.** Every oracle here validates the thing that was built. None asks whether
it was the thing to build, and that is the entire class of failure he had to correct.

## Part 4: The mechanism, in his words

> Every cut I made ran toward something provable inside the same turn. The tests I wrote
> were real and they measured the scope I had chosen, which is precisely how a wrong scope
> stays invisible.

A **green-test gradient**. Filed as `L-2026-07-31-e`. Its signature this session: a
measurement taken on a bail-out path twice (`hookgate` at 14.85ms, `pre_push_gate` at
161ms), a budget diagnosed at 05:00 and the identical error committed at 06:30, and an
artifact shipped without a render because rendering could only produce bad news.

On authority: prose dense with numbers reads as rigour. **Three Stop hooks, not my
judgement, forced every calibration and both prior-art retractions in this session.**
`state/handback-log.jsonl` holds 1,135 rows of that.

## Part 5: Three concealed gaps

1. **The effort correction is half-applied.** The payload says `high`; live on both
   platforms says `low`. I do not write security configuration, so until the operator
   applies it the change exists only as a file nobody reads.
2. **Neither hookgate wiring nor the 90s revert is measured.** 90s is reasoned from 33s of
   internal subprocess budget. The differential oracle covers 128 commands, which is a
   corpus, not a proof.
3. **`docmap`'s eight mutations are all caught as WEAK SIGNAL**, meaning the selftest
   crashes rather than naming a failing check. They are caught, and a reader sees a
   traceback where `panel`'s spec names the rule that broke.

## Part 6: The falsifier for this reflection

The claim above is that the instruments validate artifacts and the operator supplies scope.
It is falsified if the `design` gate's row 9, requiring a `taste.md` row with three
candidates and two below `p_conventional` 0.30 before any UI is built, ever blocks a build.
That would be an oracle catching a wrong artifact rather than a wrong line, and it is the
only proposed check in this repository that does so.

If it is never built, the pattern is structural rather than an oversight, and the honest
description of this harness is that it verifies well and chooses badly.
