---
name: apify-mcp
description: Use Apify MCP for actor discovery, execution, and dataset retrieval in scraping/ingestion workflows.
---

## When to use
- You need Apify Actor search, invocation, or run/dataset retrieval from an MCP-capable agent.
- You need on-demand scraping tools without enabling unrelated MCP servers.

## Activation (On-Demand)
1) Ensure `APIFY_API_KEY` is set.
2) Start Codex with Apify enabled:
   - `~/.codex/bin/codex-with-mcp apify`
   - With research: `~/.codex/bin/codex-with-mcp apify perplexity`
3) Verify registration/status: `codex mcp get apify --json`
4) Optional smoke test: `~/.codex/bin/mcp-smoke-check`

## Notes
- Global config uses streamable HTTP `https://mcp.apify.com` with bearer token env var.
- For production, restrict tools via URL query params where possible.
- Watch Apify rate limits and keep runs bounded.
