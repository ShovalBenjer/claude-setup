# Long checks run in the background, iteration stays foreground

Operator instruction 2026-08-12: test runs were blocking his iteration loop ("i need
to ctrl b it always"). The fix is a default, not a reminder:

- Full test suites, gate runs, mutation runs, builds, and anything expected to take
  longer than ~30 seconds run with run_in_background, and the session keeps working
  while they do. Results are collected when the task notifies, and a failure is
  reported in the next message, never silently.
- Foreground is for the tight loop only: one test file or one test id whose result
  the very next edit depends on.
- For a suite that will be needed repeatedly while iterating, prefer one background
  run per meaningful checkpoint over one per edit; a qa-lab or haiku subagent may own
  a long verification pass, but plain run_in_background is the default because it is
  cheaper than a second context.
- The same session (2026-08-12) removed the two hook costs that made this worse:
  per-turn ledger appends no longer invalidate the gate fingerprint (gate.py
  HARNESS_OUTPUTS), and an unevidenced completion claim nudges instead of blocking
  (completion_gate.py). If a Stop hook still forces a full gate rerun with no content
  change, that is a bug in the fingerprint exclusions, not a reason to gate less.
