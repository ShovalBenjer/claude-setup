---
name: cdp
description: Kickstart browser CDP for UI inspection / scraping. On Windows, the live profile is native Chrome on port 9224. Under WSL, defaults to Obscura (9222); pass "edge" for the Windows-side Edge bridge (9223, for Entra/domain apps).
---

# /cdp — Kickstart browser CDP for UI work

**Args:** `$ARGUMENTS` — empty (auto-detect the live endpoint), or `edge` (Windows-side MS Edge), or `status` (health check every port), or `stop` (tear down Obscura; Edge and native Chrome stay up).

## Find the live endpoint first

Three different browsers can be listening, on three ports, and which ones exist
depends on whether this session is win32 or WSL. Probe before assuming: the
Obscura and Edge flows below are WSL-shaped and their launcher
(`~/.codex/bin/obscura-cdp`) is not present on a native Windows session, so
following them there produces "no browser" on a machine where a browser is in
fact running.

| Port | What it is | Driver |
|---|---|---|
| 9224 | **Native Windows Chrome automation profile. On win32 this is normally the only one up.** | `cdp_driver.py` (in new-recruit), or raw CDP over the websocket URL |
| 9222 | Obscura stealth Chromium, WSL only | `playwright-obscura` MCP |
| 9223 | MS Edge bridge, for Entra/SSO/domain apps | `playwright-edge` MCP |

### Port 9224 — native Windows Chrome

**Resolve the address first, do not assume `127.0.0.1`.** IPv4 and IPv6 loopback
are separate sockets on Windows, so two unrelated Chrome instances can both hold
port 9224 and neither reports a conflict. That happened on 2026-07-27: a
throwaway profile under `Temp` held `127.0.0.1:9224` and the automation profile
held `[::1]:9224`, so `curl 127.0.0.1` answered with a valid payload from the
browser nobody meant to drive. Reachability is not identity.

```bash
CDP_PORT=9224 python ~/claude-setup/tools/browser/cdp.py status
```

That prints the address whose listening socket is owned by a Chrome running the
automation profile, warns when a second browser also answers on the port, and
refuses rather than adopting a stranger. Use the host it names below:

```bash
H='[::1]'                                      # whatever status resolved
curl -fsS http://$H:9224/json/version          # browser build
curl -fsS http://$H:9224/json/list             # open tabs
curl -fsS -X PUT "http://$H:9224/json/new?url=https%3A%2F%2Fexample.com"
curl -fsS "http://$H:9224/json/activate/<targetId>"
```

Anything that reads or drives a page needs a websocket. Use the repo driver,
which supplies its own dependency per invocation:

```bash
cd ~/Downloads/new-recruit
CDP_TAB=<url-substring> uv run --with websocket-client python cdp_driver.py url
CDP_TAB=<url-substring> uv run --with websocket-client python cdp_driver.py text
CDP_TAB=<url-substring> uv run --with websocket-client python cdp_driver.py shot out.png
```

Two things that will otherwise cost a debugging round:

- `CDP_TAB` substring-matches the tab URL. With no match it silently falls back
  to the first page, which is usually not the tab you meant. Open a new tab with
  `/json/new` rather than navigating whatever the user already had open.
- `Page.captureScreenshot` hangs on a background tab, because Chrome does not
  render one. Call `/json/activate/<targetId>` first, then screenshot.

If 9224 is down, launch it on the Windows side:

```powershell
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  -ArgumentList @(
    "--remote-debugging-port=9224",
    "--user-data-dir=C:\Users\shova\AppData\Local\Google\Chrome\CDP-Profile"
  )
```

The Claude-in-Chrome MCP tools (`mcp__claude-in-chrome__*`) are a separate path
and do not use any of these ports. When they report "Browser extension is not
connected", that says nothing about CDP — probe the ports before concluding
there is no browser.

## Default flow — Obscura (Linux, stealth Chromium)

This is the right choice for: public web scraping and anti-bot pages where stealth matters more than pixel capture. For visual inspection, screenshots, layout defects, RTL review, or user-reported UI bugs, use the default `playwright` MCP server instead; it launches normal Chrome through `/home/shovalbe/.codex/bin/playwright-mcp-visual`.

```bash
~/.codex/bin/obscura-cdp start
```

The script is idempotent — it health-checks `http://127.0.0.1:9222/json/version` first and only spawns Obscura if it's down. After start:

```bash
curl -fsS http://127.0.0.1:9222/json/version | head -c 300
```

Should return JSON with `Browser`, `webSocketDebuggerUrl`, etc. If yes, the `playwright-obscura` MCP server is usable. Tell the user the endpoint is live for stealth browsing, but do not present it as visual proof when screenshots are required.

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
    "--user-data-dir=C:\Users\shoval.be\AppData\Local\Microsoft\Edge\CDP-Profile",
    "https://comp-widgora-prod-b0emf3hyefetcken.swedencentral-01.azurewebsites.net/calendars"
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

## `$ARGUMENTS = status` — every port, both sides

```bash
# Assign, then test. `curl ... | head` reports head's exit status, which is 0
# even when curl could not connect, so a piped `|| echo DOWN` never fires and
# every port silently looks the same as a live one.
probe() {
  if out=$(curl -fsS --max-time 2 "$2/json/version" 2>/dev/null); then
    printf '%s -- UP: %s\n' "$1" "$(printf '%s' "$out" | tr -d '\n' | cut -c1-90)"
  else
    printf '%s -- DOWN\n' "$1"
  fi
}

# 127.0.0.1 on win32; the host gateway address only exists under WSL.
WIN_HOST=127.0.0.1
command -v ip >/dev/null 2>&1 && WIN_HOST="$(ip route show default | awk '{print $3}')"

probe "native Chrome  9224" "http://127.0.0.1:9224"
probe "Obscura        9222" "http://127.0.0.1:9222"
probe "Edge           9223" "http://${WIN_HOST}:9223"
```

Report which ports answered. Do not report "no browser available" unless all
three are down: on win32, 9222 and 9223 being down is the normal state and 9224
is the one that matters.

## `$ARGUMENTS = stop` — tear down Obscura only

```bash
~/.codex/bin/obscura-cdp stop
```

Edge stays up — closing it is the user's call (it's a Windows-side process under their control).

## Pick the right side

| Target | Use |
|---|---|
| Visual QA, screenshots, layout/RTL bugs, console/network review | Playwright Chrome (`playwright`) |
| Public web scraping where stealth matters more than screenshots | Obscura (`playwright-obscura`) |
| `*.i-sdd.com`, Azure portal, ADO web UI, Widgora prod, anything Entra/SSO | Edge (`playwright-edge`) |
| Anti-bot test (Cloudflare, Akamai etc.) | Obscura (stealth-mode is its purpose) |
| Domain-joined intranet sites | Edge (Windows session has the kerberos/NTLM auth) |

After kickstart, stealth browser automation flows through the `playwright-obscura` MCP server. Visual browser automation flows through the default `playwright` MCP server, which uses normal Chrome and supports screenshots. Windows Edge automation flows through `playwright-edge`, which attaches to `http://<windows-host>:9223`.
