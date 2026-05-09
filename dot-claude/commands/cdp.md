---
name: cdp
description: Kickstart browser CDP for UI inspection / scraping. Defaults to Obscura on Linux (port 9222). Pass "edge" for the Windows-side Edge bridge (port 9223, for Entra/domain apps).
---

# /cdp — Kickstart browser CDP for UI work

**Args:** `$ARGUMENTS` — empty (default Obscura), or `edge` (Windows-side MS Edge), or `status` (health check both), or `stop` (tear down Obscura; Edge stays up).

## Default flow — Obscura (Linux, stealth Chromium)

This is the right choice for: public web scraping, your own UI testing, screenshots, anti-bot pages. **Use this unless the target requires Windows SSO / Entra / domain join.**

```bash
~/.codex/bin/obscura-cdp start
```

The script is idempotent — it health-checks `http://127.0.0.1:9222/json/version` first and only spawns Obscura if it's down. After start:

```bash
curl -fsS http://127.0.0.1:9222/json/version | head -c 300
```

Should return JSON with `Browser`, `webSocketDebuggerUrl`, etc. If yes, the `playwright` MCP server (already in `~/.mcp.json` as `playwright-mcp-obscura`) is usable. Tell the user the endpoint is live and you're ready to drive the browser.

If `curl` returns connection refused or empty, run:

```bash
~/.codex/bin/obscura-cdp status
```

For verbose state. If genuinely broken, check `/tmp/obscura-cdp-9222.log`.

## `$ARGUMENTS = edge` — Windows-side MS Edge

For: anything requiring Windows SSO, Entra ID, Windows Hello, domain-joined SaaS, internal corp apps. Edge runs on the Windows host; WSL talks to its CDP via the host gateway.

### Step 1: probe whether Edge CDP is already running

```bash
WIN_HOST="$(ip route show default | awk '{print $3}')"
ENDPOINT="http://${WIN_HOST}:9223/json/version"
if curl -fsS --max-time 1 "$ENDPOINT" >/dev/null 2>&1; then
  echo "Edge CDP already up at $ENDPOINT"
  curl -fsS "$ENDPOINT" | head -c 300
else
  echo "Edge CDP not reachable. Run the PowerShell command below on Windows:"
fi
```

### Step 2: if down, print the exact PowerShell command for the user to run

Print verbatim and ask the user to run it on Windows side, then re-run `/cdp edge` to verify:

```powershell
Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  -ArgumentList @(
    "--remote-debugging-port=9223",
    "--remote-debugging-address=0.0.0.0",
    "--user-data-dir=C:\Users\shoval.be\AppData\Local\Microsoft\Edge\CDP-Profile"
  )
```

**Why each flag:**
- `--remote-debugging-port=9223` — separate from Obscura's 9222 so both can run side-by-side
- `--remote-debugging-address=0.0.0.0` — required for WSL→host reachability (single-user dev box only; for shared hosts use `127.0.0.1` + `socat` tunnel)
- `--user-data-dir=...\CDP-Profile` — separate profile so CDP automation doesn't fight the user's daily Edge windows

### Step 3 (optional): if the user has firewall pain

WSL2 can't reach Windows ports if Windows Defender Firewall blocks them. Tell the user:

```powershell
# As Administrator
New-NetFirewallRule -DisplayName "WSL Edge CDP" -Direction Inbound -Protocol TCP -LocalPort 9223 -Action Allow
```

Or, tighter: use `socat TCP-LISTEN:9223,fork TCP:127.0.0.1:9223` from PowerShell-as-admin to tunnel localhost-only Edge to WSL.

## `$ARGUMENTS = status` — both sides health check

```bash
echo "=== Obscura (Linux, port 9222) ==="
curl -fsS --max-time 1 http://127.0.0.1:9222/json/version 2>&1 | head -c 200 || echo "DOWN"
echo ""
echo "=== Edge (Windows, port 9223) ==="
WIN_HOST="$(ip route show default | awk '{print $3}')"
curl -fsS --max-time 1 "http://${WIN_HOST}:9223/json/version" 2>&1 | head -c 200 || echo "DOWN — run /cdp edge to get the launch command"
```

## `$ARGUMENTS = stop` — tear down Obscura only

```bash
~/.codex/bin/obscura-cdp stop
```

Edge stays up — closing it is the user's call (it's a Windows-side process under their control).

## Pick the right side

| Target | Use |
|---|---|
| Public web, your own UI, scraping, screenshots | Obscura (default) |
| `*.i-sdd.com`, Azure portal, ADO web UI, anything Entra/SSO | Edge |
| Anti-bot test (Cloudflare, Akamai etc.) | Obscura (stealth-mode is its purpose) |
| Domain-joined intranet sites | Edge (Windows session has the kerberos/NTLM auth) |

After kickstart, browser automation flows through the `playwright` MCP server (Obscura) or `playwright-edge` MCP server (Edge — once wired per master plan items 10-12).
