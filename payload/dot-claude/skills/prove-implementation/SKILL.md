---
name: prove-implementation
description: Compare implementation and architecture alternatives, detect unjustified default loops or libraries, and require executable evidence before calling a coding choice correct, best, optimized, complete, or production-ready. Use for non-trivial code changes, performance-sensitive loops, database or network paths, concurrency, algorithms, architecture choices, refactors, bug fixes with uncertain causes, and reviews where visible tests may be insufficient.
---

# Prove Implementation

Treat model output as a candidate, not evidence. A familiar `for` loop is not
wrong by default, and a fashionable technique is not better by default. Make the
choice falsifiable.

## Workflow

1. State the behavioral contract and constraints.
   - Name inputs, outputs, invariants, error behavior, scale, latency, memory,
     deployment environment, and compatibility constraints.
   - Turn each acceptance criterion into an observable oracle.
2. Inspect the actual repository before proposing a design.
   - Find existing patterns, dependencies, tests, profiling data, and caller
     contracts.
   - Verify current external APIs against primary documentation when they may
     have changed.
3. Produce viable alternatives before coding.
   - Use at least two candidates, or three for high-risk work.
   - Always include the simplest correct option.
   - For loops or bulk work, explicitly consider batching/vectorization,
     database pushdown, streaming, bounded concurrency, indexing/caching, and
     a plain loop. Reject inapplicable options with a concrete reason.
4. Select with evidence, not novelty.
   - Compare correctness risk, asymptotic cost, expected constants, memory,
     operability, failure isolation, maintainability, dependency cost, and
     reversibility.
   - Never claim globally optimal or "best." Say "best among the tested
     candidates under these constraints."
5. Implement a vertical slice.
   - Preserve or create a failing oracle before the fix when practical.
   - Do not weaken tests, read hidden/reference solutions, or change the oracle
     to make the candidate pass.
6. Attack the result.
   - Run example and boundary tests.
   - Add property, metamorphic, differential, fuzz, mutation, concurrency, or
     benchmark checks when the risk calls for them.
   - After executable checks, invoke `/codex-call` as a fresh, read-only
     reviewer for high-risk work and before any best/optimized/production-ready
     claim. A reviewer failure or disagreement blocks the strong claim; it does
     not erase passing tests.
7. Record proof and uncertainty.
   - Set `$skillRoot = "$HOME\.claude\skills\prove-implementation"` in
     PowerShell.
   - Create an evidence record with
     `python "$skillRoot\scripts\implementation_proof.py" new --goal "observable goal" --risk medium --output .claude\proofs\current.json`.
   - Run each declared check through
     `python "$skillRoot\scripts\implementation_proof.py" run-check .claude\proofs\current.json --check-id C1 --cwd . -- python -m pytest -q`.
   - Validate it with
     `python "$skillRoot\scripts\implementation_proof.py" validate .claude\proofs\current.json`.
   - Report failed, skipped, or unavailable checks before passing checks.

## Loop-specific gate

Run `python "$skillRoot\scripts\loop_audit.py" <changed files>` when changed code
contains iteration.
Treat its findings as review prompts, not automatic defects.

For every material loop, answer:

- What bounds the iteration count?
- Is I/O, a database query, model call, or sleep inside the loop?
- Is the loop accidentally nested or repeatedly allocating?
- Would batching, pushdown, streaming, indexing, or bounded parallelism improve
  the measured bottleneck?
- Does ordering, idempotency, rate limiting, or backpressure make a plain loop
  the safer choice?
- Which benchmark or scale model supports the decision?

## Evidence rules

- Passing visible tests proves only those tests.
- A benchmark without representative data and warm/cold conditions does not
  prove production performance.
- Coverage does not prove assertion quality. Use mutation testing selectively.
- The authoring model must not be the sole evaluator.
- Best-of-N is useful only when an executable oracle can select the winner.
- A final message is not proof of filesystem, database, deployment, browser, or
  external-system state.
- The JSON record is structured evidence, not a tamper-proof attestation. Prefer
  CI logs, signed commits, deployment records, or an independent reviewer for
  high-risk claims.
- Repository-state binding refuses a home/root repository, does not follow
  untracked symlinks, redacts common secret-bearing paths, and fails closed when
  file/count/byte budgets prevent a complete bounded fingerprint.

Read [failure-modes.md](references/failure-modes.md) when diagnosing model,
context, decoder/search, or long-horizon failures.
