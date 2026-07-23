Completed the scheduled engineering review sweep.

Report written to:
`/home/shovalbe/.claude/docs/ENGINEERING_REVIEW_2026-06-24.md`

Created local Hive beads:
- `#121` `video-understanding` P3: generated Remotion deps/artifacts polluting review surface
- `#122` `campaign-analysis` P3: repo-root home-style/generated artifact sprawl

Key blocker recorded in the report: Azure DevOps remote coverage was blocked by DNS/network resolution for `dev.azure.com`, so PR/remote branch/pipeline checks could not be verified live.

Verification:
- Report exists: `192` lines
- Required sections and bead ids verified with `rtk rg`
- Static checks recorded: CS lint path failed, video ruff passed, campaign MCP ruff passed, campaign frontend lint blocked by interactive Next ESLint setup

