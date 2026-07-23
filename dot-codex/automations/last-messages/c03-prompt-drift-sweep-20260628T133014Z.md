Completed the C3 prompt drift sweep.

Report written: [.claude/docs/PROMPT_DRIFT_2026-06-28.md](/home/shovalbe/.claude/docs/PROMPT_DRIFT_2026-06-28.md)

Key outcomes:
- Found CS scheduled path missing; inspected active Hive rig path `/home/shovalbe/projects/axia-seekapa-cs-agents`.
- Found concrete `v110.2` Seekapa prompt drift between shared library and CS repo.
- Found stale prompt README/version guidance in both shared and CS prompt docs.
- Campaign Analysis prompt source is locally traceable to `agent_prompt_v16.txt`, but live parity/eval/rollback evidence is incomplete.
- Live Foundry metadata GET was attempted but failed with `URLError`, so runtime parity remains unverified.
- Created Hive beads `#133` and `#134`, both P2.

Verification included report section check and file existence check; the only new file is the report.

