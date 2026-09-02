# Interaction visualization and agent-harness gap research

Date: 2026-09-02. Lane A. Trigger: the owner supervises about five parallel Claude Code projects from the mobile stream view and reports cognitive overload; the linear chat transcript (prose paragraphs plus "Used a tool, edited 2 files" rows) does not support fleet supervision. Two questions were asked: how should this interaction be presented (with research backing, plus two build options: a kitty TUI and a GUI on an existing repo), and what is this harness missing relative to pi and comparable agent harnesses.

Method: four parallel research passes (HCI and agent-oversight literature; the multi-session tool landscape including kitty and the "buzz" repo; pi and comparable harnesses; an inventory of this repo). Sources were fetched, not recalled. Sibling docs: `2026-08-17-external-landscape-comparison.md`, `2026-08-12-claude-code-repo-gap.md`.

## 1. The core reframe from the literature

Supervising five coding agents is a supervisory control problem, not a conversation problem. The relevant body of work is the one-human-many-robots literature, not chat UX.

Key results, each with a direct design consequence:

- Fan-out. Olsen and Wood (CHI 2004) and Olsen and Goodrich (PERMIS 2003): the number of agents one person can run is roughly Neglect Time / Interaction Time + 1. The UI's job is to minimize Interaction Time, the seconds spent re-acquiring context and issuing a correction. That, not screen count, caps fleet size.
- Wait time. Crandall and Cummings (IEEE Trans. Robotics 2007): as agent count grows, the binding cost shifts from operator overload to agents idling blocked on the human. The UI should therefore show the service queue explicitly ("waiting on you: 2, oldest 8m").
- Operator capacity. Cummings et al. (2007, UAV supervisory control): practical bounds of 2 to 4 for low-autonomy vehicles, up to 12 when the human handles only mission-level decisions. Five agents is feasible exactly when servicing each one is a decision (approve, redirect) rather than a read-the-transcript task.
- Situation awareness. Endsley (Human Factors 1995): perception, comprehension, projection. A transcript delivers only level 1, in the most expensive encoding (prose). Displays should present computed level 2 and 3 judgments directly: on-track, drifting, blocked, will-need-you-in-N-minutes.
- Interruption cost. Iqbal and Horvitz (CHI 2007, 2008): deferring notifications to the human's own task boundaries measurably cuts resumption lag and errors. Only a blocked agent should interrupt; progress updates belong in a board polled at the supervisor's own breakpoints.
- Calm technology. Weiser and Brown (1996), Pousman and Stasko (AVI 2006): routine progress belongs in the periphery, pre-attentively readable (color, position), escalating to the center of attention only on exception.

Recent agent-specific work confirms the transfer:

- AgentGUI (arXiv:2607.26300, 2026): a GUI for multiple concurrent long-running agent sessions. Controlled study: users found critical information 38 percent faster with structured trajectory views than with transcript reading; automated drift-detection steering raised completion by up to 34 points.
- Overseeing Agents Without Constant Oversight (Microsoft Research, arXiv:2602.16844, 2026): redesigned traces cut time-to-find-errors but did not improve accuracy. Presentation speeds review; calibration requires ground truth (tests, diffs), not nicer prose.
- Human Oversight of Agentic Systems in Practice (arXiv:2606.05391, 2026): developers oversee in four modes (a-priori control, co-planning, live monitoring, post-hoc review) and in practice use test results, not agent prose, as their correctness proxy.
- MAST failure taxonomy (arXiv:2503.13657, ICML 2025): a top failure cluster is task verification failure, agents claiming done without proof. A supervision surface must render claimed state visually weaker than verified state. This is the same thesis as this repo's gate: enforcement over prose (ADR-0005), now with external evidence.
- Professional developers "don't vibe, they control" (arXiv:2512.14012, 2025): field study; professionals plan first, scope tightly, and spend their interaction time on review. The diff, not the transcript, is where supervision time goes.

