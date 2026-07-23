---
name: memory-curator
description: Periodically review recent Codex sessions for memory-worthy patterns and propose updates to MEMORY.md and individual memory files. Always proposes — never auto-writes.
---

# /memory-curator

Layer 7 cross-session learning loop. Reads stored session summaries since the last curate marker, compares against current memory, proposes new entries / updates / dedupes / removals. User approves before any write.

## When to run

- Manual: `/memory-curator` whenever the user asks
- Recommended cadence: weekly, OR after a session that surfaced strong feedback signals
- Optional: chain into `/end-session` Phase 4 (memory updates)

## Inputs

| Source | What |
|--------|------|
| `~/.Codex/cache/sessions.db` | Session summaries from Layer 7 (table `sessions`) |
| `~/.Codex/cache/layer7/.last-curate-<project-key>` | Per-project ISO8601 marker (or absent → all sessions) |
| `~/.Codex/projects/<project-key>/memory/MEMORY.md` | Project memory index |
| `~/.Codex/projects/<project-key>/memory/*.md` | Project memory files |

## Outputs

| File | Purpose |
|------|---------|
| `~/.Codex/cache/memory-proposals.md` | Transient proposal — user reviews, then I apply |
| `~/.Codex/cache/layer7/.last-curate-<project-key>` | Updated only AFTER user accepts proposal |

## Phases

### Phase 1 — Load scope

Resolve project scope and read the marker:
```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PROJECT_KEY=$(printf '%s' "$PROJECT_ROOT" | sed 's#/#-#g')
MEM_DIR="$HOME/.Codex/projects/${PROJECT_KEY}/memory"
MARKER="$HOME/.Codex/cache/layer7/.last-curate-${PROJECT_KEY}"
mkdir -p "$MEM_DIR"
export PROJECT_ROOT
LAST=$(cat "$MARKER" 2>/dev/null || echo "1970-01-01T00:00:00+00:00")
export LAST
echo "Curating project=$PROJECT_ROOT since: $LAST"
```

Query sessions added since marker via the venv Python (sqlite-vec not required, plain sqlite3 works):

```python
import os
import sqlite3
project_root = os.environ["PROJECT_ROOT"]
legacy_basename = project_root.rsplit("/", 1)[-1]
last = os.environ["LAST"]
db = sqlite3.connect("/home/shovalbe/.Codex/cache/sessions.db")
rows = db.execute(
    "SELECT id, ts, project, branch, summary_text, test_result "
    "FROM sessions WHERE ts > ? AND (project = ? OR project = ?) ORDER BY id",
    (last, project_root, legacy_basename)  # basename fallback for legacy rows
).fetchall()
```

If `len(rows) < 3`: skip with "not enough new signal — try again after more sessions".

### Phase 2 — Read current memory

Read `MEMORY.md` (the index) and every file it references. Build an in-memory map: `{name: (type, description, body)}`.

### Phase 3 — Analyze (LLM judgment, not script)

Look at session prompts/outputs for these signals:

| Signal | Action |
|--------|--------|
| Recurring user correction not in feedback memory | Propose NEW feedback entry |
| Two memories overlap heavily | Propose DEDUPE (merge) |
| Memory contradicted by recent session behavior | Propose UPDATE or REMOVE with evidence |
| Project memory mentions a deadline that has passed | Propose REMOVE or UPDATE |
| Reference memory points to a resource no longer used | Propose REMOVE |
| Strong validated approach used in 3+ sessions | Propose NEW feedback (validated, not corrected) |
| Anti-pattern: memory cites file path / function name | Verify it still exists; if not, propose UPDATE |

**Do NOT propose:**
- Code-pattern memories (derivable from current code)
- Git history facts (use `git log`)
- Ephemeral task state (belongs in tasks, not memory)
- Anything already in AGENTS.md
- Restatements of existing memories with cosmetic changes

### Phase 4 — Write proposal file

Write `~/.Codex/cache/memory-proposals.md` in this exact format:

```markdown
# Memory Curation Proposal

**Generated:** {ISO8601}
**Sessions reviewed:** {N} (since {LAST})
**Current memory entries:** {M}

## NEW (proposed additions)

### {file_name}.md
**Type:** {feedback|user|project|reference}
**Description:** {one-line}
**Evidence:** Sessions {ids} — {brief reason}

```markdown
{full proposed file content with frontmatter}
```

## UPDATE (proposed edits to existing)

### {file_name}.md
**Reason:** {what's stale or wrong}
**Evidence:** Sessions {ids}

**Diff:**
```diff
- {old line}
+ {new line}
```

## DEDUPE (proposed merges)

### {file_a}.md + {file_b}.md → {merged_name}.md
**Overlap:** {what's duplicated}
**Proposed merged content:** {summary or full file}

## REMOVE (proposed deletions)

### {file_name}.md
**Reason:** {why stale}
**Evidence:** {what contradicts it}

## SKIP (signals seen but not actionable)

- {signal}: {why not actionable yet — e.g., "only 1 session, need pattern"}
```

### Phase 5 — Present to user

Print a summary:

```
Memory curation proposal ready: ~/.Codex/cache/memory-proposals.md
  NEW:    {N}
  UPDATE: {N}
  DEDUPE: {N}
  REMOVE: {N}

Review and respond:
  - "apply all" → I write everything as proposed
  - "apply 1,3,5" → cherry-pick by item number
  - "edit X" → modify before applying
  - "skip" → discard proposal, leave marker untouched
```

**Do NOT touch any memory files until the user responds.**

### Phase 6 — Apply (only after explicit user approval)

For each accepted item:
1. NEW: Write the file using Write tool
2. UPDATE: Use Edit tool with the diff
3. DEDUPE: Write merged file, delete originals (only after confirming with user)
4. REMOVE: Use `rm` (only after confirming with user)
5. After all accepted writes: update `MEMORY.md` index lines accordingly

After successful application, update marker:
```bash
date -u +"%Y-%m-%dT%H:%M:%S+00:00" > "$HOME/.Codex/cache/layer7/.last-curate-${PROJECT_KEY}"
```

Print final report:
```
Applied: {N} new, {N} update, {N} dedupe, {N} remove
MEMORY.md updated: {yes/no}
Marker advanced to: {timestamp}
```

## Anti-patterns (reject from your own proposals)

| Pattern | Why reject |
|---------|-----------|
| "User said X once" as evidence | Need pattern, not single instance |
| Proposing memory of code structure | Derivable from code |
| Restating AGENTS.md content | Already loaded |
| Merging memories from different categories | Loses semantic clarity |
| Removing memory based on absence of recent mention | Absence ≠ obsolescence |
| Generated memory bodies that look like AI summaries | Memories should sound like the user |

## Cost note

This skill runs entirely on session text already in the local DB. No API calls needed for the analysis itself — only the LLM context window. Skipping if `<3` new sessions keeps it cheap.

## Why "propose, don't auto-write"

Memories shape future behavior. A bad memory persists across sessions and can drift the agent. The user is the only authority on what "the user actually thinks". Auto-writing creates a feedback loop where Codex convinces itself of patterns the user never validated.
