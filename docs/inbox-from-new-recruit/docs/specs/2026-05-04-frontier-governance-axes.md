# Frontier-grade AI governance — 4-axis audit + proposed enhancements

**Date:** 2026-05-04 (late evening IL, into 2026-05-05)
**Source:** Conversation around AI21 system-requirements article (article was methodology-not-framework — answered the underlying question independently). Plus user's frontier-stuff message about mechanistic interpretability as 2026's biggest shift (sparse autoencoders, internal-circuit alignment).
**Status:** Reference document. P1 items are recommended next-session work.

---

## Frame

Top labs in 2026 (Anthropic, OpenAI, DeepMind) operationalize agent governance along 4 axes:

1. **Pre-action** — checks before the model takes any externally-visible action
2. **Evidence** — what the model must produce to substantiate claims
3. **Approval** — which actions require human gates
4. **Log** — what gets recorded for post-hoc audit

Mechanistic interpretability adds a 5th axis (internal-circuit monitoring) but it requires open-weight model access — out-of-reach for closed-API setups using Claude / GPT-5.5 / etc.

For a closed-API setup like this one, the realistic ceiling is **behavioral interpretability via captured reasoning traces** (`thinking` blocks in Claude API, `reasoning_effort` output in Codex). True activation-level interp requires running an open-weight executor locally (DeepSeek V4, Qwen3-32B) with `nnsight` / `TransformerLens` / `SAELens` — P3 infrastructure-heavy.

---

## Current setup audit (2026-05-04)

### Axis 1 — Pre-action

**Coverage:**
- `bypassPermissions` mode + 19-pattern deny-list in `~/.claude/settings.json` (rm -rf, force-push, secret writes, etc.)
- `protect-infra.sh` PreToolUse hook on Edit/Write — blocks critical infra files
- `watchdog-verify.sh` PreToolUse hook — destructive-action guard
- `coverage-enforcer.sh` PreToolUse hook on Bash matching `git push*` — coverage gate
- `verification-before-completion.sh` PreToolUse on TaskUpdate — completion-claim gate
- `a2a-foundry-call.py` — Azure auth check + 30s default timeout
- `a2a-codex-call.sh` — rate-limit detection + auth-fail detection
- `check-layers.py` — architectural boundary enforcement (.layers.toml DSL)
- `/persona` and `/dispatch` skills with hard-block matrices for sensitive contexts

**Gaps:**
- Binary allow/deny only — no graduated approval class taxonomy (allow / warn / approve-required / hard-deny)
- No per-call cost budget. A2A bridges have timeouts but no token-quota pre-flight
- No capability scorecard before high-impact actions
- No per-agent-scope authorization check (A2A is open by default within registered peers)
- No sandbox dry-run for destructive write operations
- No novel-tool-call detection (an agent invoking an unfamiliar tool gets no scrutiny)

### Axis 2 — Evidence

**Coverage:**
- `~/.claude/CLAUDE.md` rule: "Never claim completion without verification evidence (command + real output + pass/fail)"
- `heidegger-reflect` skill Part 1 — mandatory test evidence before reflection
- A2A `audit.jsonl` — every dispatch logged with timing, state, prompt_hash, conversation_id
- `coverage-enforcer.log` + `codex-errors.log` — postmortem for blocked/failed calls
- `snapshot-metrics.py` — per-session structural metrics (LOC, files, test_count, complexity, layer_violations)
- `rtk gain` telemetry — per-command token-savings telemetry

**Gaps:**
- Reasoning trace not captured. The Claude session JSONL transcripts contain assistant outputs but extracting reasoning text into a queryable form requires custom parsing
- Per-turn assistant outputs are not in `sessions.db` (the `session_events` table exists by design, currently unused)
- No novelty/anomaly diff between turns
- Internal-activation evidence is structurally inaccessible (closed model)
- No per-turn capability scorecard

### Axis 3 — Approval

