---
name: cdp
description: Kickstart browser CDP for UI inspection / scraping. On Windows, the live profile is native Chrome on port 9224. Under WSL, reach that same Chrome with `winchrome` (relay on 9324, no admin and no wsl --shutdown), or use Obscura (9222) for a Linux-local Chromium; pass "edge" for the Windows-side Edge bridge (9223, for Entra/domain apps).
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

Under WSL that message has one specific cause worth knowing, because reinstalling
the extension never fixes it. The extension reaches Claude Code through Chrome
native messaging, which launches a process named by a Windows registry manifest.
Chrome is a Windows process and can only launch another Windows process, so the
stock manifest points at `claude.exe`: the extension is wired to the **Windows**
Claude Code, and a WSL session is a different process that never sees it. The
native host's actual job is to open a unix socket a session then connects to, so
the host has to run inside WSL for that socket to be reachable. `wsl-chrome-bridge`
rewrites the `.bat` to call `wsl.exe`, which hands over the raw stdio handles and
carries the 4-byte length-prefixed frames across unmodified.

```bash
wsl-chrome-bridge setup     # rewrite the .bat, symlink extension detection
wsl-chrome-bridge verify    # bat target, native host start, extension present
wsl-chrome-bridge revert    # hand the extension back to Windows Claude Code
```

Three things this cost to find out:

- On 2.1.223 the WSL block is gone. `claude --chrome-native-host` runs on Linux
  and opens `/tmp/claude-mcp-browser-bridge-$USER/<pid>.sock`. Older builds
  refused with "Claude in Chrome Native Host not supported on this platform", and
  that string is still in the binary, so treat its return as the gate coming back.
- One manifest cannot point two ways. While bridged, Claude Code on Windows loses
  the extension. That is the trade, not a defect.
- A Claude Code upgrade regenerates the `.bat` pointing back at `claude.exe`,
  which silently unbridges it. The symptom is the extension reporting "not
  connected" again with nothing naming the cause, so re-run `setup` after upgrades.

Neither restart is skippable: quit Chrome from the system tray rather than closing
the window, and start Claude Code with `--chrome`. A session already running cannot
attach, and this is the step most likely to look like the bridge failing.

What `verify` proves and what it does not. It proves the host starts and the socket
opens. It does not prove the extension connects, because that handshake only happens
after both restarts, and a session cannot restart itself to watch it. Until a session
shows `mcp__claude-in-chrome__*` tools, this is wiring-verified and handshake-unconfirmed.
If it still reports "not connected" after both restarts, check three things in order:
`wsl-chrome-bridge verify`, that `CLAUDE_CODE_OAUTH_TOKEN` is unset in the shell profile
(it forces an account mismatch), and that the extension is signed into the same claude.ai
account as Claude Code. The binary carries a distinct message for that last case, so a
generic "not connected" means it is one of the first two.

### Port 9224 from WSL: unreachable, and the firewall is not why

Everything above about 9224 assumes a win32 session. From WSL that port is up and
unreachable at the same time, which produces the most misleading probe result in
this file: `curl 127.0.0.1:9224` returns connection-refused for a browser that
answers on Windows a second later.

Two independent facts cause it, and fixing either alone changes nothing:

- Chrome binds `--remote-debugging-port` to `127.0.0.1` only.
- WSL2's default NAT networking gives WSL its own loopback, so that address is
  not the Windows one.

Measured 2026-08-06 on this machine, and it narrows the fix a lot: a listener
bound to `0.0.0.0` on Windows **is** reachable from WSL at the default-route
address, with no admin rights and no firewall prompt. So Windows Defender is not
in the way and `New-NetFirewallRule` is not needed. The only gap is Chrome's
loopback-only bind, which a userspace relay closes:

```bash
winchrome start            # chrome + relay on the Windows side, health-checked
winchrome status           # each hop separately: chrome, relay, wsl reachability
eval "$(winchrome env)"    # exports CDP_HOST and CDP_PORT
cd ~/.claude/bin
CDP_TAB=<url-substring> uv run --with websocket-client python cdp_driver.py text
```

`dot-claude/bin/cdp-relay.py` runs on the **Windows** python and forwards
`0.0.0.0:9324` to `127.0.0.1:9224`. It is a raw byte pump, so the WebSocket
upgrade passes through unchanged.

Prefer this over the two heavier options. `networkingMode=mirrored` in
`.wslconfig` also works and is supported here (build 26200, WSL 2.7.11), but it
is global to every distro and needs `wsl --shutdown`, which kills every running
session including the one that asked for a browser. `netsh portproxy` needs
admin. The relay needs neither.

Three things measured while building it, each of which would otherwise cost a
round:

- Chrome does **not** reject the relayed request. It builds
  `webSocketDebuggerUrl` from the request `Host` header, so the URL comes back
  already pointing at the relay and needs no client-side rewriting.
- Do not health-check the relay with `netstat | grep -q` under `set -o pipefail`.
  grep exits on first match, netstat dies on SIGPIPE, and the pipeline reports
  failure for a lookup that succeeded. It printed a confident `NO` beside a relay
  the next line reached over the network.
- `--remote-debugging-address=0.0.0.0` is asserted for Edge further down this
  file. It was **not** verified for Chrome here; the relay was used instead, so
  treat that flag as untested rather than as the known-good path.

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
