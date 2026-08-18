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
| 7 | Program design (Rust types for ledger rows, IPC contract, malformed-JSONL handling) reviewed before implementation, per the pre-build design discipline | open | |

## Out of scope

Ledger writes from the UI; replacing the terminal; any server process without
an owner; multi-user.
