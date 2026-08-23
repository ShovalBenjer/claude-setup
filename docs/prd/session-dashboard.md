---
tickets: [DASH-1]
---

Status: active

# PRD: Session dashboard (buzz-style workstation surface)

Owner: operator. Opened 2026-08-17 after the spec-discipline review flagged
DASH-1 as the top rework risk: its direction spec pointed at the autonomy PRD,
which does not cover this product. This PRD is the spine; the direction spec
(specs/2026-08-17-session-dashboard-direction.md) records the stack decision.

## What it is

A local desktop app (Tauri + React, decision locked) showing the operator his
Claude estate at a glance: live sessions and agents, gate verdicts, open tasks
per capability module, and the communication surface implementing the Buzz
mode catalogue (reactions, memes, voice notes, approval widgets, code events).

## Why

Terminal reports outpace the operator's reading; state lives across ledgers,
PRs, and sessions with no single glanceable surface, and the operator wants a
UI he enjoys (buzz's look named as the bar).

## Acceptance table

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Reads state/*.jsonl read-only; never writes ledgers | open | |
| 2 | Live view: sessions, agents, last gate verdict per tree | open | |
| 3 | Capability modules with on/off toggles; meme module first (meme-gen + claude-memes via its MCP find_meme/play_meme) | open | |
| 4 | A module with open tasks can open Chrome and kickstart a cloud session; merging/posting stay with the operator | open | |
| 5 | Communication surface routes by the four-register policy in the output-channel-routing rule | open | |
| 6 | Runs on WSL2/WSLg with llvmpipe; libEGL warnings tolerated | open | |
| 7 | Program design (Rust types for ledger rows, IPC contract, malformed-JSONL handling) reviewed before implementation, per the pre-build design discipline | open, see corrective note below | docs/specs/2026-08-17-session-dashboard-direction.md, docs/specs/2026-08-17-session-dashboard-program-design.md |

### Corrective note on row 7 (added 2026-08-19)

STAGED, not closed. A fresh audit on main found 39 dashboard/ source files
already merged (commits 5a61a91..ca055da, "DASH-1 slice 1/2/3" plus follow-up
fixes) while this row still read "open" with no evidence cell. Flipping the
row to "closed" without more would misstate what happened, so this note
records the true state instead.

What is real: two specs exist and are substantive, not placeholders.
`docs/specs/2026-08-17-session-dashboard-direction.md` locks the Tauri + React
stack decision; `docs/specs/2026-08-17-session-dashboard-program-design.md`
names Rust ledger types (tolerant, skip-and-count on malformed/unknown-schema
rows, checked against a key-set scan of all six ledgers), the Tauri IPC
contract, the React component tree, and a five-slice implementation plan.
`dashboard/core`'s 16 unit tests (ledger readers, malformed-input handling,
module-toggle round-trips) are consistent with that design.

What is the actual finding: the design was never gated as a hard blocker
before implementation landed. TODO.md's own DASH-1 program-design row says
"Row 7 ... closes on PR review, not on this file existing" -- and PR review
did happen in the sense GitHub's bot reviewers provide (PR #80, the
program-design spec, and PR #82, DASH-1 slice 2, each got one `kilo-code-bot`
COMMENTED review, 2026-08-18), but no PR review artifact in this repo's own
convention (state/reviews/*.json, produced by tools/review/panel.py) exists
tied to the program-design spec landing, and nothing in
quality-contract.json or ship-gate.yml checked for one before slice 2 and
slice 3 implementation commits merged -- the `review` domain's `panel.py run`
step existed in ship-gate.yml the whole time but nothing gated dashboard/
specifically on a PASS verdict against it. The design work is real, and it did
get a bot's eyes; the review gate the row's own criterion names (this repo's
recorded-artifact convention, not "a bot commented") was not enforced as a
precondition. That gap -- criterion written, oracle never wired -- is the same
shape as EXT-1/EXT-3 and the dashboard test-coverage gap this same audit found
and fixed (quality-contract.json's `unit` and `dashboard` domains, this
commit).

Per calibrated-claims: it is VERIFIED that `kilo-code-bot` reviewed PR #80 and
PR #82 (state COMMENTED, not APPROVED, on both); it is VERIFIED that no
`state/reviews/*.json` artifact is tied to either spec commit and that
quality-contract.json/ship-gate.yml gated nothing dashboard-specific before
2026-08-19; it is ASSUMED (not verified either way) whether the operator did
an informal, unrecorded design review outside both of those channels. Row 7
stays open until either (a) a real review artifact is produced against the
current dashboard/ tree, or (b) the operator accepts the design post-hoc with
that acceptance recorded here, per accepting-architectures (block-by-block,
not a silent flip).

## Out of scope

Ledger writes from the UI; replacing the terminal; any server process without
an owner; multi-user.
