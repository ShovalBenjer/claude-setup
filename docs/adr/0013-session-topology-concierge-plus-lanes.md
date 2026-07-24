# ADR-0013 — Session topology: one concierge + three chartered lanes

Date: 2026-07-24. Status: accepted.

## Context

Three parallel sessions converge (same phrasing, overlapping work) and phone RC
spawns a fresh orphan session per connection, so "speaking to the computer" reaches
a context-free stranger. Convergence across sessions is the same measured mode-
collapse failure /diverge fights within one session.

## Decision

Four named lanes, chartered in docs/charters.md: **A concierge** (phone-facing:
listen, capture intent to ecosystem.db, route, notify — never implements),
**B claude-setup** (harness, this repo), **C resume engine** (new-recruit),
**D learning** (הסדנה). Rules: a session opens by naming its lane; a lane only
implements inside its charter; cross-lane needs go through ecosystem.db proposals
(work-claims), never through doing the other lane's work. Phone RC is treated as
always reaching lane A: the concierge session is kept durable (relaunched by
scheduler if dead), and its charter is intake-and-route only, so a fresh spawn
loses nothing (ADR-0010 makes intake stateless — it writes to db and pushes).

## Consequences

- Convergence broken structurally: lanes read different queues, own different repos.
- RC "not working properly" becomes survivable: worst case a fresh concierge still
  captures intent to disk and routes; no context needed to do intake.
- Costs discipline (charter check at session start — enforced by session-recall hook
  surfacing charters.md); buys parallelism without duplication.