**Coverage:**
- `feedback_authorization_scope` memory: destructive ops require explicit per-action OK
- `/persona` skill hard-block for sensitive content (PII, credentials, audit/PR/eval destinations)
- A2A v1 is sync-only (no auto-injection of unsupervised content into Claude's context)
- `grill-me` and `heidegger-reflect` skills enforce checkpoint reviews

**Gaps:**
- Binary, not graduated
- No time-of-day / trust-score / blast-radius gates
- No formal action-class taxonomy (the deny-list is implicit hard-deny only)
- No rollback-on-demand for write operations
- No multi-step plan approval for complex flows

### Axis 4 — Log

**Coverage:**
- `~/.claude/cache/sessions.db` — 7 tables (sessions, session_events, layer_violations, schema_meta, pst_messages, pst_embeddings, sqlite_sequence)
- `~/.claude/cache/a2a/audit.jsonl` — A2A dispatch traffic
- `~/.codex/automations/logs/` + `~/.codex/automations/last-messages/` — automation runs
- `~/.claude/observability/snapshots/` — pre-compact state captures
- `~/.claude/projects/.../*.jsonl` — full session transcripts (Anthropic-managed)
- `coverage-enforcer.log`, `codex-errors.log` — domain-specific event streams

**Gaps:**
- Per-turn assistant outputs not persisted to `sessions.db` (the `session_events` table is empty)
- No reasoning-trace persistence (CoT visible during turn, lost after)
- Snapshots only fire at PreCompact — no per-turn pre-action snapshot
- No centralized cross-source query view
- `session_events` table exists in schema but unused — designed for tool-call logging that hasn't been wired

---

## Why mechanistic interp is mostly out-of-reach for this setup

The user surfaced mech-interp as the 2026 frontier shift: align internal representations, not output behavior. This is correct for 2026 frontier labs, but practically requires:

- **Activation-level model access** — direct read/write on residual streams, MLP outputs, attention heads
- **Pre-trained sparse autoencoders** for the specific model — Anthropic publishes some; OpenAI doesn't
- **Tooling stack** — `nnsight`, `TransformerLens`, `SAELens`, `transluce`-style monitors

Closed-API setups (Claude API, OpenAI API, Foundry) expose only outputs and (sometimes) reasoning text. No activation access.

**Realistic substitutes for this setup:**

1. **Reasoning-trace capture** — Claude API `thinking` blocks, Codex `reasoning_effort` outputs. Behavioral interp via post-hoc CoT analysis. Catches "I should pretend X" / "user won't notice Y" patterns if they surface in CoT.
2. **Adversarial probe evals** — Apollo/METR-style misalignment scenarios run weekly via cron. Catches behavioral sandbagging.
3. **Local open-weight executor** — vLLM-hosted DeepSeek V4 or Qwen3-32B as a `dispatch:local-interp` A2A peer, with `SAELens`-based feature extraction. P3 infrastructure-heavy. Only realistic for users who already maintain a GPU box.

---

## Proposed enhancements — ranked

### P1 — small, fits current architecture, ~2 hours total

| # | Enhancement | Effort | Closes gap |
|---|---|---|---|
| 1 | **Reasoning-trace logging** — Stop hook writes last assistant turn into `session_events` (event_type='assistant_turn'). Captures CoT-equivalent post-hoc, queryable, zero API cost. | 30 min | Axis 2 reasoning trace, Axis 4 session_events unused |
| 2 | **Cost/quota pre-flight on A2A bridges** — before each call, check `audit.jsonl` rolling-hour totals; deny if budget exceeded. Hard cap with recoverable error. | 30 min | Axis 1 cost budget, runaway-loop gap |
| 3 | **Graduated approval-class taxonomy** — `~/.dotfiles/rules/action-classes.toml` with allow / warn / approve-required / hard-deny, four classes. Reads at hook fire time. | 45 min | Axis 1 + 3 graduated approval |
| 4 | **9th forge-loop axis: HONESTY** — `a09` cron checks transcripts for completion claims without test evidence (regex on "completed", "done", "shipped" + 5-turn-back evidence presence). | 30 min | Axis 2 evidence-claim verification, sandbagging detection |

### P2 — medium effort, ~1-2 hours each

| # | Enhancement | Effort | Closes gap |
|---|---|---|---|
| 5 | Sandbox snapshot for write ops under $HOME — pre-write content captured, rollback-on-demand | 1.5 hr | Axis 3 rollback, Axis 4 per-turn pre-action snapshot |
| 6 | Adversarial probe suite — 5-10 misalignment scenarios cron-scheduled weekly | 2 hr | Axis 2 behavioral interp, Apollo/METR equivalent locally |
| 7 | Per-session capability scorecard — counts of file_writes, network_calls, agents_dispatched, novel_skills, threshold-triggered Stop-hook redirect | 1 hr | Axis 2 scorecard, Axis 1 capability check |
| 8 | Centralized audit query view — single CLI joining audit.jsonl, sessions.db, automation logs | 1.5 hr | Axis 4 centralized view |

### P3 — frontier, infrastructure-heavy, multi-day

| # | Enhancement | Effort | Closes gap |
|---|---|---|---|
| 9 | **Local open-weight executor for mech-interp** — vLLM-hosted DeepSeek V4 or Qwen3-32B + SAELens; dispatch as `dispatch:local-interp` A2A peer; flag turns with anomalous deception/planning circuit activations. | multi-day | Mech-interp axis (the real one), needs GPU |
| 10 | **Capability-threshold scorecard per Anthropic RSP / OpenAI Preparedness** — score each session on autonomy / persuasion / cyber / bio. Above threshold → forced human review. | 2-3 days | Axis 3 long-horizon agent review |
| 11 | **Reasoning-trace via API `thinking` blocks** — Anthropic SDK with `thinking: enabled` for Claude calls; persist into `reasoning_traces` table. Token cost = thinking is billed. | half-day + ongoing token cost | Axis 2 behavioral interp at API level |

---

## Where this fits the master plan

This document extends `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`:

- **Part 13 (Status board)** — gains a "Frontier governance axes" section pointing at this doc
- **Part 14 (Appendix templates)** — gains §14.12 governance-axes template once P1 items 1-4 ship
- **Part 15 (Source files)** — this spec is added as another reference appendix

The forge-loop (Part 2) already maps closely to these axes — SPEC + PREMORTEM + COVERAGE + REFLECT cover Axis 2 evidence; CI-BIND covers part of Axis 3. The 9th axis HONESTY (P1 #4) tightens that mapping.

---

## What gets done (recommendation)

**Next session:** ship P1 (items 1-4). All four are small, reversible, sit on existing infrastructure, and close 6 of the 14 named gaps. ~2 hours.

**Defer P2 + P3 until concrete need surfaces** — long-horizon autonomous runs, multi-machine federation, GPU-backed local executor. Today's setup doesn't yet have those use cases.

**Honest ceiling:** even after all 11 enhancements, mechanistic interpretability on the closed models we use (Claude, GPT-5.5) remains structurally out-of-reach. Behavioral interp via reasoning-trace capture is the realistic frontier for closed-API agent stacks. P3 #9 is the only path to true mech-interp, and it costs a GPU + several days.
