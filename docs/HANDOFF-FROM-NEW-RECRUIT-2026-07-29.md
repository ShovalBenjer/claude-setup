# Handoff: numerical stack preference was invisible to general sessions

From the `new-recruit` voice-metrics work, 2026-07-29.

## What happened

I built an embedding and a corpus-statistics pipeline on NumPy plus the stdlib
`statistics` module. The operator's reaction: the Polars/Numba preference was
stated in past work and had rules for it.

He was right that it exists. It was written in:

- `dot-agents/skills/notebook/SKILL.md` — "polars, never pandas", `@jit` for hot
  numerical loops
- `dot-agents/skills/review/SKILL.md` — the pandas → polars swap table
- `dot-claude/agents/data-bureau.md`, `evidence-clerk.md`,
  `latent-systems-lab.md` — DuckDB/Polars for tabular state

**Every one of those loads only when that skill or agent is invoked.** I invoked
none of them, because the task did not look like "data science" or "review" from
the outside: it looked like building a text scorer. So the preference was
present in the repository and absent from the session.

`~/.claude/rules/` had 16 rules and none covered the numerical stack.

## The fix, already applied

New standing rule: `dot-claude/rules/numerical-stack.md`, synced to
`~/.claude/rules/`. Canonical and live are in sync at 17 rules.

Per `docs-control-plane` the rule is the single authoritative location; this
handoff does not restate it. Read the rule for the actual guidance.

The short version of *why it is a three-way split, not "use Polars"*: Polars
replaces pandas for tabular work, Numba replaces hot Python loops, and NumPy
stays for linear algebra. "Use Polars" is the wrong instruction for an
eigendecomposition, and a rule that said so would be ignored the first time it
was obviously wrong.

## Concrete debt in `~/.claude/skills/voice-metrics/`

Not fixed. Listed so it is not rediscovered.

| file | what it does now | should be |
| --- | --- | --- |
| `profiles.py` | `statistics.median` / `pstdev` over Python lists, ~35k messages, per metric | Polars expressions over a DataFrame; the percentile set is one `quantile` call per column |
| `voice_engine.py` `_counts()` | per-n-gram Python loop, roughly 7.8M iterations, memoised `blake2b` | the genuine `@njit` candidate, and the actual bottleneck |
| `voice_engine.py` `load_threads()` | `sqlite3` cursor into Python lists, filtered with a comprehension | Polars `read_database` or DuckDB over the SQLite file, filtered lazily |
| `voice_engine.py` PCA | `np.linalg.eigh` on a 2048×2048 covariance | **correct as-is.** Leave it in NumPy |

The measured behaviour of the skill (88% real-message pass rate, 0-12% impostor)
is unaffected by any of this: it is a performance and house-style debt, not a
correctness one. Do not let a rewrite silently change the scores; the validation
harness is `validate_scorer.py` and it should produce the same numbers after.

## The general lesson for the setup repo

A preference encoded only inside a skill is conditional on that skill being
recognised as relevant, and relevance is judged from the surface of the task.
Anything meant to hold across all sessions belongs in `dot-claude/rules/`.

Worth an audit: which other standing preferences currently live only in skill or
agent files, and would be equally invisible to a session that never triggers
them.
