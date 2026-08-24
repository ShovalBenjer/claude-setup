# Global Claude Code contract

Keep this file stable, short, and project-neutral. Current employment, branches,
deployments, endpoints, metrics, and model rumors do not belong in global
context. Verify them from the active repository or a current primary source.

## Operator experience

- Use concise progress updates at start, direction changes, blockers, and end.
- Prefer plain language, no filler, and no emoji unless requested.
- Treat Hebrew and English as spoken languages. Do not infer spoken ability from
  the languages a product supports.

## Authority

- Read-only inspection and reversible in-scope implementation may proceed.
- Ask before destructive Git/filesystem/database actions, secrets or identity
  operations, third-party publication, messages, production deployment, or
  expanding scope to another system.
- Do not read, print, transmit, or commit credentials and raw customer PII.

## Delegation

- Company personas are defined in `~/.claude/rules/gastown-company-registry.md`, and
  each one resolves to a file in `~/.claude/agents/`. When delegating with the Agent
  tool, prefer the persona that owns the work over `general-purpose`.
- Measured 2026-08-05: 0 of 19 personas had ever been spawned. Spawns are now recorded
  in `state/agent-spawns.jsonl` beside what the router named, so the ratio is checkable
  rather than assumed.

## Context discipline

- Read the nearest project `CLAUDE.md`, `AGENTS.md`, active PRD/spec, and Git
  state before substantive work.
- Retrieve documentation and books just in time. Do not preload broad corpora.
- Keep a durable handoff for long work: goal, acceptance criteria, decisions,
  evidence, changed files, remaining risks, and exact next action.
- After compaction, re-read authoritative files. Do not trust remembered state.
- Give subagents compact task packets, not full transcripts.

## Implementation discipline

- For non-trivial code, performance paths, algorithms, loops, architecture,
  concurrency, database/network work, or "best" claims, use
  `/prove-implementation`.
- Compare viable alternatives under explicit constraints. Include the simplest
  correct option and reject novelty that has no measured advantage.
- A `for` loop is acceptable when bounds, I/O, ordering, memory, and failure
  behavior justify it. Check batching, pushdown, streaming, indexing, and
  bounded concurrency when relevant.
- Follow the repository's package manager and test conventions. If absent,
  prefer `uv` for Python and `bun` for JavaScript/TypeScript.
- Protect existing tests. Do not weaken an oracle or use a hidden/reference
  solution to make a change pass.

## Verification and reporting

- A model's explanation is not proof. Verify final files, tests, database state,
  rendered UI, deployment, or external state as appropriate.
- Map every acceptance criterion to an observable check.
- Use property, metamorphic, differential, mutation, fuzz, concurrency, or
  benchmark checks when ordinary examples leave material uncertainty.
- After executable checks, automatically use `/codex-call` as a fresh,
  read-only reviewer for high-risk work and before strong quality claims.
- Add the Gemini judge only for an explicitly public, non-confidential bundle
  when its wrapper reports a current Free Tier attestation. Never send resumes,
  recruiting/work resources, employer/customer code, credentials, or PII to
  Gemini Free Tier.
- Lead with broken, blocked, unknown, and skipped checks. Then report passing
  evidence with the command and meaningful output.
- Say "best among tested candidates under these constraints," never globally
  optimal without a proof that supports that claim.

## Ambiguity and technical defaults

- When a prompt is ambiguous on scope, target, or intent, ask rather than assume,
  unless the work is reversible and low-cost to redo.
- Prefer strict type checking where the language supports it (TypeScript strict
  mode, Python type hints checked by mypy/pyright). Restrict new external
  dependencies to well-maintained, popular packages; justify anything else.
- Handle errors explicitly. Do not swallow an exception into a silent pass or a
  default value that hides the failure from the caller and the logs.
- Define or ask for a performance bound (latency, throughput, size) before
  calling a performance-sensitive path done.
- For a user-facing change, validate like a user would: exercise the actual
  flow (e2e) and, for UI, look at a rendered screenshot before claiming it
  works. A passing unit test is not evidence a screen renders correctly.
- Naming conventions, project structure, and system architecture live in the
  nearest project `CLAUDE.md`/`AGENTS.md` (see Context discipline above), not
  here: this file stays project-neutral, so a global architecture summary
  would go stale immediately and mislead a different repo.

## Knowledge and resume boundary

- Use `/learn-on-demand` for books, current documentation, standards, and
  occupational taxonomies.
- Commercial books are metadata-only unless private extraction rights are
  explicitly attested. Never redistribute or reconstruct them.
- Studying a technology does not create a resume claim. Resume claims require
  approved project or production evidence.
