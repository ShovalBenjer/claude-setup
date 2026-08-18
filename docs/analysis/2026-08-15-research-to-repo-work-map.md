# 2026-08-15: research to repo work map

Companion to `2026-08-15-research-context-audit-and-forecast.md`. That file holds
the verdicts and the forecast; this file converts every applicable item from the
five operator-supplied research documents into concrete work, one section per
repository, each item with an acceptance check phrased as a falsifier. Items that
failed the audit (catalytic KV caches, univalent kernel verification, invented
aesthetics formulas) appear in no backlog.

Ordering inside each section is by leverage, not effort. The cross-repo build
order stays: agenteval-bench first, the crosscoder repo second, the probe
verifier third.

## claude-setup (this repo, lane A)

1. TAR trajectory schema. Formalize the shape the ledgers already have into a
   declared schema (thought, action, result, refs, hash fields) and emit gate
   runs as schema-valid trajectory artifacts. Falsifier: a validator command
   exits nonzero on a hand-broken trajectory row and zero on
   `state/gate-runs.jsonl` derived output.
2. Diversity metric in prose_metrics. Add a self-similarity measurement over
   candidate outputs (the Artificial Hivemind grounding) alongside the existing
   sentence statistics, measurement-only first, threshold after a distribution
   is fitted, same as the current CV metrics. Falsifier: two near-identical
   candidate sets score higher similarity than two disjoint ones in the
   selftest.
3. LLM-directed mutation-spec pilot. Generate candidate mutation specs for the
   modules `mutate.py` currently leaves unguarded (`selfimprove/scan.py`,
   `slop_lint.py`, `memory/web_to_memory.py`, `local/reflex_router.py`), keep
   the named-check attribution rule, human-review each spec before adoption.
   Falsifier: `mutate.py --spec` on an adopted generated spec turns at least one
   selftest red per target.
4. slop_lint selftest. The prose gate is the only oracle without one. Falsifier:
   a planted banned phrase and a planted spaced connector dash each produce exit
   1 in the selftest.
5. scan.py repairs. Remove the one-proposal-per-run break, replace the
   hand-picked additive constants with counts surfaced as evidence rather than a
   pretend score, add a selftest. Falsifier: a fixture repo with three untested
   tools yields three proposals, not one.
6. ICM citation. One paragraph in the docs naming arXiv 2603.16021 and the
   intermittent active inference result (doi 10.3390/e28030269) as the published
   formalizations of this repo's filesystem-as-architecture and event-driven
   wake patterns. Falsifier: `codemap.py check` and `slop_lint.py` stay green.

## agenteval-bench

1. TAR data model. Replace string-in string-out cases with trajectory objects
   (ordered thought, action, result triples plus metadata). Falsifier: the
   golden-replay CI gate runs a trajectory fixture end to end.
2. Hash-chained trajectory storage. Port `canonical`, `row_hash`, `file_lock`
   from claude-setup `tools/bus/bus.py` (stdlib only). Falsifier: a tampered
   middle row is detected by a verify command.
3. Real schema validation. Replace the key-presence check with `jsonschema`,
   including nested types. Falsifier: a payload with a wrongly typed nested
   field fails where the current code passes it.
4. Enforce or delete dead parameters. `run_ci` threshold and `max_input_tokens`
   either gate behavior or leave the API. Falsifier: a suite passing 3 of 4
   cases fails `run_ci` at threshold 0.9.
5. Step-level process scoring. PRM-style per-step verdicts (thought-action
   alignment, action-result consistency) alongside outcome scoring, following
   the ASE 2025 trajectory-relationship labels. Falsifier: a fixture trajectory
   with a correct final answer but a contradicted intermediate step scores below
   a fully consistent one.
6. README truth pass. Move unshipped features (LLM judge, compare, reports)
   under a roadmap heading. Falsifier: every capability sentence in the README
   names code that exists.

## sqltok

1. Commit benchmark artifacts. Run the BIRD recall benchmark, commit results
   under `benchmarks/results/`, link them from the README claim. Falsifier: the
   97.4 percent full-recall figure is reproducible from a committed artifact, or
   the README figure changes to the measured one.
2. Execution accuracy run. The README marks it pending; run it via the official
   BIRD script path already delegated to. Falsifier: a committed result file
   carries the number the README cites.
3. Curriculum write-up. The CELF plus KMS plus MinHash implementation is the
   account's best algorithmic evidence; a lesson unit in the learning platform
   (see curriculum unit r1-token-budget-selection, R1-07) sources directly from
   this code.

## new-recruit (lane B)

1. Ledger-derived resume claims. A generator that emits every quantitative
   resume line from a ledger row, each with an attached falsifier, refusing
   lines with no row. The five research documents' invented resume metrics are
   the anti-pattern this exists to prevent. Falsifier: a resume line with no
   backing ledger row fails the build.
2. Funnel metrics surfacing. The measured numbers (submitted, interviews,
   approvals) rendered in the dashboard, honest zeros included. Falsifier:
   dashboard payload equals a ledger query, not a constant.

## protobuf-fuzz-guard

1. SCC cycle detection. Mutual recursion (A to B to A) is currently caught only
   incidentally by the depth heuristic; add strongly-connected-component
   analysis over the message reference graph. Falsifier: a two-message cycle
   fixture fires the recursion rule with the depth rule disabled.
2. Disclosure line. Until item 1 ships, the README states the direct-only
   limitation. Falsifier: the limitation sentence exists or the SCC rule does.

## daily-deep-learning (lane C)

1. Ingest the frontier curriculum. `2026-08-15-frontier-curriculum.md` in this
   directory holds eight tracks of unit specs written to the platform's unit
   contract (hook, know-by-end, intuition, precise definitions, drill, SRS
   cards). Register units in `tools/build_curriculum.py` in dependency order,
   author Hebrew bodies per the house style, respect the curriculum budget
   check: add tracks incrementally, R0 and R4 first. Falsifier: the platform's
   own CI (budget check, link validation) stays green per increment.
2. SRS seeding. Each unit spec carries card candidates; import them so review
   scheduling starts with the unit, not after it.

## New repository: crossdiff (the ML gap filler)

Scope from the audit, deliberately narrow. BatchTopK crosscoder over a small
base and chat pair (Gemma-2-2B class), reproducing the latent-decoupling
findings of arXiv 2504.02922 so every claim is checkable against published
numbers. Milestones: activation caching, crosscoder training, latent scaling
diagnostic, a written comparison table against the paper. Falsifier per
milestone in the repo's own README from day one; no metric appears in prose
before its artifact is committed. This is the R3 capstone in the curriculum.

## New repository or module: probe-verify (second priority)

Linear safety probe on final hidden states of a small open model, then Z3 bounds
over an input box proving the probe's threshold cannot be crossed inside a
declared safe region, per the verify-the-monitor forecast line. Small, real
formal-methods entry; the R5 capstone. Falsifier: the SMT certificate is checked
in and re-derivable by a committed script.

## Explicitly not scheduled

Catalytic memory management, GWT orchestrator (this repo already is one),
categorical rewrites of working code, photonic or PIM anything, hyperbolic
typography. Real reading, no build. The curriculum carries them as theory units
with an anti-hype note where they earn one.
