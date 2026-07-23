---
name: triage-issue
description: Triage a bug or issue by exploring the codebase to find root cause, then create a tracked work item (ADO or GitHub auto-detected) with a TDD-based fix plan. Use when user reports a bug, wants to file an issue, mentions "triage", or wants to investigate and plan a fix for a problem.
---

## Backend — auto-detect (ADO or GitHub)

```bash
backend=$(~/.Codex/bin/work-item.sh detect)
~/.Codex/bin/work-item.sh create --title "<title>" --body "$BODY" --type bug --tags "triaged"
```

Maps to `az boards work-item create --type Bug` on Azure DevOps. Full mapping: `~/.Codex/rules/ado-issue-mapping.md`.

## PR + Pipeline flow (ADO repos)

When a triaged work item is implemented later:

1. Implementing agent creates `feature/<work-item-id>-<slug>` branch from current target.
2. Commits with `#AB<id>` reference (ADO auto-links the work item).
3. Opens PR via `~/.Codex/bin/work-item.sh pr-create --link <work-item-id> --target stage`.
4. PR creation triggers the build pipeline defined in `azure-pipelines.yml` (CI runs Tier 1+2 gates).
5. Track pipeline via `~/.Codex/bin/work-item.sh pr-pipeline-status <pr-id>`.

This skill files the work item; the implementing agent handles the PR. Per `production-safety.md`, never deploy directly — the PR-merge-to-master path is the only deploy route.

# Triage Issue

Investigate a reported problem, find its root cause, and create a GitHub issue with a TDD fix plan. This is a mostly hands-off workflow - minimize questions to the user.

## Process

### 1. Capture the problem

Get a brief description of the issue from the user. If they haven't provided one, ask ONE question: "What's the problem you're seeing?"

Do NOT ask follow-up questions yet. Start investigating immediately.

### 2. Explore and diagnose

Use the Agent tool with subagent_type=Explore to deeply investigate the codebase. Your goal is to find:

- **Where** the bug manifests (entry points, UI, API responses)
- **What** code path is involved (trace the flow)
- **Why** it fails (the root cause, not just the symptom)
- **What** related code exists (similar patterns, tests, adjacent modules)

Look at:
- Related source files and their dependencies
- Existing tests (what's tested, what's missing)
- Recent changes to affected files (`git log` on relevant files)
- Error handling in the code path
- Similar patterns elsewhere in the codebase that work correctly

### 3. Identify the fix approach

Based on your investigation, determine:

- The minimal change needed to fix the root cause
- Which modules/interfaces are affected
- What behaviors need to be verified via tests
- Whether this is a regression, missing feature, or design flaw

### 4. Design TDD fix plan

Create a concrete, ordered list of RED-GREEN cycles. Each cycle is one vertical slice:

- **RED**: Describe a specific test that captures the broken/missing behavior
- **GREEN**: Describe the minimal code change to make that test pass

Rules:
- Tests verify behavior through public interfaces, not implementation details
- One test at a time, vertical slices (NOT all tests first, then all code)
- Each test should survive internal refactors
- Include a final refactor step if needed
- **Durability**: Only suggest fixes that would survive radical codebase changes. Describe behaviors and contracts, not internal structure. Tests assert on observable outcomes (API responses, UI state, user-visible effects), not internal state. A good suggestion reads like a spec; a bad one reads like a diff.

### 5. Create the work item

Create a work item using `~/.Codex/bin/work-item.sh create --title "<title>" --body "$BODY" --type bug --tags "triaged"` with the template below. Do NOT ask the user to review before creating — just create it and share the URL/ID.

<issue-template>

## Problem

A clear description of the bug or issue, including:
- What happens (actual behavior)
- What should happen (expected behavior)
- How to reproduce (if applicable)

## Root Cause Analysis

Describe what you found during investigation:
- The code path involved
- Why the current code fails
- Any contributing factors

Do NOT include specific file paths, line numbers, or implementation details that couple to current code layout. Describe modules, behaviors, and contracts instead. The issue should remain useful even after major refactors.

## TDD Fix Plan

A numbered list of RED-GREEN cycles:

1. **RED**: Write a test that [describes expected behavior]
   **GREEN**: [Minimal change to make it pass]

2. **RED**: Write a test that [describes next behavior]
   **GREEN**: [Minimal change to make it pass]

...

**REFACTOR**: [Any cleanup needed after all tests pass]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All new tests pass
- [ ] Existing tests still pass

</issue-template>

After creating the issue, print the issue URL and a one-line summary of the root cause.
