# ADR 0001: One unified platform standard, enforced by the intent-control-plane

- Status: Accepted
- Date: 2026-07-10
- Deciders: Shoval
- PRD: `docs/prd/2026-07-10-platform-standard.md`

## Context

The estate is ~12 private Azure DevOps repos plus a local Claude/Codex harness. There was no
unified standard, so each repo diverged (the six-dimension scorecard puts none above 12/17,
worst at 5/17). The cs-agent pipeline is the strongest baseline (blocking security/lint/type/
test gates, a Foundry Codex reviewer posting resolvable threads) but its review is advisory,
it has a stage branch with no stage resource, and its shape is not enforced elsewhere. The
harness (`intent-control-plane`) already maps and scores every repo. Research (OpenSSF
Scorecard, google/eng-practices, real fetches of jax/ruff/uv/pydantic/fastapi) showed the
elite bar is CI-as-product + verifiable releases + docs-as-tested-code + a supply-chain
dimension, not the community-health ceremony most elite repos actually skip.

## Decision

Adopt ONE platform standard and make the `intent-control-plane` the platform brain:

1. A canonical repo structure per class (product-service, harness, agentic-langgraph) and a
   six-dimension compliance score (repo-org, code-health, docs, testing, CI/CD, supply-chain),
   scored deterministically by `intent_control_plane.standards`.
2. Enforcement by mandatory Codex-review plus comment-resolution branch policies and stage/prod
   promotion, rolled out advisory then required with severity routing.
3. A Codex-first, Haiku-fallback delegation flywheel that turns scorecard gaps into verified
   work on stage branches.
4. Sim-before-real (Mojuco): a deterministic-first eval pyramid and a sim-reviewer before real
   Codex, to bound cost, with the simulation calibrated against real outcomes.
5. The standard is Azure-translated, not a cargo-cult of the GitHub-OSS bar (skip PyPI Trusted
   Publishing, OSS-Fuzz, CODEOWNERS, community bots).
6. A concurrent-session guard is part of the standard: because multiple Claude/Codex sessions
   share the HOME repo, every shared-repo destructive/git-hygiene op is gated on a pre-flight
   live-session check (added after a 2026-07-10 collision where a git-hygiene pass broke a live
   parallel session's worktree).

## Alternatives considered

- A full IDP (Backstage/Port catalog + scorecards): heavier than a solo team needs; the
  `standards` scorer + `dashboard` TUI are the lighter equivalent.
- cs-agent as the golden template verbatim: it is a baseline, not elite (advisory review, no
  stage env, no supply-chain dimension).
- Per-repo ad-hoc standards (the status quo): produces the divergence we measured.

## Consequences

Positive: every repo is measurable and comparable; gaps become a delegation queue; the setup
becomes one localizable system; the elite deltas are adopted where they pay (CI-as-product,
supply-chain) and skipped where they do not (OSS ceremony).

Negative: the `intent-control-plane` becomes load-bearing, so it must be git-versioned (done
2026-07-10, commit `1e05912`), packaged (still needs a `[build-system]` so it runs without
`PYTHONPATH`), and reliable; the mandatory-review gate risks noise (mitigated by severity routing
and an advisory-then-required rollout); a stage environment adds some cost even scaled to zero;
the concurrent-session guard adds a pre-flight check to shared-repo writes (accepted cost, given
a real collision already occurred).
