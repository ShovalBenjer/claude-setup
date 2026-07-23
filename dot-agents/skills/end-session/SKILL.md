---
name: end-session
description: End-of-session cleanup — security wipe of temp files, context compaction, lessons learned post-mortem, handover for next session. Run before /clear or exiting.
---

# /end-session

Safe session teardown with cleanup, compaction, lessons learned, and handover.

## Triggers

- Before `/clear`
- Before closing Codex terminal
- When context reaches 80%+ (status line shows `/clear!`)
- Manual invocation for mid-session checkpoint

## Usage

```
/end-session [--quick]
```

- `--quick`: Security cleanup + save tasks only (skip post-mortem)

## Instructions

Run all phases in order. Do NOT skip the security cleanup.

---

### Phase 1: Security Cleanup (MANDATORY)

Wipe all temp files that may contain tokens, secrets, or cached sensitive data:

```bash
# Wipe token files
for f in /tmp/.codex-azdo-token /tmp/.Codex-azdo-token /tmp/.secret-* /tmp/.token-*; do
  [ -f "$f" ] && : > "$f"
done

# Clear cached status files (contain infrastructure metadata)
for f in /tmp/.codex-ci-status /tmp/.codex-last-test-result /tmp/.codex-workflow-phase /tmp/.Codex-ci-status /tmp/.Codex-last-test-result /tmp/.Codex-workflow-phase; do
  [ -f "$f" ] && : > "$f"
done

# Clear any Python/Node REPL history from this session
: > /tmp/.python_history 2>/dev/null || true
```

**Verify cleanup:**
```bash
ls -la /tmp/.codex-* /tmp/.Codex-* /tmp/.secret-* /tmp/.token-* 2>/dev/null
# All should be empty (0 bytes) or absent
```

---

### Phase 2: Task State Snapshot

Check for in-progress tasks and save their state:

1. Run `TaskList` to see all current tasks
2. For any in-progress tasks: update status with current state
3. Mark completed tasks as completed
4. Note any blocked tasks and their blockers

---

### Phase 3: Lessons Learned & Post-Mortem (skip with --quick)

Write a session post-mortem. This is NOT a status report — it captures what was *learned* that future sessions should know.

**Template:**
```markdown
# Session Post-Mortem: {DATE}

## What was accomplished
- {bullet list of completed work}

## What was learned (non-obvious)
- {things discovered that weren't known before}
- {patterns that worked or failed}
- {gotchas encountered}

## Decisions made
- {DECISION}: {what} — {why} — {alternatives considered}

## What's unfinished
- {task}: {current state} — {what remains} — {blocker if any}

## Process observations
- {what went well in the workflow}
- {what was slow or frustrating}
- {what should change for next time}

## Security notes
- {any secrets/tokens used this session}
- {any infrastructure topology exposed}
- {any temp files that need attention}
```

**Where to save (per-session, never a shared name):**
- If a spec/project is in progress: append to `docs/reflections/YYYY-MM-DD-session.md`
- Otherwise: save to `~/.codex/cache/sessions/YYYY-MM-DD-<project>-session.md`, where
  `<project>` is the cwd basename. Several Claude/Codex sessions run in parallel; a
  date-only name lets a same-day session on another project overwrite yours, so include
  the project. If a file for a different project already exists, never overwrite it.

---

### Phase 4: Memory Updates

Two paths — pick based on signal strength.

**Path A: Single-session (this conversation only)**

Review THIS session for memory-worthy items:

1. **Feedback memories**: Did the user correct an approach? Did a non-obvious approach work?
2. **Project memories**: Did we learn something about ongoing work, deadlines, stakeholders?
3. **User memories**: Did we learn about preferences, role, knowledge level?
4. **Reference memories**: Did we discover external resources?

Update existing memories if they're stale. Create new ones only for genuinely new information.

**Path B: Cross-session aggregation** (run when ≥3 new sessions accumulated since last curate)

If the marker `~/.codex/cache/layer7/.last-curate` is older than 3 sessions ago in `~/.codex/cache/sessions.db`, run `/memory-curator` instead. It compares the recent session corpus against current memory and proposes new entries / dedupes / removals as a single batch — better signal than per-session inspection alone.

Decision rule: Path B if `SELECT COUNT(*) FROM sessions WHERE ts > {marker}` ≥ 3, else Path A.

---

### Phase 5: Context Compaction

Prepare a compact handover that reduces tokens for the next session:

1. **Run `/project-state`** to save status.json and handover.md
2. **Humanize the handover** (if `/humanize` available): ensure the handover reads naturally, not like AI slop
3. **Create a resume prompt** at `~/.codex/cache/resume/<project>-<HHMMSS>.md` (a
   PER-SESSION file, NEVER the shared `~/.codex/cache/resume-prompt.md`). `<project>` is
   the cwd basename and `<HHMMSS>` (or a short session id) disambiguates same-project
   parallels. Multiple sessions run at once; a single shared resume file gets clobbered and
   one session's handover is lost. Before writing, if a resume file owned by a DIFFERENT
   session/project already exists, never overwrite it, write your own namespaced file:

```markdown
# Resume Prompt for Next Session

## Context
{2-3 sentence summary of where we are}

## Active Work
- {branch}: {what's being done} — {next step}

## Key Files Modified This Session
- {file}: {what changed}

## Unresolved
- {issue}: {current state}

## Start With
{the first thing to do next session}
```

The resume prompt should be <500 tokens. It replaces reading the full conversation history.

---

### Phase 6: Final Status

Print a clean session summary:

```
╔══════════════════════════════════════════╗
║         SESSION COMPLETE                  ║
║         {DATE} | {DURATION}              ║
╠══════════════════════════════════════════╣
║  Tasks completed:  {N}                   ║
║  Files modified:   {N}                   ║
║  Tests passing:    {yes/no}              ║
║  Security cleanup: {done}                ║
║  Handover saved:   {path}                ║
║  Lessons saved:    {path}                ║
║  Ready for /clear: YES                   ║
╚══════════════════════════════════════════╝
```

**Then fire end-session meme:**
```bash
~/.claude/bin/play-meme.sh end_session &
```

---

## What This Skill Replaces

Previously, session boundaries required manually running:
- `/project-state` (handover)
- `/heidegger-reflect` (lessons)
- Manual cleanup

`/end-session` combines all of these into one command with security cleanup added.

## Security Rationale

Codex conversations are sent to Anthropic's API for processing. While Anthropic has data handling policies, the principle of least exposure applies:
- Temp files with tokens should not persist beyond the session
- Infrastructure metadata in cache files should be cleared
- The conversation itself cannot be wiped (it's already sent), but we minimize what persists locally
- Future sessions should use the CI poller script (runs outside Codex's view) rather than inline `az` commands
