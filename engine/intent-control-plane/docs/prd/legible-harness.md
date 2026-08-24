---
prd: legible-harness
ticket: none (internal platform architecture)
status: active
owner: Shoval
created: 2026-07-12
adr: docs/adr/0004-layered-stack-codebase-memory-herdr.md
---

# PRD: Legible Harness (layered stack adoption)

The control plane for ADR-0004: stop implementing in the dark by adopting a four-layer stack,
knowledge (codebase-memory-mcp) + view (herdr) + learning (intent-control-plane, ours) + behavior
(persona/CLAUDE.md steering). Companion to the intent-control-plane PRD (the brain internals) and the
platform-standard estate PRD. This table is the control plane; update status as work lands, do not
spawn dated notes.

## Goal

Two blindnesses end. Agents are no longer blind to a codebase's wiring (the widgora blind-completion
failure becomes structurally hard, because an agent must consult the graph before editing). The
operator is no longer blind to the running agents (herdr renders live swarm status and allows
take-over). We stop hand-rolling the knowledge layer and keep only our moat, the grade/evolve/route
learning layer.

## Stop condition

codebase-memory is installed pinned+verified and wired project-scoped to intent-control-plane, its
graph answers real architecture/trace queries and its Grep/Glob hook injects context; done_gate reads
the graph's cross-language dead-code instead of the Python-only heuristic; a pre-edit behavior gate
makes agents query the graph for touched files; herdr runs on WSL2 with tower.py rendered as a live
pane and take-over proven; the widgora repo is indexed and the graph provably surfaces the
unwired-widget class. Global promotion of the hook is a separate, later, gated step.

## Acceptance table

Legend: done = verified live; partial = below bar; pending = not started; gated = needs explicit
operator OK (install / corp / global) before it can start.

