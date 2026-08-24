# Handoff: block/buzz is the buzz, adopt and customize (operator directive)

Operator, 2026-08-13: "the html you wrote is miles away from a polished
https://github.com/block/buzz which i want a better version customized, but we
need to start from this level." Every earlier "buzz" reading as "notifications"
was wrong; buzz is this repo.

Facts (gh, 2026-08-13): Apache-2.0, Rust, 26,716 stars, pushed 2026-08-12.
Self-hostable workspace, humans + agents in shared rooms, all events (messages,
reactions, workflow steps, reviews, git events) signed entries in one Nostr relay
log. Docs: VISION.md, ARCHITECTURE.md, VISION_AGENT.md in-repo.

Why it fits this estate: the peer sessions already talk over a UDS socket bus and
hash-chained state/bus.jsonl; buzz is that pattern productized with a polished UI.
Apache-2.0 permits fork/customize (unlike command-center's non-commercial block).
Rust aligns with the 2026-08-13 stdlib demotion in repo-stack-reasoning.md.

Next session, claim lane A, in order:
1. Self-host buzz locally (Rust build or released binary), reach the UI.
2. Wire one Claude session in as an agent (VISION_AGENT.md is the contract).
3. Map our bus/state ledgers onto its event log; decide bridge vs replace.
4. Customize from there ("a better version customized"): operator directs taste.
5. Session Lens (tools/dashboard) becomes a stopgap; retire or embed later.

The stdlib Session Lens stays as baseline comparison only. Do not extend it.
