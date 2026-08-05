# ADR-0021: Rust for hot paths and boundaries, Python for oracles

Date: 2026-08-03. Status: accepted. Extends ADR-0005 (enforcement over prose) by naming
what the enforcement is written in. Supersedes nothing.

## Context

The operator stated a language preference: Rust over Python. This ADR exists because a
preference that stays in a chat log gets re-argued every session, while a criterion in an
ADR is something a future session can apply without asking.

**Measured state of the estate on 2026-08-03, before any decision:**

- **Rust is already here and already live.** `tools/hookgate/` is 324 lines of Rust
  (`src/main.rs`, `src/rules.rs`) on `fancy-regex` and `serde_json`, built with
  `lto = true`, `codegen-units = 1`, `opt-level = 3`, `strip = true`. The live
  `~/.claude/settings.json` runs `tools/hookgate/target/release/hookgate` on
  **PreToolUse**, which fires on every tool call in every session.
  `docs/specs/2026-07-30-data-architecture-and-orchestration.md:244` records 2.26 ms.
- **Python is 93 files, 23,736 lines, 37 directories**, almost all of it oracles, almost
  all stdlib-only. 415 tests run in 33 seconds.
- **Rust is already linked even where it is not written**: `ruff` and `uv` are on PATH and
  both are Rust, and `numerical-stack.md` prescribes Polars, which is Rust. So the real
  question was never Python against Rust. It is **write Rust or link Rust**.
- **FleetView is already spec'd as Tauri** in `2026-07-24-command-center-superior.md`,
  which is a Rust core with a web frontend and no server process. That decision predates
  this ADR.

## The criterion, which is the whole point of this ADR

**Language follows the failure mode, not preference and not familiarity.**

| Write it in Rust when | Write it in Python when |
|---|---|
| It runs on a per-invocation path where latency compounds (hooks, per-keystroke, per-tool-call) | It runs once per gate, per commit, or per session |
| A defect class in it is one the type system or borrow checker eliminates structurally | Its defects are logic errors that a test catches and a compiler cannot |
| It is a long-lived binary a human is waiting on | It is an oracle whose value is that it is cheap to change |
| It must process the whole estate, including the 17,292 gitignored files | It processes 1,852 tracked files |

**The tiebreaker when both columns argue: does the check still run on a machine with no
toolchain?** `python tools/gate/gate.py run` works anywhere python3 exists. Rust needs a
build, `target/` is gitignored, and an oracle that fails to run is worse than a slow one.
This is why the gate stays Python.

## Options considered

Recorded per charters rule 2, with the conventionality of each.

| # | Option | p_conv | Verdict |
|---|---|---|---|
| 1 | Keep everything Python, treat the preference as taste | 0.60 | Rejected. It ignores a real measured defect class (below) and an already-live Rust component |
| 2 | Rewrite the estate in Rust | 0.25 | Rejected. 23,736 lines, and it taxes the mutation discipline hardest, which is the repo's most distinctive property |
| 3 | Rust for new components, Python frozen | 0.35 | Rejected. Splits the estate by date rather than by failure mode, which is arbitrary in two months |
| 4 | **Rust by failure mode, with a named first candidate** | **0.20, PICKED** | The criterion is checkable, and it names one rewrite justified by a dated defect rather than by preference |

Picked 4 because it is the only option whose rule can be applied by a future session
without re-litigating the preference, and because it produces one concrete piece of work
rather than a policy.

## Decision

1. **New components are assessed against the table above, not against a default.** A
   component that lands in neither column stays Python, because that is what the estate is.
2. **`tools/hookgate` stays Rust and is the reference case.** Anything that expands
   PreToolUse rules goes there rather than into a new Python hook.
3. **FleetView stays Tauri** as already spec'd.
4. **The 13 gate domains, the review panel, the refuters and the mutation operators stay
   Python.** Their value is that a new mutation operator costs an afternoon rather than a
   compile cycle, and that the gate runs with no build step.
