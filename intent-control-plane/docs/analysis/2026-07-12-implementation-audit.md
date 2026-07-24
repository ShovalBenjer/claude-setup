# Implementation quality audit (2026-07-12)

Independent adversarial audit (6 read-only reviewers) of the 18 modules built this session, graded
A-F per file against docstring / types / error-handling / correctness / simplicity / testing. Full
JSON in the workflow output (wx47he7pc). This is the fix backlog; lift each to the standard (research
prompt: ~/docs/research/prompts/2026-07-12-code-implementation-quality-standard.md) then re-audit.

## Grades

Mean overall ~ 2.44/4 (C). Distribution: A=1, B=7, C=9, D=1.

| file | overall | docstring | test | H/M/L |
|---|---|---|---|---|
| durable.py | A | A | B | 0/2/2 |
| archive.py | B | A | B | 1/2/3 |
| transitions.py | B | B | B | 1/0/4 |
| routing.py | B | B | C | 0/2/4 |
| provenance.py | B | A | C | 1/2/3 |
| guardrails.py | B | A | B | 1/3/2 |
| cache.py | B | A | B | 0/2/5 |
| observe.py | B | A | B | 0/1/3 |
| company.py | C | B | C | 0/2/3 |
| rubric.py | C | B | C | 1/3/1 |
| symbol_graph.py | C | A | C | 1/2/3 |
| codebase_map.py | C | A | C | 1/2/2 |
| roster_evolution.py | C | B | C | 1/3/2 |
| fleet_init.py | C | B | C | 1/3/2 |
| memory.py | C | B | C | 1/3/3 |
| reliability_policy.py | C | B | B | 1/1/3 |
| spawn_grade.py | C | B | C | 3/2/4 |
| swarm.py | D | B | D | 2/2/1 |

## High-severity findings (16) — the fix list

1. swarm.swarm_pass: kept-set is order-dependent, defeats "keeps only those that beat the running baseline".
2. swarm.gradient_flat(patience=0): unguarded ValueError (empty max()).
3. rubric.score_rubric: the deterministic-disposes safety property has a gap.
4. symbol_graph.extract_symbols: DEF_KINDS drops arrow functions + const-class expressions (JS/TS undercount). [FIXING NOW - breaks the widgora map]
5. codebase_map.build_file_map: does not guard extract_symbols/extract_imports (only read_text) - a parse error crashes the whole walk.
6. roster_evolution.validate_rehire: held-out gate is a no-op when held_out_baselines is empty/falsy.
7. fleet_init.fleet_report: the real entry point has zero direct test coverage.
8. memory.EmbeddingBackend: declared + shape-tested but zero real call sites (unwired).
9. reliability_policy (whole module): next_model_on_error/should_retry/backoff_seconds/injection_flags have zero callers (unwired).
10. spawn_grade._main: the only production entrypoint (called by gastown-spawn) is never tested.
11. spawn_grade + company: live cross-module bug - real spawns emit "scored", company.trust_score treats non-"kept" as -15, tanking trust.
12. spawn_grade.grade_spawn: criteria without results silently degrades to "scored" instead of failing closed (Codex-flagged).
13. archive.keep_verdict: held_out/held_out_baselines same-typed + positional; a caller swap silently inverts the regression gate.
14. transitions.advance_pass: check-then-insert TOCTOU race across two unsynchronized sqlite connections, no transaction/lock.
15. provenance.classify_commit: plain-English fixes ("Fixed the login bug") misclassified as "other".
16. guardrails._GAMING_PATTERNS: check-suppression only matches camelCase continueOnError, misses common forms.

## Systemic (cross-cutting)

- dict[str, Any] used as DTO across all row builders; no TypedDict/dataclass shape guarantee.
- Several modules are unwired scaffolds (company, memory, reliability_policy, fleet_report) - wire or remove (ponytail).
- Tests are happy-path heavy; few property/mutation tests despite clear invariants.
- Function-level docstring coverage inconsistent (helpers often bare).

## Sequence to A

1. Fix the live-impact highs now (arrow-function undercount #4, the spawn "scored" bug #11/#12).
2. Run the standards research (prompt above) -> control doc.
3. Fix-pass on the remaining highs + systemic (TypedDict DTOs, wiring-or-removal, docstring coverage, property tests).
4. Re-audit; target mean B+ then A.