## 2. Industry convergence

LangSmith, Langfuse, Braintrust, Arize Phoenix, AgentOps, Helicone, and Datadog LLM Observability have converged on the same primitives: a trace tree as the canonical unit, a span waterfall with per-span latency, tokens, and cost, a run-status board filterable by outcome, always-visible cost meters, eval scores attached to spans, and a dual view (execution graph plus flat log) because neither alone suffices for loopy agents. OpenTelemetry GenAI semantic conventions (invoke_agent, execute_tool, inference spans) are the emerging standard schema underneath.

GitHub Agent HQ ("mission control", Oct 2025) is the clearest product statement for coding agents specifically: one board across a fleet (Claude, Codex, Devin), per-session progress, mid-run steering, and the PR (diff plus CI status) as the terminal artifact rather than the transcript.

From SRE practice (Google SRE book): pages must be rare and actionable, alert on symptoms not causes, three severity tiers with only the top tier interrupting.

## 3. Design principles for a five-agent mission control

Ranked, each traceable to sources above:

1. Status first, prose last. Top level is at most five cards, each dominated by a computed state badge from a small explicit state machine: working, needs-input, awaiting-review, blocked, failed, done-verified. Prose is the deepest drill-down.
2. Optimize time-to-service. Each needs-input card carries one line: what the agent needs and why. Every second saved raises fan-out.
3. Interrupt only at page tier. Blocked or permission-needed interrupts; everything else batches to the supervisor's breakpoints.
4. Verified state over claimed state. Agent self-reports render weaker than tests green, gate PASS, diff reviewed. The gate verdict is exactly the signal to surface.
5. Diff plus timeline as primary artifacts; transcript as provenance only.
6. Show the wait queue as a first-class number.
7. One glance equals fleet health, pre-attentively (color and position, no reading).
8. Progressive disclosure in fixed strata: badge, one-line status, timeline and diff, full transcript.
9. Detect and badge drift and loops automatically (repeated tool calls, spec deviation) rather than expecting the human to notice them in prose.
10. Support all four oversight modes, not just live watching.
11. Always-on cost and token meters per session and fleet-wide; runaway loops appear here first.
12. Emit OTel GenAI shaped events underneath so any UI is a lens over standard data, matching this repo's "dashboard owns nothing" rule.

The screenshot that triggered this doc violates principles 1, 3, 5, 7, and 8 simultaneously: it is a single stratum (prose) at uniform salience with no state machine, no queue, and no verified-state signal.

## 4. Build option A: a custom kitty TUI

kitty offers four capabilities that make a custom monitor genuinely better than tmux-based art:

- Remote control (`kitty @` over a unix socket): launch tabs (`launch --type=tab --cwd`), list all windows with foreground processes as JSON (`ls`), drive a session without attaching (`send-text`), jump to a session (`focus-window --match`), and color tabs (`set-tab-color`), which turns the tab bar itself into the glanceable fleet strip.
- Panel kitten: a dock at the screen edge for a persistent status strip.
- Watchers: Python callbacks on window lifecycle events, free session signals.
- Kittens and the graphics protocol for overlays and inline images.

Data sources from Claude Code, in order of reliability:

1. Hooks (Stop, Notification, PreToolUse, PostToolUse, SessionStart, SessionEnd, SubagentStop): a five-line hook POSTing `{session_id, cwd, event}` to a unix socket gives push-based exact state. Every surveyed TUI instead scrapes tmux panes heuristically; hooks are the differentiator nobody uses.
2. Statusline JSON (model, cwd, context percent, cost) as a per-session heartbeat. This repo already has the receiver written: `dot-claude/statusline.py` tees exactly this payload to `state/sessions/<id>.json` as the declared FleetView substrate. It is not wired (no statusLine key in `dot-claude/settings.json`) and `state/sessions/` does not exist. Wiring it is the single highest-leverage move in this doc.
3. Transcript JSONL tailing (`~/.claude/projects/*/*.jsonl`) for the drill-down stratum; schema is unversioned, so treat as best-effort.
4. OTel export for history and cost charts, not for the live loop.

