# ADR-0010 — Sessions are ephemeral; disk is the only memory

Date: 2026-07-24. Status: accepted.

## Context

Observed same-day: auto-compact "continue" loses working state; a fresh-compacted
session already showed 64% context; 3 parallel sessions each carry unshared context;
phone RC spawns orphan sessions. Any design that keeps truth in a conversation is
already broken — conversations compact, die, and diverge.

## Decision

No load-bearing state lives only in a conversation. Every decision, claim, run, and
work item lands on disk (docs/, state/, ecosystem.db) or in GitHub (PR, issue,
commit) BEFORE it counts as done. Sessions are cattle: any session must reach full
working context from disk in under 60 seconds (docs/SESSION-BOOT.md), and killing
any session must cost zero decisions. PreCompact hook snapshots git state and
reminds the summarizer of the handoff schema; but the hook is a seatbelt, not the
design — the design is that compaction has nothing exclusive to lose.

## Consequences

- Every tool/loop writes its output to a file or DB as its LAST step, not to chat.
- Cross-session coordination happens through ecosystem.db work-claims, never through
  "the other session knows".
- Costs a little friction (write-through everywhere); buys immunity to compact loss,
  session death, and RC orphaning — the three pains observed today.
