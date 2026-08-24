---
PRD: prd/claude-os.md
Ticket: EXT-8
Status: active
---

# ecosystem.db graph half: FalkorDB + Graphiti (2026-08-24)

Operator decision, 2026-08-24: build the graph-shaped half of the state
plane on FalkorDB + Graphiti, not SQLite bitemporal columns, not Dolt,
not raw Neo4j. Filed here after a session-continuity gap: the branch
this decision was first reasoned on (`rules-sync-repo-stack-reasoning`)
was deleted mid-session before the file could land, and the decision
survived only in a side vault
(`claude-setup-vault/directions/ecosystem-db-falkordb-graphiti.md`)
until this write. Recorded as its own finding, not smoothed over: a
decision that depends on a side channel to survive a worktree loss is
exactly the "sessions with my requests forgotten" failure mode this
was raised against.

## Why, and why this does not repeat the unbuilt-PRD pattern

`docs/prd/2026-08-03-unified-architecture.md` already proposed plain
SQLite with `valid_from`/`valid_to` columns for `ecosystem.db`, sized
against a 16,644-row estate. That reasoning still holds for pure
operational tables (sessions, proposals, runs, post_queue): this spec
does not touch those. It does not hold for the two features
`docs/prd/claude-os.md` already names as graph-shaped: the repo
portfolio graph (row 15) and blast-radius graph (row 16). Real graph
traversal (imports, call edges, repo relationships) plus real temporal
bounds is what those need; a relational table simulates both poorly.

Checked directly, not assumed:

- FalkorDB: real graph database (GraphBLAS/Rust), ~5,600 stars at
  check time, active within 24h. Confirmed as Graphiti's supported
  backend.
- Graphiti (github.com/getzep/graphiti): real temporal knowledge-graph
  library, MCP server exists, entity/event extraction, incremental
  updates without full recompute.
- This repo's own `docs/books/` corpus already describes the same
  pattern independently: `graph_rag_3.txt` and three sibling files
  (FTS5-indexed, `/home/shov/.claude/corpus/books.sqlite3`) describe
  entity graphs with temporal bounds as edge properties and hybrid
  vector+fulltext+temporal+graph retrieval. Found by a real query
  against material already on disk, not invented for this decision.
- `agent_memory_1.txt` (same corpus, O'Reilly early-release on agent
  memory systems) supplies the design constraint this spec adopts
  below: "we do not simply upload every slice of personal or
  organizational information to a memory database... effective memory
  is retained in an intentional manner." Its worked example (an agent
  with curated org memory, RCA records, standing rules, fixes a bug
  correctly; the same agent blank-slate ships a costly regression) is
  the argument against dumping every `state/*.jsonl` row into the
  graph unfiltered.

## Scope: one finishable slice, not a wholesale redesign

Per the standing complaint this decision responds to (forgotten
requests, stale `.md` files piling up, "what will actually matter and
not grade down"), this is one verifiable slice:

1. Stand up FalkorDB locally (Docker, per Graphiti's own README).
2. Wire the Graphiti MCP server against it.
3. Load one real graph: the repo portfolio (`claude-setup` plus
   siblings, `new-recruit`, `daily-deep-learning`, `verdict-bench`,
   `claude-setup-vault`) as nodes and edges (`repo`, `depends-on`,
   `references`). This is `docs/prd/claude-os.md` row 15, already
   named, still TODO; this slice does not invent new scope, it builds
   what was already committed to paper.
4. Apply the curation constraint from `agent_memory_1.txt`/`agent_memory_2.txt`
   (same book, ch.2, read in full 2026-08-24), not a vague "curate
   somehow" but the book's own worked shape:
   - Ingestion (a `MemoryConnector` contract: `list_records`, `search`,
     `fetch`, each source yielding a common `RawRecord`) stays separate
     from admission. Every reachable `state/*.jsonl` row and repo file
     can be listed; not all of them belong in the graph.
   - Normalize what's admitted into a richer record carrying domain,
     owner, kind, authority, and `updated_at`, the fields an agent
     needs to judge trust, not just match keywords on.
   - Write the admission rule as a small, human-owned config (the
     book's `methodology.yaml` pattern: owned domains, max age,
     require-timestamp), enforced by a `screen()` function that returns
     an admit/reject decision with a named reason per record. This
     repo already has the domain vocabulary for "owned" (the charters
     in `docs/charters.md`, lane A/B/C/D) to seed that config from,
     rather than inventing one.
   - Do not let ingestion default to "load everything": that is the
     exact failure mode the book's worked example measures (15 records
     ingested, 5 rejected by the methodology as stale/out-of-domain,
     with the reason stated for each).
5. Prove one real temporal query: what the dependency graph looked
   like before PR #89's IPC fix landed, or an equivalent before/after
   pair, since temporal traversal is the reason to choose Graphiti
   over a plain graph at all.
6. Acceptance: one MCP query returns real graph data, the same
   definition-of-done pattern as the unified-architecture PRD: a
   command that exits zero and produces a named artifact, not a claim.

Explicitly out of this slice: the rest of `ecosystem.db` (sessions,
proposals, reputation tables) stays on the existing SQLite plan.
FalkorDB does not creep into replacing tables that were never
graph-shaped.

## What would falsify this choice

If, after building the repo-portfolio-graph slice, no query benefits
from graph traversal over what a plain SQLite JOIN would answer just
as well, this was the wrong tool: the slice should then be the last
graph work attempted here, not upgraded further. Named per this repo's
own falsifier discipline, not assumed correct because it sounds more
advanced.

## Related

`docs/prd/claude-os.md` (rows 15, 16), `docs/prd/2026-08-03-unified-architecture.md`
(the SQLite baseline this spec narrows, not replaces), TODO.md EXT-7
(a separate, still-open operator decision on gate-run hash-chaining,
not this spec's scope).