| #   | Item | Status | Evidence / proof target |
|-----|------|--------|-------------------------|
| P0  | Finish the brain before wrapping it (integrate cycle-1 H5/H10, fix archive.py:137 strict=False fail-open, land the correctness trio #1/#3/#14) | pending | full gate green + done_gate unwired count falls |
| K1  | Pinned+verified install of codebase-memory-mcp v0.9.0 (binary + checksums.txt, manual sha256 verify) | done | sha256 e2832a8d… matched; `codebase-memory-mcp --version` = 0.9.0; in ~/.local/bin |
| K2  | Project-scoped MCP wiring (intent-control-plane/.mcp.json only, not global) | done | `.mcp.json` in-repo points at ~/.local/bin binary; not the global ~/.claude hook |
| K3  | Index intent-control-plane; the graph answers real queries | done | indexed 1200 nodes/4267 edges at 7029dd6; search_graph "advance_pass" -> transitions.py:87-150 + its 3 tests |
| K4  | Grep/Glob PreToolUse hook active + injects graph context | pending | a Grep on an indexed symbol shows `additionalContext` from `search_graph` |
| K5  | done_gate uses the graph's cross-language dead-code (replace Python-only zero-caller heuristic) | pending | RED: a JS/TS unwired symbol the old gate missed; GREEN via graph query |
| K6  | Deprecate the hand-rolled knowledge layer (symbol_graph.py, codebase_map.py) once K3-K5 proven; keep behind a documented fallback seam | pending | modules marked fallback-only in docstring; callers routed to the MCP |
| K7  | Widgora root-cause validation: index widgora, graph surfaces the unwired-widget/unbound-handler class | gated | trace/architecture query on widgora names an unwired component (read-only index) |
| B1  | Persona + CLAUDE.md behavior upgrade (skill-first "query the map before editing", no-narration, memory-as-a-tool, bias-to-action) | pending | the four patterns present in the rule; a spawned agent queries the graph unprompted |
| B2  | Pre-edit graph gate: an agent editing file F must first query codebase-memory for F's callers/impact | pending | RED: a hook/gate test that blocks an edit with no prior graph query; GREEN wire it |
| X1  | Record herdr agent_status transitions into the strategy telemetry (close the observe loop) | pending | a live agent_status_changed event appends a record_dispatch row |
| V1  | Install herdr (mise) + confirm it runs in WSL2 | done | herdr 0.7.3 via mise (checksum + SLSA verified); `mise exec -- herdr --version` = 0.7.3 |
| V2  | Socket-API client (list agents, subscribe to status) | pending | RED: client parses a real `agent.list` reply; GREEN over `~/.config/herdr/herdr.sock` |
| V3  | tower.py rendered as a herdr pane via `plugin.pane.open` | pending | tower panel visible inside herdr, reading real intent.db/telemetry |
| V4  | Live swarm status + strategy cross-tab in the pane (events.subscribe) | pending | pane updates on a real agent state change |
| V5  | Watch + take-over a running workflow agent from herdr | pending | operator types into a live agent's pane and the agent receives it |
| C1  | Playwright completion-smoke gate for UI-touching work (complements the static graph) | pending | RED: a UI task marked done without a browser smoke is blocked; GREEN wire the gate |

## Phase roadmap

- **P0 Finish the brain (prereq, local, ungated).** Integrate cycle-1's two verified patches, fix the
  archive.py:137 `strict=False` fail-open (Codex-flagged), land the correctness trio. Wrap a solid
  brain, not a buggy one.
- **P1 Knowledge pilot (K1-K4, gated on install OK).** Verified pinned install, project-scoped wire,
  index this repo, prove the graph + the Grep/Glob hook. Blast radius = this repo only.
- **P2 Behavior (B1-B2).** Make agents query the graph before editing; fold the system-prompt patterns
  into the personas + CLAUDE.md. This is what converts the tool into the anti-blind-completion habit.
- **P3 Learning connect + deprecate (K5-K6, X1).** done_gate consumes the graph's dead-code; retire
  the hand-rolled knowledge layer behind a fallback seam; observe loop records live agent status.
- **P4 View (V1-V5, gated on install OK).** herdr install + socket client + tower.py pane + live status
  + take-over.
- **P5 Widgora validation (K7, gated corp).** Index widgora read-only; prove the graph catches the
  unwired-component class that caused the original failure.
- **P6 Global promote (gated).** Promote the codebase-memory hook from project-scoped to global
  (~/.claude/.mcp.json) once P1-P4 are proven; commit the team-shared `.codebase-memory/graph.db.zst`
  so parallel sessions + Codex share one graph. Separate, later, explicit OK.

## Execution tasks

Each task: goal, slices (RED before GREEN where code), owner persona, verification (proof), stop
condition. No task is done without pasted command output.

### P0 - Finish the brain

- **T0.1 integrate cycle-1 (H5, H10).** Owner: Engineering Firm + Review Board. Apply the two
  adversarially-confirmed patches (codebase_map parse-error guard; spawn_grade `_main` tests +
  `--archive-path`) to master, run the full gate, commit. Verify: `git apply` clean + full suite green
  + `done_gate` unwired count not increased. Stop: both landed, gate green.
- **T0.2 archive.py:137 fail-open (Codex).** Owner: Engineering Firm. `zip(strict=False)` in
  keep_verdict silently truncates a held-out length mismatch, ignoring an unpaired regressed case.
  Slices: (RED) a keep_verdict test where held_out is longer than held_out_baselines and the extra case
  regressed, asserting "rejected"; (GREEN) `strict=True` (fail loud on mismatch) or explicit
  length-guard. Verify: RED fails pre-fix, green post-fix, full suite green. Stop: the gate cannot be
  fooled by a length mismatch.
- **T0.3 correctness trio (#1 swarm order-dependence, #3 rubric deterministic-disposes, #14
  transitions TOCTOU).** Owner: Engineering Firm + QA Lab. Solo, TDD, one commit each. #14 already has
  a threads+barrier RED test; the fix is a single `BEGIN IMMEDIATE` read-check-insert on one
  connection. Verify: each RED confirmed pre-fix, full suite green. Stop: all three green, done_gate
  clean of them.

### P1 - Knowledge pilot (gated on install OK)

- **T1.1 verified install (K1).** Owner: Security and Compliance Office + MCP and Tooling Office.
  Download the v0.9.0 release binary + `checksums.txt` for linux-x86_64, compute `sha256sum`, assert it
  matches the pinned checksum, place in `~/.local/bin`. Do NOT run the bundled `install` yet (it writes
  the global hook). Verify: pasted sha256 equality + `codebase-memory-mcp --version`. Stop: the pinned
  binary is on PATH, integrity proven, nothing global touched.
- **T1.2 project-scoped wire + index (K2, K3).** Owner: MCP and Tooling Office. Write a project
  `.mcp.json` in intent-control-plane pointing at the binary; `index_repository` this repo. Verify:
  ToolSearch lists the 14 tools; `get_architecture` returns this repo's real layers; `trace_path` on a
  known function (e.g. `advance_pass`) returns its real callers. Stop: the graph answers true queries
  about this repo.
- **T1.3 Grep/Glob hook smoke (K4).** Owner: QA Lab. Enable the `cbm-code-discovery-gate` PreToolUse
  hook project-scoped; run a Grep on an indexed symbol. Verify: the tool result carries
  `additionalContext` sourced from `search_graph`. Stop: the hook provably injects graph context on a
  real search, non-blocking.

### P2 - Behavior

- **T2.1 CLAUDE.md + persona steering (B1).** Owner: Architecture Office. Add a rule: before editing
  a file, query the codebase graph (`get_architecture` / `trace_path`) for its callers and impact;
  do not narrate the query; treat the graph as memory. Verify: the rule present; a fresh spawned agent
  queries the graph unprompted on an edit task. Stop: the four system-prompt patterns are encoded and
  observed once live.
- **T2.2 pre-edit graph gate (B2).** Owner: Security and Compliance Office + Engineering Firm. A
  PreToolUse gate (advisory first) that flags an Edit/Write to a source file with no prior graph query
  this session. Slices: (RED) test the gate flags an unguarded edit and passes a guarded one; (GREEN)
  wire it. Verify: unit test + a real blocked/allowed pair. Stop: the anti-blind-edit gate is live,
  advisory, with an override.

### P3 - Learning connect + deprecate

- **T3.1 done_gate on the graph (K5).** Owner: Engineering Firm. Replace `unwired_public_symbols`'
  Python-only regex zero-caller heuristic with a `search_graph` dead-code query (cross-language, entry-
  point-aware). Slices: (RED) a JS/TS unwired symbol the old gate misses, asserted unwired via the
  graph; (GREEN) route done_gate to the MCP with the old heuristic as fallback. Verify: RED pre-change,
  green after, and the widget-class (frontend) unwired symbol is caught. Stop: done_gate sees frontend
  dead code.
- **T3.2 deprecate the hand-rolled layer (K6).** Owner: Review Board (ponytail). Mark symbol_graph.py
  + codebase_map.py fallback-only in their docstrings; route live callers to the MCP; keep the modules
  + tests as the offline fallback. Verify: `grep` shows no live non-fallback caller; suite green. Stop:
  the hand-rolled knowledge layer is fallback-only, not the primary path.
- **T3.3 observe loop (X1).** Owner: Latent Systems Lab. Subscribe to herdr `pane.agent_status_changed`
  and append a `record_dispatch` row per terminal status (green/red), so live agent outcomes feed the
  strategy bandit. Slices: (RED) a fake event maps to a telemetry row; (GREEN) wire the subscriber.
  Verify: a real status change appends a row; `intent policy table` reflects it. Stop: live agent status
  closes the strategy-measurement loop.

### P4 - View (gated on install OK)

- **T4.1 install herdr (V1).** Owner: MCP and Tooling Office. `mise use -g herdr`; launch `herdr` in the
  WSL2 terminal. Verify: `herdr --version` + a live session with a pane. Stop: herdr runs on WSL2.
- **T4.2 socket client (V2).** Owner: Engineering Firm. A small client over
  `~/.config/herdr/herdr.sock` (newline-delimited JSON): `agent.list`, `events.subscribe`. Slices:
  (RED) parse a recorded `agent.list` reply into typed rows; (GREEN) connect to the live socket.
  Verify: real `agent.list` parsed; a live event received. Stop: we can read + subscribe to herdr state.
- **T4.3 tower.py pane (V3, V4).** Owner: Product Studio. Render tower.py via `plugin.pane.open`
  (split/tab); feed it live status via the subscriber + the strategy cross-tab. Verify: the tower panel
  visible inside herdr, updating on a real agent state change. Stop: the brain has a live face.
- **T4.4 take-over (V5).** Owner: Product Studio. Prove operator take-over: type into a running
  workflow agent's pane and confirm the agent receives it (`pane.send_text`/`send_keys`). Verify: a live
  take-over of a running agent. Stop: watch AND take-over both work, the capability that beats a static
  dashboard.

### P5 - Widgora validation (gated, corp, read-only)

- **T5.1 index widgora + prove the class (K7).** Owner: MCP and Tooling Office + Product Studio.
  Read-only `index_repository` on the widgora repo; run an architecture/trace query that surfaces an
  unwired component or unbound handler. Verify: the graph names a real unwired widget-class symbol that a
  file-by-file agent would miss. Stop: the tool provably catches the original failure class. (No writes
  to widgora; corp OK required to index.)

### P6 - Global promote (gated)

- **T6.1 promote hook to global + share the graph.** Owner: MCP and Tooling Office + Security Office.
  Only after P1-P4 proven and with explicit OK: run `codebase-memory install` to write the global
  `~/.claude/.mcp.json` hook (affects all sessions); commit `.codebase-memory/graph.db.zst` so parallel
  sessions + Codex share one graph. Verify: a second session sees the hook; the artifact re-hydrates
  without reindex. Stop: the knowledge layer is estate-wide, one shared graph.

## Premortem (5 failure modes)

1. The global hook disrupts the 6 live parallel sessions mid-flight. Mitigation: project-scoped pilot
   (P1) first; global (P6) is a separate, later, explicit-OK step.
2. codebase-memory supersedes our modules but we delete them before it is proven, losing the fallback.
   Mitigation: K6 keeps symbol_graph/codebase_map as a documented fallback seam, not deleted.
3. The static graph is trusted for UI completion and misses a rendered-but-unmounted widget.
   Mitigation: C1 keeps the Playwright runtime smoke as a required, complementary gate.
4. herdr's socket API shifts (versioned-but-evolving) and breaks the pane. Mitigation: T4.2 pings the
   protocol version first and handles optional fields gracefully; the pane degrades, not crashes.
5. AGPL exposure if a herdr plugin is distributed. Mitigation: the pane/plugin stays local to the
   operator; nothing herdr-derived is published.

## References

ADR-0004 (`docs/adr/0004-layered-stack-codebase-memory-herdr.md`), the substrate/view spec
(`docs/specs/2026-07-11-substrate-view-mosaic-temporal.md`), the coding-style standard
(`docs/specs/2026-07-12-coding-style-standard.md`), the implementation audit
(`docs/analysis/2026-07-12-implementation-audit.md`), the intent-control-plane PRD, the estate
platform-standard PRD (`~/docs/prd/2026-07-10-platform-standard.md`). External: DeusData/codebase-
memory-mcp v0.9.0 (MIT, arXiv:2603.27277), ogulcancelik/herdr v0.7.3 (AGPL-3.0), the Anthropic
claude-sonnet-5 / claude-fable-5 system-prompt references.
