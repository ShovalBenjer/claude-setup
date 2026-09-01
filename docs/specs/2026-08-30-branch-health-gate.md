# Branch Health Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** branch_health

## Problem

Stale branches (merged into the default branch but not deleted) and orphaned
worktrees are the two shapes of git debris that have caused gate failures in
this repo. The codemap domain excludes `.claude/worktrees` from compileall
because a sibling worktree carried live conflict markers; the types domain
failed on the same markers. Nothing in the quality contract caught this debris
before it broke a downstream domain.

## Solution

A new `cmd` domain `branch_health` in `quality-contract.json` runs
`python tools/audit/branch_health.py check --project .`. The tool exits 0
when no stale branches or worktree problems are found, and nonzero when any
issue is detected.

The oracle checks three things:
1. Branches fully merged into the default branch that have not been deleted
   (excluding branches checked out in an active worktree)
2. Worktrees marked prunable by git
3. Worktree directories that no longer exist on disk

## Scope

- `tools/audit/branch_health.py`: new oracle with `check` and `selftest`
  subcommands
- `quality-contract.json`: `branch_health` domain entry (cmd, timeout 60s)

## Design decisions

- A `cmd` domain rather than a builtin, because the oracle has its own
  selftest and a clean exit-code contract.
- Branches checked out in an active worktree are excluded from the stale
  branch check, since they are actively in use even if their content is
  merged.
- Timeout set to 60s; the check runs only local git commands.
- The selftest creates a temporary repo and exercises the clean, stale-branch,
  valid-worktree, and orphaned-worktree paths.

## Non-goals

- Automatically pruning worktrees or deleting branches. The domain reports;
  the operator decides.
- Checking remote branches. Only local refs are in scope.
