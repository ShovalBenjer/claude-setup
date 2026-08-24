# Global Setup + Per-Project Suggestions (2026-07-08)

Grounded in: the `~/docs` SOTA corpus (the 6 stack reports + gap-analysis + maturity map), the
2026-07-08 GitHub-trending research, the maturity-signal scan of `~/projects`, and the persona/
contract recon. Per-project detail is written as `MATURITY-TODO.md` inside each repo; this doc is
the global layer plus the cross-project summary.

## Through-line
The setup's recurring defect is prose-not-enforcement: skills, personas, contracts, and the forge
loop live as instructions the model may ignore, not as hooks/gates the harness runs. 2026-07-07 fixed
the intent recall + skill router + Codex-review-on-push. What remains global is persona routing,
contract enforcement, and a self-improvement loop.

## Global setup backlog (prioritized)

G1. SELF-IMPROVEMENT LOOP (highest leverage; new build). Weekly Codex-run job over the existing
    substrate (`~/.intent/intent.db`, `~/.claude/cache/a2a/audit.jsonl`, `~/.claude/cache/sessions.db`):
    score completed intents (proof attached? expectation met?), reflect on failures and propose
    router/skill/persona diffs (GEPA-style reflective rewrite), curate skills/personas by real usage
    and flag never-fired ones for prune/merge (Hermes create-curate-evolve), emit a diff for human
    approval. Closes the forge REFLECT axis with code. Refs: gepa-ai/gepa, NousResearch/hermes-agent-
    self-evolution, Google Agent Quality Flywheel.

G2. CONTRACT ENFORCEMENT (turn contracts from comments into gates). (a) Backfill `allowed-tools`
    frontmatter on the skills that touch sensitive tools (only 2 of 61 declare it today). (b) Wire the
    idle `verification-before-completion.sh` hook to the intent-plane `proof_required` so a completion
    without the contracted evidence is blocked. (c) Keep boundary-contracts as the code-seam contract.

G3. PERSONA AUTO-ROUTING. Extend `prompt-router.sh` to inject the owning gastown persona per task
    alongside candidate skills (one block; persona routing == skill routing). Personas are currently
    prose in gastown-company-registry.md with no loader.

G4. EVAL GATE (from gap-analysis, still open). promptfoo + DeepEval invoked from a pre-push hook,
    block on regression-vs-baseline; Inspect AI to drive Claude/Codex as the eval subject. OpenAI Evals
    is being retired 2026-11-30; promptfoo is the migration target.

G5. AGENT-SDK for recurring workflows. Move the weekly audit + eval pipeline + G1 loop off
    conversational Task-tool fanout onto anthropics/claude-agent-sdk-python for typed hooks and real
    subagent tracing (`parent_tool_use_id`).

## Patterns to steal from the 2026-07-08 trending research (learn-from, not adopt-wholesale)
- Portable SKILL.md registry (obra/superpowers, anthropics/skills): ship gastown personas + forge rules
  as skills that run unmodified from Codex CLI, not only Claude Code. Diff superpowers' skills against
  gastown and port the gaps (systematic-debugging, using-git-worktrees).
- Spec-kit slash commands (github/spec-kit): make the PRD Control Plane executable as
  /specify -> /plan -> /tasks -> /implement instead of ad hoc.
- Worktree-per-agent isolation (AgentWrapper/agent-orchestrator): any time >1 agent edits the same repo,
  give each its own worktree+branch+PR (the workflow tool already supports isolation: 'worktree').
- Reversible context compression (headroomlabs-ai/headroom): front CRM/eval/log tool outputs through a
  compressor before they hit a subagent's context; keep it reversible so evidence can be re-fetched.
- Temporal memory (getzep/graphiti): facts with validity windows, so a project decision or prior finding
  is superseded instead of going silently stale in a flat memory file. Candidate upgrade to intent recall.
- Architectural-health MCP (sentrux): expose the Layer-7 sensor as an MCP tool with an ungameable
  geometric-mean score so any agent can query structural health mid-session.
- Context-handoff serialization (earendil-works/pi): study how it hands a Claude reasoning trace to a
  different model, directly relevant to the Opus-orchestrator / Codex-executor split.
Security caveat: openclaw's community skill marketplace had ~11-12% malicious uploads; never run
untrusted skills against anything holding Azure/Jira/CRM credentials. Sandbox first.

## Cross-project maturity (signal scan 2026-07-08; not depth)
Systemic gaps, worst first:
1. Type-checking enforced in only 2 of 9 repos (mypy/pyright/strict-TS). Your typed-DTO rule is declared,
   not checked. Biggest single gap.
2. ADRs: 0 of 9 repos. No architecture decision recorded anywhere. Cheapest maturity win.
3. call-analyzer-frontend: 0 tests, no CI (weakest repo).
4. qc-telephony-api: no lockfile (dep reproducibility on a prod API).
5. Lint missing: sales-agents, video-understanding, ORM-AGENT root.
6. ORM-AGENT + video-understanding: no root manifest (monorepo language ambiguity; root tooling absent).
Per-repo actions are in each repo's `MATURITY-TODO.md`.

## Stack direction (from the landed stack-SOTA reports + rust-vs-python)
- Python-first stays correct for the AI/CS-agent/data domain. Reach for Rust only behind a measured
  benchmark, and prefer a PyO3/maturin extension over a rewrite (you already run ruff/uv/polars/pydantic-
  core, all Rust-backed Python). Detail: `~/docs/Polyglot Stack Selection...`, and the rust-vs-python prompt.
- Right-size rigor to maturity stage (POC vs prod): `~/docs/Code Maturity Ladder...`.
- Dedup without over-abstraction (AHA/rule-of-three), wire a duplication detector as a non-blocking CI
  signal: `~/docs/Code Reuse, Deduplication...`.
- Architecture: simplest-that-works, modular-monolith-first, enforce with ADRs + one fitness function:
  `~/docs/System Architecture & Design Patterns SOTA...`.
- API: contract-first, RFC 9457 errors, keyset pagination, breaking-change gate: `~/docs/API Design...`.
- Persistence: Postgres-by-default + extensions; raw+codegen over ORM where it wins: `~/docs/Data & Persistence...`.

## Recommended sequence
1. G2 contract gate + G3 persona routing (small, extend hooks I already built).
2. G1 self-improvement loop (the difference-maker; Codex-run, human-approved diffs).
3. Per-repo: enforce type-checking (gap 1) and add one ADR each (gap 2); fix call-analyzer-frontend
   tests+CI and qc-telephony lockfile.
4. G4 eval gate + G5 Agent-SDK once the loop exists to consume the eval signal.