Stack: Textual (Python). Rationale: async tailing of N files plus a socket is its home ground, it shares a language with kittens, watchers, and the existing `statusline.py` and `tools/dashboard/serve.py`, and performance is a non-issue at 5 to 20 sessions. Ratatui and Bubble Tea are viable; Bubble Tea only matters if forking claude-squad wholesale.

Existing TUIs to borrow from rather than fork: claude-squad (8.4k stars, Go, tmux plus worktree per session, live preview pane, diff tab) has the best session-plumbing design; ccmanager (1.2k stars, TypeScript, tmux-free child PTYs, status badges with notification hooks) proves the no-tmux route. Both detect state by output parsing, which hooks obsolete.

Shape of the build (small, roughly a week of sessions): a `fleetview` daemon owning the socket and `state/sessions/`, a Textual board (five cards, state badges, wait queue, cost strip), and a thin `kitty @` adapter for focus, launch, and tab coloring. The existing SSE dashboard (`tools/dashboard/serve.py`) stays as the browser lens over the same files; the Rust Tauri `dashboard/` (one implemented reader, five stubs) should be treated as parked rather than a third live surface.

## 5. Build option B: a GUI on the buzz repo

"Buzz" resolves to block/buzz (Block's platform, launched 2026-07-21, about 32k stars, Apache-2.0): a self-hostable Nostr-based workspace where humans and agents share channels, Slack-shaped with agents as cryptographically identified members. Rust/Axum backend, Tauri desktop and web UI, Flutter mobile in progress. Agents connect via `buzz-cli` (JSON in and out) or `buzz-acp`, which is compatible with Claude Code, Codex, and goose. Agent messages, patches, reviews, and CI results land in channels with attribution. (The other famous buzz, chidiwilliams/buzz, is Whisper transcription and unrelated.)

Assessment: buzz gives mobile plus desktop reach and a place where agent output is already event-shaped, and this repo's bus (`tools/bus/bus.py`, addressable lanes, exactly-once inbox) maps naturally onto buzz channels, one channel per lane. But buzz is chat-shaped, exactly the presentation this research argues against for fleet state, and adopting it means adopting a whole workspace platform (Postgres, Redis, MinIO) to get a monitor. Verdict: worth a spike as the remote and mobile tier (a bridge that mirrors `state/bus.jsonl` and session state into a buzz channel would be under 200 lines), not as the primary supervision surface.

Stronger GUI alternatives for the actual use case, if a GUI is wanted before the TUI exists: vibe-kanban (28k stars, board-shaped, worktree per card, in-app diff review; risk: parent company shut down 2026-04, community-maintained), happy (23.6k stars, active, end-to-end encrypted mobile and web client for Claude Code with push on permission requests; directly fixes the mobile pain in the screenshot today by wrapping `claude` in `happy`), opcode (22k stars, Tauri GUI over `~/.claude` with cost analytics; maintenance slowing). Crystal is deprecated, terragon is dead, conductor is closed macOS-only.

## 6. Harness gap analysis: pi and peers versus this repo

pi is Mario Zechner's coding agent (badlogic/pi-mono, moved 2026-04 to earendil-works/pi, about 45k stars). Philosophy: a system prompt under 1,000 tokens, four core tools, no MCP (CLI tools with READMEs read on demand), no built-in todos, plan mode, subagent tool, or permission prompts (container sandboxing instead), and everything else as TypeScript extensions with the richest event API in the field (blockable tool_call, mutable provider payloads, custom renderers, overridable compaction). Its standout capability: sessions are append-only JSONL trees with `parentId` on every entry, navigated and forked in place (`/tree`, `/fork`). Its stated product is context observability: every request inspectable, a documented session format, alternate UIs buildable on the core.

Peers in one line each: opencode (client-server split, one server driving TUI, desktop, and IDE clients), Amp (team-shared threads plus an Oracle reviewer model), goose (everything is MCP, shareable declarative recipes), aider (auto-commit per edit and the field's only built-in lint-and-test feedback loop), Codex CLI (orthogonal OS-sandbox by approval-policy matrix), Claude Code (richest hook set, checkpoints and rewind, Agent SDK).

What this repo has that none of them ship: a multi-domain quality contract with UNCOVERED-fails semantics, oracle selftests plus mutation testing of the selftests, a hash-chained event bus, claims and lessons ledgers with falsifiers, and review artifacts keyed by sha. The market's verification answer is sandboxing or human approval, not adversarial self-checking. That is the moat; nothing below suggests trading it.

What this repo is missing, ranked by leverage:

1. Live session observability, the subject of this doc. The substrate exists unwired: `statusline.py` not registered, `state/sessions/` absent, the SSE dashboard manual-start with no systemd unit, the Tauri dashboard five-sixths stubs. pi treats observability as the product; here it is the least finished layer. Fix order: wire statusline, add a Stop/Notification hook feeding the same `state/sessions/` files, put a systemd unit on `tools/dashboard/serve.py`, then build FleetView per section 4.
2. Cost and token telemetry. No ledger under `state/` carries tokens or dollars; no cost domain in the 32-domain contract. Every surveyed harness shows per-session cost in its footer. The statusline payload already contains `total_cost_usd`; wiring item 1 captures it for free, then a small `state/cost.jsonl` rollup and a budget check can join the contract.
3. Orchestration control. The bus can address lanes but nothing spawns, supervises, cancels, or reassigns a session; `spawn_log.py` records after the fact. claude-squad and vibe-kanban both demonstrate worktree-per-task spawn and reap; FleetView should own the spawn and cancel verbs, not only the view.
4. Session branching and checkpointing of conversations. Snapshots here version files, not dialogue. pi's in-file session tree and Claude Code's fork-on-resume both do this natively; at minimum, record enough in `state/sessions/` to resume or fork a lane's session by id.
5. Interception-grade hooks. This repo's hooks observe and gate at the Claude Code event surface, but nothing can mutate a tool input or block with a reason the way pi's `tool_call` event or opencode plugins can. Not urgent; hookgate covers the dangerous subset for Bash.
6. A documented session format of our own. pi's critique of Claude Code (undocumented, shifting JSONL) applies to anything FleetView builds on transcripts. Keeping `state/sessions/` as the stable, owned schema and treating transcript JSONL as best-effort input honors disk-is-memory (ADR-0010).

## 7. Recommendations

1. Wire `statusline.py` now (one settings.json key plus deploy), creating `state/sessions/`. Smallest change, unlocks items 1 and 2 above and the mobile pain partially (cost and context visible per session).
2. Add a fleet-state hook: Stop and Notification events append state transitions to `state/sessions/<id>.json`. With 1, this is the complete FleetView data plane.
3. Build FleetView v0 as a Textual TUI over `state/sessions/` with a `kitty @` adapter, per section 4. Board of cards, wait queue, cost strip, tab coloring. Claim it as Lane A work; the charter already names FleetView.
4. Trial happy today for the phone-side pain, unmodified, while the TUI does not exist yet.
5. Spike a buzz bridge (bus lanes to buzz channels) only after 1 to 3, as the remote tier.
6. Add a cost rollup and contract domain once `state/sessions/` has data.
7. Defer the Tauri dashboard; two surfaces (TUI plus SSE web lens) over one data plane beat three half-built ones.

Falsifier for this doc's central claim: if wiring statusline plus hooks and building the section 4 board does not reduce the owner's reported time-to-service a blocked session versus the mobile stream, the supervisory-control framing is wrong for this fleet size and the chat surface should be improved instead.
