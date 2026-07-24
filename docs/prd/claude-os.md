---
prd: Claude OS
ticket: SETUP-OS
status: active
spine: ../../CLAUDE-OS.md
updated: 2026-07-23
---

# PRD — Claude OS (personal Claude control plane)

THE spine is `CLAUDE-OS.md` at repo root (layers L0-L8, deep-work protocol,
native-feature map, dynamism loops). This PRD is the ticketed acceptance surface:
one row per capability, status + evidence. When work lands, update the row here —
do not spawn a dated note (docs-control-plane rule).

## Problem

One operator, 6+ parallel Claude sessions, three ventures (hiring, learning, the
OS), four I/O channels. Coherence currently depends on the operator carrying state
between sessions by memory. Conversational prompting yields partial, shallow output;
the operator wants deliberate, long-horizon, organic-quality systems. The OS must
carry the state and enforce the depth structurally.

## Goal / North Star

Capture intent anywhere → verified action comes back to the phone. Run on the
Claude subscription at near-zero external cost. The operator is an approval surface,
not a coordinator.

## Non-goals

- Not a prompt collection. Not autonomous-do-anything. Not a work-machine port
  (Seekapa/Azure/systemd assets are excavation input, not carried).
- Not self-modifying without approval (ADR-0005).

## Acceptance table

| # | Capability | Layer | Status | Evidence |
|---|---|---|---|---|
| 1 | claude-setup = canonical OS repo, relocated, July state, pushed | L1/L6 | DONE 2026-07-23 | commit 146cb7b; github.com/ShovalBenjer/claude-setup |
| 2 | CLAUDE-OS.md single source of truth, supersedes all prior plans | L0 | DONE | CLAUDE-OS.md §5 supersession table |
| 3 | Notification fabric: phone push + desktop toast verified | L4 | DONE 2026-07-22 | push test #4 landed; notify-toast.ps1 hook |
| 4 | Always-fresh PR review workflow on every source repo | L5 | DONE 2026-07-23 (auth pending) | 22 repos; OAuth token SET on all 22 (2026-07-23); live review PROVEN on PR #2 (4/4 seeds caught) |
| 5 | Deep Work Protocol hooks (spec-anchor, handoff, slop gate, postconditions, RTK guard) | L0 | TODO | — |
| 6 | Daily digest push from cron | L4 | TODO | tools/digest/ scaffold on test branch |
| 7 | SessionStart recall injects digest + skills (Windows paths) | L2 | TODO | — |
| 8 | Multi-model agreement-gated review, provenance + audit | L5 | PARTIAL | Claude-only proven (PR #2); 2nd model = free Gemini (Codex removed, ADR-0007); agreement gate pending |
| 9 | WhatsApp copilot: triage + style drafts + coaching retro | L2/L4 | TODO (scope granted) | tools/whatsapp readers proven |
| 10 | Learning-card emitter → הסדנה queue | L8 | TODO | — |
| 11 | Scheduler topology consolidated; WSL systemd retired | L3/L7 | TODO | — |
| 12 | Skills estate fully owned/merged/archived | L5 | TODO | — |
| 13 | Weekly self-improvement loop running | L5 | TODO | — |
| 14 | **Memory + web-search write pipe** (fetch→distill→typed memory) | L2 | TODO | — |
| 15 | **Repo portfolio graph** (nodes+edges, d2 + SQLite) | L6 | TODO | — |
| 16 | **Blast-radius graph** (intra-repo import/call, feeds PR fanout) | L5/L6 | TODO | — |
| 17 | **Git branch health sweep** (stale/merged/drift, gated actions) | L5 | TODO | — |
| 18 | **Rules-as-enforcement** (per-repo rules bound to hooks, not prose) | L1 | TODO | — |
| 19 | **Persona review economy** (contracts, reputation, PIP, fire, recruit) | L5/L8 | TODO | spec 2026-07-23-persona-review-economy |
| 20 | Concierge phone topology (Mayor owns the line, dispatches) | L3 | TODO | — |

## Maturity target

L4 Governed Control Plane (policy enforcement, approval gates, independent review,
eval gates, audit, provenance) → L5 Self-Improving Personal AI OS. Tracked per ADR.

## Pending operator decisions

1. Global default model fable[1m] → sonnet (config edit awaits OK).
2. Rotate API key found in תזכורת לעצמי group.
3. PR-fabric opt-in repo list (default: all 22).
4. WhatsApp copilot cadence (2x daily proposed) + coaching frequency.
5. Authorize subscription OAuth token (in-progress; unblocks #4 acceptance).
