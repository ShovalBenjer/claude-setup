---
name: jira-task-draft
description: Draft Jira tasks + subtasks LOCALLY as markdown so Shoval can paste them into Jira by hand. Never calls the Jira API. Saves to ~/docs/jira-tasks/YYYY-MM-DD-<topic>.md. Triggers on "/jira-draft", "/draft-jira", "ticket this", "draft jira ticket", "create task locally for", "draft jira tasks".
model: sonnet
---

# Jira Task Draft (local-only)

Use this skill to draft Jira tasks + subtasks as a structured markdown file that Shoval can copy/paste into Jira's "Create issue" UI by hand. **Never** calls the Jira API. **Never** auto-creates tickets.

Companion to `meeting-notes` — meeting notes capture what *was decided*, this skill captures what *will be done* in Jira-shaped form.

## When to trigger

- User says `/jira-draft`, `/draft-jira`, `/jira-task-draft`
- User says "ticket this", "draft jira ticket(s) for", "create task locally for", "draft jira tasks for <initiative>"
- After a meeting-notes session, when the user wants the action items turned into ticket-shaped drafts

Do NOT trigger from casual mentions ("we should make a ticket someday"). The user must convey a concrete initiative with at least one identifiable task.

## Required inputs

Before writing the file, you need:
- **Initiative / topic**: 2-6 word phrase used in the filename
- **At least one parent Task** with a clear summary
- **At least one Subtask under each Task** (otherwise it's just a Task, not a task+subtask structure — push back briefly)

Optional but useful:
- Priority hint (P0 / P1 / P2 / P3 or High / Medium / Low)
- Component / label hints (Infra, Backend, Frontend, AI, DevOps)
- Estimate hint (S / M / L or hours)
- Dependencies between tasks (blocker / blocks)

If a required field is missing, ask ONE concise question. Do not invent placeholders.

## File format

Save to `~/docs/jira-tasks/YYYY-MM-DD-<kebab-topic>.md`. If a file for that date+topic exists, append `-2`, `-3`, etc.

```markdown
# Initiative: <Topic>

**Date drafted:** YYYY-MM-DD
**Owner:** Shoval (unless overridden)
**Context (1-2 sentences):** <why this initiative exists right now>

---

## TASK 1: <terse summary, imperative voice>

- **Type:** Task
- **Priority:** <P0 / P1 / P2 / P3>
- **Components / labels:** <comma-separated, may be empty>
- **Estimate:** <S / M / L or hours, optional>
- **Depends on:** <other TASK # in this file, or external ticket key, or none>

**Description:**
<2-5 sentences. What changes after this is done. Be concrete.>

**Acceptance criteria:**
- <bullet>
- <bullet>

### Subtasks

- [ ] **SUB 1.1:** <imperative summary>
      Description: <one-liner or short paragraph>
      Estimate: <optional>
- [ ] **SUB 1.2:** <imperative summary>
      Description: <one-liner>

---

## TASK 2: <next parent>

(same structure)
```

## How Shoval uses the output

1. Opens the file
2. For each TASK: clicks "Create issue" in Jira → pastes the summary + description + AC
3. For each SUB under that task: uses Jira's "Add child issue" / "Create subtask" → pastes the SUB summary + description
4. Checks off the boxes (`- [x]`) in the local file as he creates each one in Jira
5. Optional: writes the Jira keys back into the file (e.g. `SUB 1.1: SK-1234` ✓)

## Voice rules

- **Imperative summaries.** "Ship v3 via PR" not "We need to ship v3 via PR". One verb at the start.
- **Concrete acceptance criteria.** "ACA health endpoint returns 200 in production browser" not "deployment works".
- **No filler.** Skip "Background:" / "Notes:" sections unless they add information not already in description.
- **Hebrew/English mixing preserved verbatim** if Shoval used it.
- **No emojis** unless the user used them.

## What this skill does NOT do

- Does not call `mcp__atlassian__jira_*` tools — these exist but are off-limits for this skill
- Does not pick a project key — that's Shoval's call in Jira UI
- Does not assign people — assignment happens in Jira after creation
- Does not save anywhere except `~/docs/jira-tasks/`
- Does not modify the user's Atlassian state in any way

## Cross-references

- Companion: `meeting-notes` (decisions → tickets pipeline)
- Companion: `shoval-voice-draft` (for follow-up messages about ticket assignments)
