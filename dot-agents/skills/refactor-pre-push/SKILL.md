---
name: refactor-pre-push
description: Suggest /simplify on hot-zone changed files immediately before /commit-push-pr runs the push step. Reminder skill, not auto-rewrite — preserves the authorization-scope rule that destructive ops need explicit OK. Triggers on "/refactor-pre-push", "before push", or as step 6 of Path A's standing workflow.
model: sonnet
---

# Refactor pre-push — REFACTOR axis support

## When to invoke

- About to execute `/commit-push-pr` step 4 (the push) of Path A
- User said "/refactor-pre-push" or "ready to push, anything to clean up first?"
- A hot-zone file (per `d05-hot-zone-indicator` automation) is in the staged diff

## Why this exists

The forge loop's REFACTOR axis is one of the three most-missed in the weekly audit (current 2.06/8). The audit looks for `/simplify` having been run on changed files. This skill closes that gap by surfacing the prompt to do so *just before push* — when the diff is final and the cost of extra cleanup is low.

## What it does

This is a **reminder, not an actuator**. It does NOT:
- Auto-run `/simplify`
- Auto-rewrite code
- Block the push

It DOES:
- Surface a 1-line check: "About to push N files. Have you run /simplify? Hot-zone changes detected: [list]"
- If hot-zone changes exist, recommend running `/simplify` first
- If the user says "skip refactor", record that for the forge audit (so the bypass is auditable, not silent)

## Protocol

1. Read the staged diff:
   ```bash
   git diff --cached --name-only
   ```
2. Cross-reference against hot zones (top-5 files by `fix()` commit count last 30 days, from latest `d05-hot-zone-indicator` output if available at `~/.Codex/docs/HOT_ZONES_*.md`).
3. Output a single line:
   - If no hot-zone overlap: "No hot-zone files changed — REFACTOR optional. Push?"
   - If hot-zone overlap: "Hot-zone files in this push: <list>. Recommend `/simplify` before push. Skip? (forge-loop REFACTOR axis will be marked skipped if yes.)"
4. Wait for user response. Don't proceed to push without explicit go.

## Anti-patterns

- **Don't auto-run `/simplify`.** Refactoring is destructive in spirit — changes code without test feedback. Path A's TDD discipline says don't refactor while RED, and don't refactor without explicit user OK.
- **Don't block the push.** The skill is a soft prompt. Hard blocks belong to the watchdog/protect-infra hooks.
- **Don't summarize what `/simplify` would do.** That's `/simplify`'s job. This skill only flags the opportunity.

## Integration with Path A

Path A step 6 is "refactor if /review surfaces findings". This skill is the *pre-push* check that catches refactor opportunities the forge loop says we should be addressing — independent of what `/review` finds later. It runs at step 4 (commit-push-pr), step 6 happens after step 5 (review).

So the order is:
- step 4 commit-push-pr → fires `refactor-pre-push` reminder before the push
- if user runs `/simplify`, push happens after
- if user skips, push happens immediately
- step 5 (review) happens after push regardless
- step 6 (refactor) happens only if step 5 surfaces findings

This means refactor-pre-push **prevents** step 6 cycles when used.
