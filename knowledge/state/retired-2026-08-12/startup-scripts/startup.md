# Startup Prompt (Local MCP + Codex Desktop Connector)

Use this prompt in Codex Desktop at session start:

```md
You are in `/home/shovalbe/projects/campaign-analysis`.
Goal: run the local MCP server for connector testing and verify it is reachable.

Do exactly this:

1) Install deps:
- `uv sync --extra mcp`

2) Start local server prerequisites:
- Generate signing key:
  - `export MCP_OAUTH_SIGNING_KEY=$(openssl rand -base64 32)`
- For local dev mode, make sure Entra vars are unset:
  - `unset MCP_ENTRA_TENANT_ID MCP_ENTRA_APP_CLIENT_ID MCP_ENTRA_APP_CLIENT_SECRET`

3) Run server:
- `uv run uvicorn app_mcp.server:app --host 0.0.0.0 --port 8787 --reload`

4) Expose HTTPS URL (required by most desktop connector flows):
- In a second terminal, run:
  - `cloudflared tunnel --url http://127.0.0.1:8787`
  - (or `ngrok http 8787`)
- Copy the public `https://...` URL.

5) Restart server with issuer set to the public URL:
- `export MCP_OAUTH_ISSUER=<PUBLIC_HTTPS_URL>`
- Re-run:
  - `uv run uvicorn app_mcp.server:app --host 0.0.0.0 --port 8787 --reload`

6) Verify endpoints:
- `curl <PUBLIC_HTTPS_URL>/.well-known/oauth-authorization-server`
- `curl -i <PUBLIC_HTTPS_URL>/sse` (expect `401`)
- `curl -X POST <PUBLIC_HTTPS_URL>/oauth/register -H "Content-Type: application/json" -d '{"redirect_uris":["https://cb"],"client_name":"local-smoke"}'`

7) Connector setup in Codex Desktop:
- Add custom MCP connector using `<PUBLIC_HTTPS_URL>`.
- Save.
- If Entra vars are unset, auth runs in dev mode.
- If Entra vars are set, expect Microsoft sign-in popup.

8) If anything fails, print:
- server logs,
- tunnel URL,
- outputs of the 3 curl checks above,
- and a short diagnosis.
```

