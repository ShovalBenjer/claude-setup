---
name: heygen-mcp
description: Use HeyGen MCP for avatar/video generation flows when agent-driven tool access is required.
---

## When to use
- You need HeyGen video/avatar operations through MCP tools.
- You want HeyGen enabled only for the current task/session.

## Activation (On-Demand)
1) Ensure `HEYGEN_API_KEY` is set.
2) Start Codex with HeyGen MCP enabled:
   - `~/.codex/bin/codex-with-mcp heygen`
   - With TTS/video stack: `~/.codex/bin/codex-with-mcp heygen elevenlabs`
3) Verify registration/status: `codex mcp get heygen --json`
4) MCP command check: `uvx heygen-mcp --help`

## Notes
- Global config runs `uvx heygen-mcp` with env-backed key injection.
- Keep generated outputs scoped to project paths and track API-credit usage.
