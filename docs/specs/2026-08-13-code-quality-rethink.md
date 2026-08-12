# Spec: cross-project tech-stack + code-quality rethink (operator directive)

PRD: none yet (this spec seeds it). Ticket: TODO. Status: active.

Operator, 2026-08-13, verbatim intents:
1. Reasoning task ACROSS ALL PROJECTS: rethink tech-stack choices, search modern
   libs, and rethink code implementation level accordingly.
2. Code-level conventions questioned: "common bro for loops? sick of it", "lame
   commenting", one-line docstrings as convention vs PEP 257 / full Google-style
   docstrings ("maybe i dont know enough": wants a reasoned recommendation, not
   compliance).
3. Type safety + a SIMULATION LADDER: static -> compile -> runtime -> container
   simulation runs -> E2E, modeled on how video games ship: tiny agents as test
   players, open-alpha / open-beta stages inside the testing pyramid ("egyptian
   pyramid im building, all of this for code to be better").
4. Specing, planning, and research grade are LACKING in his flow; find where the
   system falls short against: Matt Pocock (TS/type-safety pedagogy), Andrej
   Karpathy (agent/eval/simulation thinking), BetterStack (observability/stack
   practice), and relevant others.
5. Use agents for the research.

Grounding already on disk: stdlib demotion (repo-stack-reasoning.md 2026-08-13),
block/buzz adoption handoff, minimalism audit (code found clean but conventions
never challenged), testing-pyramid skill (static list, no simulation stages).

## Round-1 findings (2026-08-13, two of three agents delivered; sim-ladder agent
## fully blocked, that axis reruns in the lead loop)

The twist (VERIFIED from the repo's own files): the conventions the operator is sick
of are not even the repo's standards. intent-control-plane/docs/specs/
2026-07-12-coding-style-standard.md, status active, already mandates SUBSTANTIVE
docstrings ("mandatory and load-bearing", not one-liners) with ruff D100-D107
pending on a 76-item backfill, and already bans accumulator loops mechanically
(ruff PERF401/C4/SIM/PIE, enforcement "on"). The root repo simply never adopted
that config: no root ruff config found. So "bro for loops" and "lame one-line
docstrings" are a CONFIG ADOPTION gap, not a convention to invent.

Ranked actions from round 1 (each independently acceptable):
1. Add run_id/span correlation ids to every state/*.jsonl write + thin OTLP-shaped
   adapter (BetterStack axis, VERIFIED vs betterstack.com observability guide:
   ledgers today cannot answer "every event of run X in order").
2. Adopt intent-control-plane's ruff config (PERF/C4/SIM/PIE + D-rules) at repo
   root; flip D-rules on after a docstring backfill batch. Kills the loop/docstring
   complaints with existing, already-written standards.
3. Devcontainer or Nix pin for the Python toolchain: converts the two "permanent"
   WSL2 test failures (AGENTS.md known gaps) into reproducible/fixable.
4. Gate-enforced spec-before-PR: docs/specs entry with Status: active required for
   non-trivial PRs (spec culture exists, enforcement does not).
5. Type policy: strict at boundaries (mypy strict exists in intent-control-plane;
   root has none). NOTE the agent's "keep stdlib-only, no pydantic" lean predates
   the same-day stdlib demotion: rerun that choice through /diverge.
6. Simulation ladder (game-style alpha/beta with tiny agents): UNSOURCED this
   round, agent had no tools; runs in the lead loop next session.
