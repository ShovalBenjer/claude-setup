# nexus-engine-rs

A native, physics-driven viewer over the plan surface of this repo. Nodes are rigid bodies,
links are springs, the cursor is a force field. Built from
`~/Downloads/gemini-code-1785458291930.md`.

**Status: a working vertical slice, not the spec.** Read the scope table before assuming a
module exists.

## Run

```bash
python ../../command_center/plan_export.py     # produces command_center/plan_data.js
cargo run --release                            # opens the window
cargo run --release -- --check                 # headless: parse + count, no window
cargo test                                     # 8 tests
```

`--check` exists because "it compiles" and "it reads your repo" are different claims. It
loads the real artifact and prints the counts without needing a window server.

## How it is put together (standard shape, not a new idea)

**This and `command_center/plan_console.html` read the same file.** One contract
(`plan_data.js`, produced by `plan_export.py`), two viewers: a browser console that works
over `file://` on a phone, and this native window for shoving a graph around on a desktop.
Both write the same `state/plan_decisions.json`, so a decision made in either is picked up
by the next export. Neither is the source of truth; the exporter is.

That is also why `models.rs` parses the `window.PLAN_DATA = ...;` JS assignment instead of
emitting a second `.json`. A second file is a second thing that can be stale.

### Prior art, because this was briefly written up as if it were the interesting part

Searched 2026-07-31. Exact queries:

1. `software architecture visualization interactive graph tool survey research`
2. `docs-as-code architecture decision record approval workflow tool JSON single source multiple renderers`
3. `force-directed graph note viewer Obsidian graph view plugin physics knowledge base awesome list`

Every not-a-gap signal fires, so the "one contract, two viewers" framing is **retracted** as
anything but ordinary engineering:

- **Survey exists.** Software architecture visualization is a surveyed field with a
  published evaluation framework of seven areas and 31 features applied across six tools.
- **The exact pattern is a shipped product.** Structurizr is explicitly a
  "model once, render many" models-as-code tool for C4: the model is the source of truth,
  views are derived, and it carries a decision log so ADRs sit beside the model. That is
  this design, already built, with more of it. Log4brains and DocToolChain occupy the same
  space for ADR publishing.
- **Curated list / plugin category exists.** Force-directed graphs over a markdown vault
  with live physics controls is a populated Obsidian plugin category (19 plugins tagged
  `#graph`), including 3D variants with tunable repel/link/centre forces.
- **The approval workflow is a known pattern too:** ADRs in git with a pull request as the
  proposed-to-accepted transition.

What is actually particular here is narrow and worth stating as such: this reads *this
repo's* state (the `plan-divergence` ledger, the gate, `plan_export.py`'s refusal to infer a
status from markdown) and renders in *this repo's* locked palette. That is integration, not
invention. If the goal were the shortest path to reviewing architecture, Structurizr is the
honest recommendation and this is not.

## Scope against the spec

| Spec module | State | Note |
|---|---|---|
| `models.rs` | **built** | kinds are the ones that exist on disk (prd/adr/spec/research/analysis), not the spec's C4 levels, which nothing here produces |
| `physics/engine.rs` | **built** | rapier2d bodies, collider hulls, cursor impulse field |
| `views/canvas.rs` | **built** | egui canvas, click-select, kind columns, filter |
| `sandbox/` ContractLock + RevertSandbox | **not built here, deliberately** | it exists in Python as the `plan-divergence` skill; a second implementation would fork the ledger. This reads that ledger. |
| `gpu/shader.wgsl` SDF background | **not built** | a real gap |
| `views/diff_panel.rs` | **not built** | a real gap |
| `views/timeline.rs` | **not built** | a real gap |

## Deviations from the spec, each with a reason

- **Crate versions.** The spec pins `eframe 0.28`, `wgpu 0.20`, `rapier2d 0.18`. Current is
  `eframe 0.35`, `rapier2d 0.34`. Both changed APIs that the spec's code shape depends on:
  rapier moved to glam `Vec2` and dropped an argument from `PhysicsPipeline::step`, and egui
  replaced `App::update(ctx, frame)` with `App::ui(ui, frame)` and collapsed
  `SidePanel`/`TopBottomPanel` into one `Panel`. Pasting the spec verbatim does not compile.
- **Edges are spring forces, not `ImpulseJointSet` distance joints.** At 58 nodes and 1 edge
  the visual result is identical and the joint API is the part of rapier that moves most
  between releases. Revisit past a few hundred edges.
