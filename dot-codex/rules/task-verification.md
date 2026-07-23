# Task Completion Verification

## Purpose

Prevent false task completion claims. A task is NOT complete until VERIFIED.

## Mandatory Verification Protocol

Before marking ANY task as complete, you MUST:

1. **RUN the verification command** - Not just say you did
2. **CAPTURE the output** - Show actual evidence
3. **CONFIRM zero errors** - Count must be zero, not "approximately"
4. **TEST in real environment** - Not just "should work"

## Task Completion Checklist

For each task, you MUST answer:

```
Task: [name]
Verification Command: [exact command run]
Output: [paste actual output]
Errors: [count] ([list them])
Pass: YES/NO
```

## Forbidden Phrases

- ❌ "This should work"
- ❌ "The fix is complete" (without running tests)
- ❌ "Task completed successfully" (without evidence)
- ❌ "All tests pass" (without showing output)
- ❌ "Configured" (without testing the config)

## Required Phrases

- ✅ "Ran: [command], got: [output]"
- ✅ "Verification: [X errors, Y warnings]"
- ✅ "Test result: [PASS/FAIL] with evidence: [link/screenshot]"

## Task Categories & Minimum Verification

| Category | Minimum Verification |
|----------|---------------------|
| Code Change | Tests pass, linter passes, type check passes |
| Config Change | Config loaded, app starts, feature works |
| UI Change | Screenshot, accessibility test, visual review |
| API Change | Request/response test, error handling verified |
| Infrastructure | Service starts, health check passes, logs clean |

## Anti-Patterns

### Pattern: Premature Completion
```
❌ BAD: "I created the component. Task done."
✅ GOOD: "Created component at X. Ran `bun run type-check` - 0 errors. 
         Added test at Y. Ran `bun test` - all pass. Screenshot: Z"
```

### Pattern: Surface-Level Implementation
```
❌ BAD: "Added ESLint rule. Task complete."
✅ GOOD: "Added rule to .eslintrc.json. Ran `bun run lint`:
         - Before: 5 violations
         - After: 5 violations (rule is warn, not error)
         - Action: Need to fix violations before task complete"
```

### Pattern: Infrastructure Without Testing
```
❌ BAD: "Created CI workflow. Ready for review."
✅ GOOD: "Created workflow. Tested locally with `act`:
         - Job runs successfully
         - All steps complete
         - Output: [paste logs]
         - Note: Need to merge to test on real PR"
```

## Self-Reflection Requirement

Before ANY "task complete" statement, ask yourself:

1. Did I RUN the verification? (not just think about it)
2. Did I CAPTURE evidence? (not just claim success)
3. Did I TEST edge cases? (not just happy path)
4. Would a skeptic be convinced? (show the proof)

If ANY answer is "no" or "sort of", the task is NOT complete.
