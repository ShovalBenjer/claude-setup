# Deterministic preflight: proposal (not built)

Status: PROPOSAL, operator-originated 2026-07-29, needs /diverge on the recipe
format and runner shape before any build (charters rule 2). Filed from the
operator's framing, in his words: current skills and tools "dont have the
turning it into deterministic presteps (like a notebook for training llm, all
the important steps before actually training a model), just in this case its
for inference only, then same for each implementation, review,
validation/verification etc."

## The defect this names

A training notebook works because everything before the nondeterministic step
is fixed: data prep, tokenization, config, seeding run in a known order and
leave artifacts, so a skipped step is visible in the outputs. This harness has
the opposite shape around its nondeterministic step (the model acting): the
pre-steps live in skill prose and rule files that fire only when the task is
RECOGNIZED as matching them. The 2026-07-29 new-recruit handoff documents the
failure exactly: the Polars/Numba preference existed in three skills and was
invisible to a session whose task did not look like data science from the
outside. Recognition-gated guidance is nondeterministic preflight.

What exists today enforces at the WRONG END: the gate and Stop hooks judge
after the work (post-flight), prompts and rules advise before it but nothing
REQUIRES the advice to have been consumed. Enforcement map:
docs/analysis/2026-07-29-session-retro-modes-models-workflows-observability.md
sec 5.

## Proposed shape (to be diverged, not final)

Per activity class, a RECIPE: an ordered list of deterministic steps, each
producing a recorded artifact, run before the model acts.

- implement: resolve ticket and claim row; read the owning layer per
  repo-stack-reasoning; name the oracle that will prove the change and the
  regression that will fail first (tdd-enforcement); name stack constraints
  from rules (numerical-stack, orjson class); emit acceptance criteria.
- review: resolve the diff scope and blast radius; load the avoid-list and
  check registry; declare the verdict schema before reading the code.
- validate/verify: enumerate claims made; map each to an executable check;
  declare what a PASS will not assert (RT-3).
- research: declare the three-vocabulary search set before searching
  (prior-art-gate already half-does this at Stop; move it to pre).
- inference (external judges): resolve model, quota headroom, and the exit
  code contract before the first request (tools/openrouter and tools/nvidia
  already do this in code; the recipe generalizes it).

Runner: recipes as data (JSON schema, versioned in-repo), one small stdlib
runner that executes a recipe and appends a preflight record keyed to the
prompt ticket (intent-control-plane already mints PT ids at UserPromptSubmit).
The Stop gate then gets one new check, the whole enforcement point in one
line: an ACT-class turn with no preflight record for its ticket gets the same
corrective turn a handback gets today. That converts every rule the recipes
reference from advice into a step that is measurably present or absent.

## Why this fits the stack (repo-stack-reasoning applied)

Stdlib runner plus JSONL records matches every existing oracle's shape; no
server, no framework. The flexibility the operator asks for lives in the
recipe DATA, which any session can extend, while the runner stays frozen and
selftested with a mutation spec like every other oracle, or it repeats L017.

## Explicitly out of scope until diverged

Recipe format alternatives (JSON vs literate .md-with-commands vs Python
registry), whether recipes nest, whether preflight blocks or only records for
the first two weeks (measure-first per RT-1's lesson), and which activity
class pilots first.
