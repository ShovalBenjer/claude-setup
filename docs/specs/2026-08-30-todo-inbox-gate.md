# TODO Inbox Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** todo_inbox

## Problem

`tools/intent/render_todo.py` maintains a generated prompt-inbox block inside
TODO.md, rendering captured prompts from the intent store so they are visible
until triaged. The tool existed with a selftest and a `check` subcommand, but
nothing in the quality contract invoked it. A TODO.md whose generated block
drifted from the store would pass the gate silently, hiding every untriaged
prompt from the operator.

## Solution

A new gate builtin `todo_inbox` calls `render_todo.py check --project .` and
maps its exit codes to the gate's verdict vocabulary:

- Exit 0: PASS, the block matches the store.
- Exit 1: FAIL, the block is stale (drift detected).
- Exit 2: CANNOT MEASURE, the intent store is absent.

The exit-2 path is new: `render_todo.py` previously exited 1 when the store
was absent, which would FAIL every CI runner that lacks `~/.intent/intent.db`.
The fix adds a store-presence check before the `check` logic and returns 2
with a "CANNOT MEASURE" message, so the gate reports N/A rather than FAIL on
runners without the store.

## Scope

- `tools/intent/render_todo.py`: exit 2 when store absent (check only),
  selftest updated to verify exit code 2
- `tools/gate/gate.py`: `todo_inbox` builtin, registered in `BUILTINS`
- `quality-contract.json`: `todo_inbox` domain entry

## Design decisions

- The builtin is named `todo_inbox` rather than `render_todo` to avoid a
  naming collision with the module it imports.
- Only the `check` command gets the exit-2 path. `write` and `list` still
  treat an absent store as an empty result, which is their correct behavior
  (writing "no prompt tickets" is accurate when there is no store).
- The store-presence check duplicates the path logic from `load()` rather
  than adding a return value to it, because `load()` is also called by
  `write` and `list` where an absent store is not an error.

## Non-goals

- Enforcing that prompts are triaged within a time window. The inbox is a
  visibility tool, not a triage deadline.
- Running `render_todo.py write` automatically when drift is detected. The
  gate reports the problem; the operator or a session runs the fix.
