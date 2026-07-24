# ADR 0002: Knowledge and capability reach the agent by measured, content-first retrieval

- Status: Accepted
- Date: 2026-07-10
- Deciders: Shoval
- Builds on: ADR 0001 (harness is a Python package with thin bash adapters)

## Context

A 2026-07-10 audit (two adversarially-verified passes over the live hook/config surface
and this package) measured how the codebase repo map and the knowledgebase actually reach
a Claude Code agent, and how skills are selected. The findings:

Retrieval:
- The only live per-turn knowledge retrieval is `router.corpus_docs()`: a SQLite FTS5
  (BM25) match over the `~/docs` corpus that returns up to 3 basenames (filenames), no
  content. The agent must Read the files itself.
- The per-turn intent context pack is computed (`build_context_pack` ranks all prior
  events by `event_score`) and written to a JSON file, but the hook injects only the
  IDs. The one real relevance signal is discarded unread.
- The repo map (`project_map.py`) is a dead scaffold: no subcommand, no hook, reachable
  only by a manual `python -m`. No codebase-structure map reaches the agent automatically.
- The `vector_index`/`vector_search` path is a dead scaffold and is sparse bag-of-words,
  not dense embeddings. There is no dense-embedding, tree-sitter graph, co-change, or
  rerank anywhere in the setup (grep-confirmed).

Skills:
- 100 skills are installed across three loader dirs; the router names 69; 71% have never
  been invoked once across 2311 transcripts; a router nudge converts to an actual Skill
  call ~15% of the time, and usually only for a skill the operator would have run anyway.
- `sessions.db.session_events` has an `event_type='skill_invoke'` slot built for usage
  tracking, and it is empty. No usage telemetry exists today.

Grounding: the July-2026 SOTA reference (`~/docs/Next-Gen AI Coding Intelligence 2026...`)
states embeddings-alone underperform on code; the mature target is hybrid lexical + graph
+ rerank + just-in-time content + subagent isolation, and MCP tool definitions carry a
context cost unless lazy-loaded. The Anthropic emotion-concepts research shows affect-laden
content causally steers a coding agent toward reward-hacking/corner-cutting even without
visible emotional markers.

## Decision

1. The `intent` package is the single source of truth (extends ADR 0001). Retrieval,
   skill selection, the repo map, and the degradation meter are CLI subcommands the hooks
   invoke, not logic embedded in bash.
2. Retrieval surfaces ranked content/snippets, not just filenames, and stops discarding
   the computed context pack. Stay lexical (FTS5 BM25 + sparse cosine) until measured
   insufficiency, then add hybrid/dense behind the same interface. No embeddings-first.
3. The repo map is wired as `intent repo-map` so it is reachable. The tree-sitter/AST
   upgrade (imports, call graph, co-change) is deferred: it is a new dependency and needs
   explicit sign-off.
4. Skill selection becomes usage-measured. Populate `session_events` (`skill_invoke`)
   first, then order router candidates by real invocation counts and drop never-converting
   nudges. Decisions about pruning the dead 71% are driven by that data, not by hand.
5. The sim2real rungs (`reliability` pass^k / PRD T4.3, `calibration` judge kappa / T4.7,
   `trace_diff` / T4.4, `eval_tiers` tier-1 gate / T4.1) are accepted as pure, tested,
   unwired-by-design cores. They are not deleted and not force-wired. Wiring them into the
   live eval pipeline is deferred shared-HOME work, tracked here so the unwired status is
   visible rather than silent.
6. The MCP adapter is deferred until the CLI surface is stable, and will wrap the same
   functions (no reimplementation), lazy-loaded to avoid the tool-definition context tax.

Harness sensors and constraints layered on the above:

7. A live turns/context-degradation meter is added to the control tower, grounded in
   context rot (effectiveness drops past ~100-120k tokens) and intent drift.
8. The low-affect output rule (no emoji, no slop) is a reliability constraint, not a style
   preference: emotion-vector steering causally raises reward-hacking and corner-cutting
   in coding tasks even with no visible emotional markers.

## Consequences

Positive: one implementation, exposed as a portable `intent` CLI (`uv tool install`-able)
and, later, an MCP adapter for cross-agent reuse; the tested hot path stays tested; the
router stops narrating ignored candidates; the computed relevance signal reaches the model
instead of a disk file; the setup can finally answer "which skills and strategies win over
time" from real data; unwired scaffolds are tracked, not silently inflating the test count.

Negative: two entry points (CLI and, later, MCP) to keep in sync, mitigated because MCP
calls the same functions; one telemetry writer to maintain; the turns meter and the
skill-usage logger are new PostToolUse/hook surfaces that need wiring in settings.json
(an explicit, flagged step, not an automatic edit).

## Rejected alternatives

- MCP-first: pays the tool-definition context tax plus a server lifecycle on the hot local
  path and weakens the tests.
- CLI-only forever: loses the cross-agent discoverability the operator wants ("transferable
  if I move it out").
- Embeddings-first: the SOTA reference says dense-alone underperforms on code; lexical is
  the correct floor until measured to fail.
- Status quo: discarded rankings, filename-only corpus, a hand-keyword skill table that
  converts 15% of nudges, and dead-scaffold repo-map/vector paths.
