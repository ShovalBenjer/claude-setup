---
name: mcp-activation
description: Activate only the MCP servers needed for the current Codex session.
---

## Purpose
Keep MCP exposure minimal by enabling servers per session/task instead of always-on.

## Usage
- Status: `~/.codex/bin/codex-with-mcp --status`
- Perplexity + Playwright: `~/.codex/bin/codex-with-mcp perplexity playwright`
- Apify only: `~/.codex/bin/codex-with-mcp apify`
- Video stack: `~/.codex/bin/codex-with-mcp heygen elevenlabs`
- Dry run command: `~/.codex/bin/codex-with-mcp --dry-run perplexity apify`
- Lazy Key Vault hydration (manual): `~/.codex/bin/codex-secrets-sync --project auto --mcp-only`

## Verification
- Full smoke check: `~/.codex/bin/mcp-smoke-check`
- Individual server details: `codex mcp get <server> --json`

## Policy
- Default all managed MCP servers to `enabled = false` in `~/.codex/config.toml`.
- Activate narrowly for the task, then end the session.
- `codex-with-mcp` auto-attempts lazy secret sync when required MCP env vars are missing.
