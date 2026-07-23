# ADR-0007 — Second reviewer = free different-family models (Codex removed)

Status: Amended (2026-07-23 PM): Codex subscription is being cancelled. The
decorrelated-second-reviewer role moves to FREE, different-family models — Gemini
(AI Studio free tier) as primary, OpenRouter/Groq free tiers (DeepSeek/Llama) for a
third voice. Models are interchangeable ACTORS assigned to model-agnostic personas
(see persona-review-economy spec), never hardcoded to a role. Original Codex-as-
reviewer decision below, kept for history.

---
## Original (Codex as reviewer, not executor)

## Context
The global CLAUDE.md said "Codex is the executor (gpt-5.5); Claude is the
orchestrator." The 2026-07-20 decision made the hiring engine claude-only and killed
the Codex execution handoff. But Codex remains valuable as a DIFFERENT model for
decorrelated review (ADR-0004).

## Decision
Codex's role in the personal OS is independent reviewer / second opinion only,
reached via `a2a-codex-call.sh` (read-only, low effort, audited). It does not execute
build tasks, does not own runtime, does not carry the loop. Claude orchestrates and
executes; Codex reviews.

## Consequences
+ Resolves the standing contradiction between the global rule and the 07-20 decision.
+ Preserves Codex's real value (model diversity for the agreement gate) without the
  dead execution handoff.
- The global CLAUDE.md line is now stale and should be updated to match.
- A2A audit must record which model reviewed, for provenance.