- **Rotation is locked on every body.** A tumbling label is unreadable. This is a diagram.
- **No gravity.** Nodes rest at their column anchor instead of piling up at the bottom.

## The bug the tests caught, kept here because it will recur

This world is measured in **pixels**, not metres. A node collider is 92x22 units, so at
rapier's default density of 1.0 each node has a mass near 2000 and every impulse divides by
it. The first test run moved a node 21px toward a target 200px away in 600 steps: the graph
was, in effect, frozen. `MASS_TARGET` in `physics.rs` sets density so mass lands near 20.
If `NODE_HALF_W`/`NODE_HALF_H` ever change, that constant changes with them.

## State at session close, 2026-07-31

### Verified by command

```
cargo test                                    8 passed, 0 failed
cargo run --release -- --check                loaded 90 nodes, 97 edges, 2 contracts
python -m pytest command_center/tests -q      47 passed
python command_center/content_export.py       89 nodes, 58 with a stated reason, 28 terms
python command_center/tags_export.py          90 nodes tagged, flow 7/7 steps resolved
gate.py run --project .                       VERDICT: PASS
```

Gate detail: build, unit, types, security, docs and review all PASS (review at 0 high, 3
medium, 15 low across 4 personas). `pipeline` WAIVED until 2026-09-30 for the pre-existing
reason recorded in `quality-contract.json` (no forge, no `origin` remote). `perf`, `e2e` and
`a11y_ux` are N/A.

The first gate run of the session was **FAIL** on a HIGH: the security persona's
`sql-concat` check matched `command_center/fused_data.js:3281`. False positive with a real
cause, now recorded in `.gitignore`: the content layer embeds document PROSE into the
payload, so a document that merely *describes* a dangerous pattern ships that description
inside a `.js` file where a scanner reads it as code. The three generated payloads are now
ignored, which is the correct fix for a build output rather than a waiver. The hazard class
survives the fix: point any scanner at those files again and it recurs.

### Built this session

- `plan-divergence` skill (`.claude/skills/plan-divergence/`): lock, status, close, report.
  Refuses to close without evidence, refuses `diverged` without a category. Two contracts
  closed against its own construction.
- Five exporters under `command_center/`: `plan_export` (documents), `arch_export`
  (AST to C4), `fused_export` (both, plus reference edges), `content_export` (what / why /
  how plus glossary), `tags_export` (derived tags plus one flow).
- `plan_console.html`: offline-safe browser viewer over the same contract.
- This engine: physics graph, C4 drill-down, tag overlay, flow badges, inspector.

### Known defects, in priority order

1. **The approve path has never executed.** `state/plan_decisions.json` does not exist.
   This is the verb the whole tool was requested for, and it has no evidence in either
   viewer. Fix first, and write the test that fails when the round trip breaks.
2. **Inspector text clips at x~1360** although the rect measures `[1070,30]-[1500,864]`.
   Eight attempts. Five of them targeted sizing, which was never the bug; the sixth found
   the real one (a self-referential rect computed from `ui.max_rect()` every frame) and the
   clipping survived it. Remaining suspect is how `scope_builder(UiBuilder::max_rect(...))`
   positions a child Ui. Read `Ui::new_child` before touching a builder call again.
3. **Tag recolouring and flow badges have never been observed firing.** The data is there
   and the controls render; that is all that is known.
4. **`tags_export.py` has no tests.** Its `risk` tag greps bare identifiers to decide
   whether a test names a module, so any module named with a common word is mislabelled.
   It needs a negative control.

### Not built, from the spec

`sandbox/` ContractLock enforcement, `RevertSandbox`, `gpu/shader.wgsl`,
`views/diff_panel.rs`, `views/timeline.rs`, and the spec's `FailureCategory`,
`NodeStatus`, `premortem_contract`, `diff_data`, `metrics` and `FastSimStep`. Roughly 30%
of the specification, against roughly 75% of what was actually asked for. The reflection at
`docs/reflections/2026-07-31-nexus-plan-graph-and-divergence-skill.md` explains why that gap
runs in that direction and why it was not a neutral choice.

### Exact next action

Run the approve path end to end in both viewers, confirm `state/plan_decisions.json` is
written and read back by `plan_export.py`, and add the failing test. That moves the
request-completion number honestly. Building the WGSL background would only move the spec
number.

### Nothing is committed

Every change from this session is in the working tree of `new-recruit`, plus one line and a
comment in `claude-setup/tools/workspace/Start-Claude.ps1` (adding
`Downloads\new-recruit\projects` as a project root so this repo appears in the startup
picker). Committing needs an explicit decision.
