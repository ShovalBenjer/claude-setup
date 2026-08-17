---
PRD: prd/autonomy-ecosystem.md
Ticket: DASH-1
Status: active
---

# Session dashboard: direction locked, Tauri + React (2026-08-17)

Operator pick, 2026-08-17, after a /diverge pass (four candidates with stated
conventionality) and a practitioner-sentiment check weighted toward cynical
signal (HN, GitHub issues, the OpenCode Tauri-to-Electron migration writeup;
Reddit itself was unreachable from the sandbox and is flagged as a coverage gap).

## The decision

A personal session dashboard reading local `state/*.jsonl` ledgers (tasks,
agents, gate verdicts), built as a Tauri desktop app: Rust core, React front.

## Why this candidate won

- The operator's stated tension was Rust-level performance against a striking
  custom UI in the block/buzz style. Buzz itself is Rust backend plus web front,
  so the tension dissolves in this stack, and the buzz clone is the live design
  reference (Apache 2.0).
- Ratatui structurally caps the visual ceiling (terminal cells, no true
  graphics), failing the aesthetic requirement outright.
- Dioxus carries an open, reproducible WSL2 desktop SIGSEGV (dioxus issue 3354)
  plus a continuously-paid ecosystem-immaturity tax; a worse WSL2 risk than
  Tauri's cosmetic libEGL/llvmpipe warnings, which match this machine's known
  software-rendering baseline.
- The named Tauri regret case (OpenCode migrating back to Electron) was about
  WebKit rendering fidelity for a large chat UI plus a Node-native server;
  neither transfers to a small local JSONL dashboard.

## Constraints the build inherits

- WSL2/WSLg, Intel GPU, llvmpipe software rendering: expect libEGL warnings,
  treat them as noise, never as a bug to chase.
- Reads ledgers only; no writes to `state/` from the UI.
- New component over 300 lines owes `docs/prior-art/<name>.json` before the gate
  passes; the design anchor is the buzz UI, named in the artifact per the
  out-of-distribution rule.
- Build starts in its own worktree and PR, not on the rules-sync branch.

## Requirements added by the operator, 2026-08-17 (after the direction lock)

- Capability modules with per-module on/off toggles; the meme surface is the
  first named module and it is TWO capabilities: the meme-gen skill
  (browser-driven Gemini/ChatGPT creation, tested live this date) and the
  operator's own ShovalBenjer/claude-memes-skills (Rust binary, Giphy GIFs
  inline in the terminal, 22 curated events plus embedding-matched auto mode).
  The integration seam for the dashboard is the latter's MCP mode
  (`claude-memes mcp`, tools find_meme and play_meme over stdio); the UI calls
  those rather than reimplementing selection.
- A module showing open tasks can act: open Chrome and kickstart a cloud
  session (claude.ai/code) to work them. Outward actions from the dashboard
  inherit the-loop-may-act boundaries; kicking a session is allowed, merging
  and posting stay with the operator.
- The communication surface implements the operator's Buzz mode catalogue
  (recorded in dot-claude/rules/output-channel-routing.md, from his Gemini
  research chat of this date): emoji-reaction acks, stickers/memes for social
  register, inline diagrams and annotated screenshots, voice notes/TTS
  briefings, interactive approval widgets, and code-native event rendering,
  routed by the high-signal / social / deep-engineering / urgent policy.
