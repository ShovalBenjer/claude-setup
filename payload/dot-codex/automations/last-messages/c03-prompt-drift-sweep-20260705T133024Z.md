Completed the sweep and wrote the report here:

[.claude/docs/PROMPT_DRIFT_2026-07-05.md](/home/shovalbe/.claude/docs/PROMPT_DRIFT_2026-07-05.md)

Key outcomes:
- Found drift in CS prompt source-of-truth: shared `v110.2` differs from active CS repo `v110.2`.
- Campaign deploy defaults to `agent_prompt_v16.txt`, but CI still references missing `agent_prompt_v14.txt` and `call_analyzer_openapi.json`.
- Live Foundry metadata check was blocked by Azure token refresh/DNS for `login.microsoftonline.com`.
- Created one Hive bead: `#155` P3, `Archive stale shared prompt README and unreferenced drafts`.
- Did not edit prompt files, deploy prompts, create ADO work items, or print secrets/prompt bodies.

Verification: report has all required sections, 176 lines, and Hive DB confirms bead `155|cs-agent|P3|open`.

