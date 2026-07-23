# A6. News Feed -> Stack-Relevant Digest

Schedule: Sundays 6:00 PM
Repo root: latest news ingestion output
Mode: read + summary file

Read news ingested in the last 7 days. Filter to items mentioning:

- Anthropic: Claude Code, Claude API, Claude model releases, MCP.
- Microsoft Agent Framework, Semantic Kernel deprecation, AutoGen.
- Azure AI Foundry, Azure Functions, Azure Container Apps, Azure DevOps.
- Ink, React for terminal, Bubbletea, cmux, OpenTUI, OpenCode.
- Catppuccin, Nord palette updates.
- TypeScript, Bun runtime updates.
- HeyGen V3, per `project_siu_heygen_aca.md`.
- Chatwoot, Telegram Bot API, WhatsApp Business API.
- OpenSSL, Node.js, libraries appearing in local `package.json` files.

For each match:

- 2-line summary.
- 1-line implication for our stack, citing which project.
- Action if any, for example `upgrade Ink to v6 in .claude-ink-tui`.

Output `~/.claude/docs/NEWS_DIGEST_<DATE>.md`, sorted by implication strength: `HIGH`, `MEDIUM`, `LOW`.

High-impact items should be noted in a `SessionStart banner` section in the report so the next session can surface them.
