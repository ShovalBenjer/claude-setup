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
