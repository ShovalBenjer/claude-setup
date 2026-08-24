# repo-compare: block/buzz vs claude-setup harness

Date: 2026-08-17. Method: metadata + README + VISION_AGENT.md, no clone (gh api reads only).
VERIFIED = fetched and quoted; ASSUMED = inferred, not directly fetched.

## What buzz is (VERIFIED, README + gh repo view)

Buzz is Block Inc's "hive mind communication platform": a self-hostable Nostr-relay-based
team workspace (Rust backend, Postgres/Redis/S3, Tauri+React desktop client) where humans
and AI agents share the same channels, threads, DMs, canvases, and git events as one signed
event log. Every message, reaction, workflow step, review approval, and git patch is a
signed Nostr event (NIP-01/34/42/98), giving one audit trail regardless of whether the
author is a human keypair or an agent keypair. Agent orchestration runs through two small
Rust crates: `buzz-agent` (an ACP agent, up to 8 concurrent sessions, each with isolated
MCP servers/history/context, self-summarizing on context fill) and `buzz-dev-mcp` (a
minimal MCP server exposing shell + file-edit tools). `buzz-acp` bridges ACP to MCP so
Goose, Codex, and Claude Code can all sit behind the same relay. Apache 2.0, 27.7k stars,
pushed today (2026-08-17), active. VISION_AGENT.md states the design goal directly:
"small enough to hold in your head... run ten agents in parallel behind Buzz."

## Capability overlap

Both systems: (1) treat multi-agent work as first-class, not a bolt-on; (2) demand an
append-only, auditable event/state trail rather than trusting a model's self-report
(buzz: hash-chained Nostr event log via `buzz-audit`; ours: `state/bus.jsonl` hash-chained,
verified by `tools/bus/bus.py verify`); (3) route heterogeneous agent backends (buzz: Goose/
Codex/Claude Code via ACP; ours: Codex/Foundry/OpenAI agents via `dispatch` skill and
`gastown-company-registry.md`); (4) give agents scoped, named identity rather than a shared
God-mode credential (buzz: per-agent Nostr keypair + channel membership; ours: named
personas with bounded tools per `.claude/agents/*.md`).

## What we have that buzz doesn't (ADOPT nothing, just noting our edge)

- A 12-domain verification gate with a stated contract and per-domain oracle+selftest+
  mutation triple (`tools/gate/gate.py`, `quality-contract.json`, `docs/QUALITY-CONTRACT.md`).
  Buzz has `just ci`/`just check` (fmt+clippy+tests) but no equivalent claim-falsification
  layer or mutation-testing requirement (VERIFIED from README's "Common dev commands";
  ASSUMED no mutation testing, not found in README, not exhaustively searched).
- Claim falsifiers (`tools/refute/refute.py`) and a review panel that writes a verdict
  artifact per commit sha (`tools/review/panel.py`), nothing in buzz's README claims an
  automated adversarial-verification layer over agent claims themselves, only over code
  (CI, clippy). ASSUMED absent; not verified by reading source.
- Rules/skills as versioned, diffable payload with a drift checker
  (`tools/audit/skills_sync.py check`), buzz has `.agents`, `.claude`, `.codex`, `.goose`
  directories at repo root (VERIFIED from file listing) suggesting it also treats
  agent-config as tracked payload, but no evidence of a sync/drift oracle between a live
  tree and the repo copy. WATCH: worth a follow-up read of buzz's `.claude`/`.codex` dirs
  to see if they solved the same drift problem differently.

## What buzz has that we lack: adopt / watch / ignore

**ADOPT-candidate: ACP (Agent Client Protocol) as the agent<->tool boundary.**
Buzz's `buzz-agent`/`buzz-dev-mcp` split (ACP for agent<->client, MCP for agent<->tools,
zero coupling between the two protocols) is a cleaner separation than our current pattern
where a persona's tool list is baked into `.claude/agents/*.md` frontmatter per session.
Relevance to the operator's tiny-model-swarm interest: buzz explicitly designs for "ten
agents in parallel... a codebase small enough to fork, modify, and understand in a day,"
which is the same shape as a lead-orchestrator-plus-cheap-worker-swarm. File anchor for
where this would land: `~/.claude/rules/gastown-company-registry.md` (persona routing) and
`~/.claude/rules/hive-mind-workflows.md` (fanout pattern), WATCH rather than ADOPT now,
because ACP is a protocol choice for a *runtime* multi-agent product; this harness is a
single-operator CLI session tree, not a hosted multi-agent server, so the protocol
overhead (stdio JSON-RPC, session lifecycle, MCP server-per-session) has no current host.
Revisit if/when a persistent multi-agent server (not per-session subagents) gets built.

**WATCH: signed-event audit log (Nostr) as the state substrate.**
Buzz's audit trail is cryptographically signed per event (Schnorr, NIP-42/98), stronger
than our hash-chain (`bus.jsonl` chains hashes but events are not individually signed by
distinct agent identities). Relevant to `~/.claude/rules/latent-vector-workflows.md`'s
state-record schema, which already has `agent`/`claim`/`evidence` fields but no signature.
WATCH: adopting per-agent signing would require a keypair-per-persona identity model we
don't have and no current threat model demands (single operator, not multi-tenant). Not
worth the complexity now; worth re-checking if personas ever act as independently
untrusted principals (e.g., third-party agents joining the workflow).

**IGNORE: the workspace/chat/channel product surface itself** (channels, threads, huddles,
canvases, git-hosting backend, desktop app). This is a team collaboration product; nothing
in `AGENTS.md`'s stated scope ("no application here, nothing is served") calls for a chat
product. Out of scope by design.

**IGNORE: Nostr relay/protocol as our transport.** No current need for a multi-relay,
multi-tenant, web-of-trust reputation model; our system is single-operator, single-machine.
Revisit only if this harness ever needs to federate across machines/operators.

## Verdict table

| Item | Verdict | Reason |
|---|---|---|
| ACP-style agent/tool protocol split | WATCH | clean separation, but no current multi-agent server host in this repo |
| Nostr-signed per-agent audit events | WATCH | stronger identity guarantee than our hash-chain; no current multi-principal threat model |
| Chat/workspace product surface | IGNORE | out of AGENTS.md's stated scope (no application here) |
| Nostr relay as transport | IGNORE | single-operator, single-machine; no federation need |
| Mutation-testing / claim-falsifier layer | (we have, they don't, VERIFIED-partial) | our existing edge; no action |

## Gaps in this pass

Did not clone or read buzz's actual Rust source (`crates/buzz-agent`, `crates/buzz-dev-mcp`,
`buzz-audit`), verdict is README/VISION-doc-level, not code-level. Did not check buzz's
`.claude`/`.codex` directories' contents for a skills-sync equivalent (flagged as WATCH
above but unread). If a deeper technical adoption decision is wanted (e.g. actually
prototyping ACP), a follow-up pass should clone and read `crates/buzz-agent/src/`.
