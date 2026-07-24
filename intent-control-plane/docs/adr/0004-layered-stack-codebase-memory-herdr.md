# ADR-0004: Adopt a layered stack, codebase-memory (knowledge) + herdr (view) + intent-control-plane (learning)

Status: proposed (pending operator ratification + the install OK)
Date: 2026-07-12
Deciders: Shoval (deferred the call), lead

## Context

"We keep implementing in the dark" (operator, 2026-07-12). The darkness is two distinct
blindnesses: agents are blind to a codebase's wiring (the widgora failure, commits shipped with
widgets unwired, is the canonical case), and the operator is blind to the running agents (no way
to watch or take over the swarm). This session hand-rolled a thin knowledge layer to attack the
first (symbol_graph.py tree-sitter, codebase_map.py per-file/function, done_gate zero-caller). The
operator then surfaced three external artifacts: DeusData/codebase-memory-mcp, ogulcancelik/herdr,
and the Anthropic system-prompt leaks.

Verified (read-only, 2026-07-12):
- codebase-memory-mcp: 30.1k stars, v0.9.0, MIT, arXiv:2603.27277, single static C binary, zero
  runtime deps, Linux x86_64 (WSL2 = x86_64, ok). Supply chain: SHA-256 checksums + SLSA-3
  provenance + Sigstore cosign + VirusTotal per release; installer verifies sha256 before install,
  no sudo, writes ~/.local/bin + ~/.claude/.mcp.json + a non-blocking PreToolUse Grep/Glob hook
  (cbm-code-discovery-gate) that injects graph context. 14 MCP tools (index_repository, search_graph,
  trace_path, query_graph, get_architecture, detect_changes...). It is a production superset of our
  hand-rolled knowledge layer.
- herdr: 15.5k stars, v0.7.3, AGPL-3.0+, one Rust binary (no electron), mise-installable. Socket API
  (unix socket, newline-delimited JSON, versioned): agent.list/get + pane.get expose agent_status;
  events.subscribe on pane.agent_status_changed; plugin.pane.open (overlay/split/tab/zoomed) renders
  an external executable INTO a pane. That is enough to run our tower.py view as a herdr pane and to
  read/subscribe to live swarm status.

## Decision

Four best-of-breed layers; build only what is uniquely ours.

1. Knowledge (agents not blind to code): ADOPT codebase-memory-mcp. Stop deepening symbol_graph.py /
   codebase_map.py; keep them only as fallback until codebase-memory is wired and proven. Its
   Grep/Glob hook is the root-cause fix for the widgora-style blind-completion failure.
2. View (operator not blind to agents): ADOPT herdr as the multiplexer; render tower.py as a herdr
   pane via plugin.pane.open and feed it live status via events.subscribe. NOT a standalone tower,
   NOT a new Rust TUI. Decided from the socket-API evidence, not effort estimates.
3. Learning (which agent/strategy/persona wins, graded over time): KEEP intent-control-plane. This is
   the one thing neither codebase-memory nor herdr does; it is our moat.
4. Behavior (how agents are steered): fold the system-prompt patterns (skill-first "load the codebase
   map before editing", no-narration, memory-as-a-tool, bias-to-action) into the personas + CLAUDE.md.

## Consequences

- Positive: the knowledge layer stops being hand-rolled and becomes SOTA + shared across all sessions
  and Codex; the view becomes real (watch + takeover) on Linux (herdr clears the macOS-only Mosaic
  blocker); we only maintain the learning layer.
- Cost / risk: two third-party deps. codebase-memory writes a GLOBAL PreToolUse hook affecting every
  live session, so it is piloted PROJECT-SCOPED (intent-control-plane/.mcp.json) first, then promoted
  to global only once proven, protecting the operator's concurrent sessions. herdr is AGPL: fine for
  local operator use; a distributed herdr plugin would attach AGPL obligations (kept local).
- Static graph still cannot see a rendered-but-unmounted React widget or an unbound scroll handler,
  so the Playwright runtime completion-smoke for UI work stands alongside the graph, not replaced.
- Gated action: the actual install (download + wire) is the one step held for explicit operator OK,
  done as a pinned v0.9.0 + manual sha256 verify, never a curl|bash on faith.
