---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable work items (ADO or GitHub auto-detected) using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

## Backend — auto-detect (ADO or GitHub)

Detect the backend before any issue/PR command:

```bash
backend=$(~/.claude/bin/work-item.sh detect)  # "ado" | "gh"
```

Use `~/.claude/bin/work-item.sh create` instead of literal `gh issue create`. It maps to `az boards work-item create --type 'User Story'` on Azure DevOps repos. Full mapping: `~/.claude/rules/ado-issue-mapping.md`.

For each work item created, the implementing agent should later create a feature branch and open a PR via `~/.claude/bin/work-item.sh pr-create --link <work-item-id>` — on ADO this auto-links the work item and triggers the build pipeline.

# To Issues

Break a plan into independently-grabbable work items using vertical slices (tracer bullets).

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue/work-item ID or URL as an argument, fetch it with `~/.claude/bin/work-item.sh view <id>` (auto-routes to `gh issue view` or `az boards work-item show`).

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Create the work items (ADO work items / GitHub issues)

For each approved slice, create a work item using `~/.claude/bin/work-item.sh create --title "<slice>" --body "$BODY" --type "User Story" --tags "tracer-bullet"`. Use the issue body template below. On ADO, the work item ID returned should be passed as `--link` to `work-item.sh pr-create` later so the PR triggers the linked-work-item pipeline.

Create issues in dependency order (blockers first) so you can reference real issue numbers in the "Blocked by" field.

<issue-template>
## Parent

#<parent-issue-number> (if the source was a GitHub issue, otherwise omit this section)

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Blocked by #<issue-number> (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.
