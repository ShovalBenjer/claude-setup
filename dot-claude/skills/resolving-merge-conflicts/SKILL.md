---
name: resolving-merge-conflicts
description: "Use when you need to resolve an in-progress git merge/rebase conflict."
---

# resolving-merge-conflicts

1. **See the current state**: git history, the conflicting files, and which side is the
   live base. The landing-beats-asking memory binds here: against a base that other
   sessions advance, merge, do not rebase.

2. **Find the primary sources** for each conflict: why each side changed, from commit
   messages, the PR, the ticket. Do not resolve a hunk whose intent you have not read.

3. **Resolve each hunk.** Preserve both intents where possible; where incompatible,
   pick the one matching the merge's stated goal and note the trade-off. Never invent
   new behaviour. Always resolve; never `--abort`.

   Estate-specific hunk rules, learned the expensive way:
   - `state/*.jsonl` ledgers are append-only and conflict at the tail by construction
     when two sessions appended. The resolution is always the union, both sides' rows
     kept, ours-then-theirs. A hash-chained ledger (prompt-tickets, bus, supply-chain,
     resource-ledger) will then carry a fork at the join point: record that fact, never
     rewrite earlier rows to "fix" the chain (25 such forks existed in
     prompt-tickets.jsonl before 2026-08-23, and repairing them is the operator's call).
   - Generated files (`docs/CODEBASE-MAP.md`, `docs/DOCMAP.md`, the TODO prompt-inbox
     block) are never hand-merged: take either side, then regenerate with the owning
     tool and commit that.
   - Tests and oracles: a conflict between a test and code that fails it is not
     resolved by weakening the test (tdd-enforcement rule).
   - Never bare `git stash` to clear the way: the stash stack is shared across
     worktrees and sessions. WIP commit instead.

4. **Run the checks the repo declares**: here, the root suite and `gate.py run`
   (background, per long-checks-background), plus `codemap check`/`docmap check` if
   docs moved. Fix what the merge broke.

5. **Finish**: stage, commit, and for a rebase continue to the end. The merge is
   finished by its post-merge check, not its click (merges-are-the-operators,
   follow-through section): fresh fetch, ancestry verified, gate against the merged
   branch, all in the same report.

Adapted 2026-08-23 from mattpocock/skills `engineering/resolving-merge-conflicts`
(MIT), steps 1 to 5 his shape, the hunk rules ours. Delta record:
docs/analysis/2026-08-23-pocock-skills-delta.md.
