Completed the unattended sweep.

Report written: [PROMPT_DRIFT_2026-06-07.md](/home/shovalbe/.claude/docs/PROMPT_DRIFT_2026-06-07.md)

Created Hive beads:
- `58` `campaign-analysis` P2: clarify Call-analyser-agent canonical prompt and live MCP state
- `59` `cs-agent` P2: reconcile Seekapa v110.2 prompt source drift

Key result: live Foundry metadata was blocked by DNS failure for `brn-azai.services.ai.azure.com`, but local drift was still confirmed. The strongest finding is that shared and project copies of `seekapa-system-prompt-v110.2-yasha-conversational.md` differ by hash/size, while project docs say the project copy mirrored live `seekapa:117`.

Verification included section checks, leak scan, prompt hash/size comparison, env/auth state, and Hive bead DB verification. No prompt files were edited and no deployment was attempted.