5. **First and only named rewrite candidate: `tools/bus/bus.py`.** Justified below.
6. **`docs/prior-art/tools-hookgate.json` and any future Rust component carry the same
   prior-art obligation** as a Python one. The language does not change the rule.

## Why `bus.py` and nothing else

Not advocacy. A dated defect from this repository's own ledger.

`tools/bus/bus.py` is 1,243 lines, is the hash-chained ledger the repo treats as
tamper-evident, and today's audit measured **the highest branch complexity in the
repository at 41** in its worst function. On 2026-08-01 its mutation spec ran 23 of 23
applied, 21 caught, **2 survived, and both survivors were the lock**: `append_row stops
taking the lock`, and `the lock is released before the write instead of after`. The
file's own selftest could not distinguish a locked append from an unlocked one.

**A guard dropped at the wrong point is a borrow-checker error in Rust, not a mutation
that survives.** That is the one place in this estate where the type system would have
prevented a defect that actually happened, on the one artifact everything else trusts.

Scope if it proceeds: the append and verify paths only. Query and reporting stay Python
and shell out, so the rewrite is bounded and reversible.

## Correction, 2026-08-04: two facts this ADR rests on were re-measured and moved

Both were checked the day after this ADR landed, and both weaken it. Recorded here rather
than edited into the argument above, because an ADR that quietly repairs its own evidence
stops being a record of why a decision was made.

**1. The `bus.py` lock defect is closed.** `python tools/audit/mutate.py --spec bus` now
reports **23 of 23 applied, 23 caught, 0 survived**. The two surviving lock mutants that
justified naming `bus.py` as the first rewrite candidate no longer survive. The
borrow-checker argument is still coherent as an argument about *defect classes*, and it no
longer has a live instance behind it. **The rewrite's evidence is now historical, not
current**, and it should not be started on this justification alone.

**2. `tools/hookgate` is not untested, contrary to the Consequences section below.**
`tests/test_hookgate.py` and `tests/test_hooks_exist.py` both exist and both name it. What
is true, and narrower: it has **no `selftest` verb**, and separately **the Rust carries zero
unit tests**, `#[test]` count is 0 across all 319 lines of `src/main.rs` and `src/rules.rs`.
So the reference case is covered from the Python side and unverified from the inside, on a
binary that runs on every PreToolUse.

**What this changes in practice.** The criterion in the Decision section stands, because it
was never derived from either fact. What falls is the *urgency* of the named rewrite. The
work that is now better justified than the rewrite is **unit tests plus a mutation approach
for the 319 lines of Rust that already ship**, since that is the least verified code per
unit of blast radius in the repository.

## Consequences

- **A build step enters the critical path for `bus.py` if the rewrite proceeds**, and that
  is the strongest argument against it. Mitigation required before merge: `bus.py verify`
  keeps a stdlib-only Python fallback that runs when the binary is absent, so the chain
  remains checkable on a machine with no toolchain.
- **Two languages means two mutation harnesses.** `mutate.py` operates on Python source. A
  Rust component needs its own mutation approach (`cargo-mutants` is the obvious candidate
  and is not adopted here, only named). **Until that exists, a Rust rewrite of `bus.py`
  would move it from mutation-covered to mutation-uncovered**, which is a regression in the
  property this repo cares most about, and is a blocking precondition rather than a note.
- `tools/hookgate` currently has **no selftest verb and is named in no test**, per today's
  audit. That is a gap the reference case should not have and it is owed regardless of
  this ADR.

## Falsifier

**The criterion is wrong if it never routes anything.** If, six months from now, every
component built under this ADR is Python, the failure-mode table was a way of saying "keep
doing what we were doing" with extra steps.

**And the `bus.py` claim is refuted if `cargo-mutants` on a Rust port leaves survivors of
the same class.** If a borrow checker does not in fact eliminate the lock-ordering defect,
the one piece of evidence behind this ADR's named rewrite is gone and the rewrite closes.

## Applied per file

`docs/analysis/2026-08-05-implementation-reasoning-per-file.md` applies this criterion to
each source file over 300 lines: why each is a flat script of functions with a selftest,
where the loops are and why they are plain, and the one place a class earns its keep.
