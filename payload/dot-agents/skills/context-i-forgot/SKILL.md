---
name: context-i-forgot
description: Mid-session context injection. Capture forgotten info, classify impact, resume primary task.
---

## Purpose

Handle mid-session interruptions where the user remembers something important
or sees something that needs noting. Prevents losing the current thread.

## Protocol

### Step 1: Snapshot

Before accepting new context, capture the current state:
- What task is in progress (name, goal)
- What files are being worked on
- Current progress estimate (%)
- What step comes next

State this snapshot explicitly so the user sees it preserved.

### Step 2: Accept

Listen to the user's new context. Could be:
- A forgotten requirement or constraint
- Something they saw (error, log, UI issue)
- A new idea or secondary task
- A correction to earlier instructions

### Step 3: Classify

Determine the impact on current work:

**Orthogonal** (does NOT affect current task):
- Create a TaskCreate entry with clear description
- Note it was captured: "Logged as task #N for later."
- Resume primary work immediately

**Impactful** (DOES affect current task):
- Explain what changes in the current approach
- State the delta: "This means we also need to..."
- Re-plan if needed, then continue from where we stopped

### Step 4: Resume

Return to the primary thread with an explicit statement:
- "Resuming [task name]. Next step: [what was next]."
- If impactful: "Adjusted plan: [what changed]. Continuing from [step]."

### Step 5: Trace

Log the injection for compaction awareness:
- If using TaskList: the task entry serves as the record
- If orthogonal: mention it in the eventual commit message or work log

## Rules

- Never silently absorb context -- always classify and acknowledge
- Never abandon current task for an orthogonal item
- Never lose the thread -- always state what you were doing and what comes next
- If unsure whether orthogonal or impactful, ask the user
