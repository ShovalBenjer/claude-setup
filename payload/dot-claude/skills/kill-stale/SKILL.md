---
name: kill-stale
description: "/kill-stale"
allowed-tools: ["Bash", "Read"]
---

# /kill-stale

Find and kill hanging MCP servers, language servers, and orphaned dev processes.

## Trigger

User invokes `/kill-stale` or asks about hanging/stale processes.

## Steps

1. **Detect** stale processes:
```bash
ps aux | grep -iE 'mcp|playwright.*mcp|perplexity.*mcp|typescript-language-server|tsserver|eslintServer|kilo.*server' | grep -v grep
```

2. **Report** findings as a table: Process, PID, Age, Memory (RSS)

3. **Ask user** for confirmation before killing

4. **Kill** confirmed processes:
```bash
kill <pids>
```

5. **Verify** they're gone:
```bash
ps aux | grep -iE 'mcp|tsserver|eslintServer' | grep -v grep
```

## Known stale patterns

- Duplicate Playwright MCP instances (>1 is always stale)
- Kilo language servers (`kilo x typescript-language-server`, `tsserver`, `eslintServer`) — safe to kill, Kilo respawns on demand
- Any MCP process older than 2 hours with no active Claude session

## Rules

- Always confirm before killing
- Never kill PID 1 or system processes
- Report memory freed (sum RSS of killed processes)
