---
name: azure-keyvault-secrets
description: Sync MCP/project secrets from Azure Key Vault for Codex sessions.
---

## Purpose
Provide one formal secrets path for global + SIU + figma-4-all when running Codex.

## Commands
- Auto scope, MCP keys: `~/.Codex/bin/Codex-secrets-sync --project auto --mcp-only`
- SIU scope: `~/.Codex/bin/Codex-secrets-sync --project siu`
- figma scope: `~/.Codex/bin/Codex-secrets-sync --project figma4all`

## Files
- `~/.Codex/secrets/keyvault.conf`
- `~/.Codex/secrets/global.map`
- `projects/social-intelligence-unit/.Codex/secrets.map`
- `projects/figma-4-all/.Codex/secrets.map`

## Notes
- `~/.Codex/bin/perplexity-mcp-launch` lazily calls secret sync if `PERPLEXITY_API_KEY` is missing.
- This wrapper delegates to `~/.codex/bin/codex-secrets-sync` for one source of truth.
