---
name: elevenlabs-mcp
description: Use ElevenLabs MCP for TTS/audio-generation tools in on-demand agent sessions.
---

## When to use
- You need ElevenLabs TTS/audio tooling through MCP.
- You need audio tooling enabled only during the active task.

## Activation (On-Demand)
1) Ensure `ELEVENLABS_API_KEY` is set.
2) Start Codex with ElevenLabs MCP enabled:
   - `~/.codex/bin/codex-with-mcp elevenlabs`
   - With HeyGen: `~/.codex/bin/codex-with-mcp heygen elevenlabs`
3) Verify registration/status: `codex mcp get elevenlabs --json`
4) Optional smoke test: `~/.codex/bin/mcp-smoke-check`

## Notes
- Global config runs `uvx elevenlabs-mcp` with env-backed key injection.
- For long-running audio workflows, monitor latency and credit consumption.
