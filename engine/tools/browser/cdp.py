#!/usr/bin/env python3
"""Drive a real Chrome from the terminal over the DevTools protocol.

Why this exists. This machine has Chrome installed and a dedicated automation
profile, but no browser tool is exposed to the assistant session, so pages that
require a logged-in session were simply unreachable. WebFetch cannot see them:
it is an anonymous fetcher, so every authenticated page comes back as a login
wall or a 404. This closes that gap using nothing but the standard library.

Design notes worth knowing before you edit this.

  It launches a SEPARATE Chrome instance against its own user-data-dir. The
  operator's daily Chrome keeps running untouched, because you cannot attach a
  debugger to an already-running Chrome that was started without the flag, and
  restarting theirs to get one would throw away their open tabs.

  The WebSocket client is hand-rolled. The standard library ships no WebSocket
  client, and the alternative was a dependency for what amounts to eighty lines
  of framing. Server-to-client frames are never masked and client-to-server
  frames always are, per RFC 6455, which is why only one direction masks here.

  Fragmentation is handled because it is not optional in practice. A
  Page.captureScreenshot response is a megabyte of base64 and Chrome does split
  it across continuation frames; a reader that assumes one frame per message
  works fine on small replies and then silently truncates the interesting ones.

Subcommands:
  launch      start Chrome with the debug port, or report the one already up
  status      is the debug endpoint answering
  text URL    navigate, wait for load, print the page's visible text
  shot URL    navigate, wait for load, write a PNG so it can be looked at
  eval URL JS navigate, then evaluate an expression and print the result
  stop        kill the Chrome instance this tool launched
"""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_PORT = int(os.environ.get("CDP_PORT", "9222"))
PORT = DEFAULT_PORT

# IPv4 and IPv6 loopback are SEPARATE sockets on Windows, so two unrelated
# Chrome instances can both "listen on 9224" without either reporting a
# conflict. Measured 2026-07-27: pid 19604 held 127.0.0.1:9224 with a throwaway
# profile under Temp, pid 10396 held [::1]:9224 with this module's automation
# profile, and only the second had the Claude extension in it.
#
# The failure that costs the hour is not "connection refused". It is that
# /json/version on the hardcoded 127.0.0.1 ANSWERS, with a valid payload, from
# a browser nobody meant to drive. Reachability is therefore not identity, and
# a resolver that stops at the first endpoint that replies is choosing at
# random between two browsers. So each candidate address is checked against the
# process that owns that listening socket, and only a socket owned by a Chrome
# whose command line names our profile is adopted.
#
# "localhost" is deliberately not a candidate: it is exactly the name whose
# resolution order decides which of the two browsers you get, which is the
# ambiguity being removed here. CDP_HOST overrides for the case where someone
# really does mean a specific stack.
HOST_CANDIDATES = ("127.0.0.1", "[::1]")
# Address as the OS reports it in a listener table, keyed by URL host form.
_LISTEN_ADDR = {"127.0.0.1": "127.0.0.1", "[::1]": "::1"}
HOST = os.environ.get("CDP_HOST") or HOST_CANDIDATES[0]

HOME = os.path.expanduser("~")
PROFILE = os.path.join(HOME, ".claude", "automation-chrome-profile")
PIDFILE = os.path.join(HOME, ".claude", "automation-chrome-profile", ".cdp-launch.pid")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(HOME, r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def chrome_path() -> str:
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("chrome.exe not found in any known location")


# ---------------------------------------------------------------- HTTP side

def _endpoint(path: str, timeout: float = 3.0, host: str | None = None) -> dict | list:
    url = "http://{}:{}{}".format(host or HOST, PORT, path)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def alive(timeout: float = 1.0, host: str | None = None) -> dict | None:
    try:
        return _endpoint("/json/version", timeout=timeout, host=host)
    except Exception:
        return None


def parse_listeners(text: str, port: int) -> dict[str, int]:
    """Owning pid per local address listening on `port`.

    Input is `Get-NetTCPConnection -State Listen` rendered as text. Kept apart
    from the call that produces it so the mapping can be tested without a
    Windows box and without a live socket.
    """
    found: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        addr, lport, pid = parts[0], parts[1], parts[-1]
        if not lport.isdigit() or int(lport) != port or not pid.isdigit():
            continue
        found.setdefault(addr.strip("[]"), int(pid))
    return found


def parse_profile_pids(text: str, marker: str) -> set[int]:
    """Pids of chrome processes whose command line names `marker`.

    Input is `pid<TAB>commandline` per line. Same reason for the split: the
    parsing is the part worth testing, the subprocess call is not.
    """
    pids: set[int] = set()
    for line in text.splitlines():
        pid, _, cmd = line.partition("\t")
        if marker in cmd and pid.strip().isdigit():
            pids.add(int(pid.strip()))
    return pids


def choose_host(answered: dict[str, bool], listeners: dict[str, int],
                profile_pids: set[int]) -> tuple[str | None, str]:
    """Pick the address whose listener is OUR browser, or refuse to guess.

    `answered` says which candidate host form replied to /json/version. Pure so
    the three outcomes that matter can be asserted: a verified match, no
    endpoint at all, and the dangerous one, an endpoint owned by a stranger.
    """
    replied = [h for h in HOST_CANDIDATES if answered.get(h)]
    if not replied:
        return None, "no debug endpoint answered on {} or {}".format(*HOST_CANDIDATES)
    verified = [h for h in replied
                if listeners.get(_LISTEN_ADDR[h]) in profile_pids]
    if verified:
        note = ""
        strangers = [h for h in replied if h not in verified]
        if strangers:
            note = ("; WARNING {} also answers on this port and is a DIFFERENT "
                    "browser, not this profile".format(", ".join(strangers)))
        return verified[0], "verified against the process holding the socket" + note
    if not listeners and not profile_pids:
        # No listener table available (not Windows, or the query failed). Falling
        # back to first-answer is what this function exists to avoid, so say so.
        return replied[0], "UNVERIFIED: no listener table, adopted the first answer"
    return None, ("{} answered but the process holding that socket is not this "
                  "profile's Chrome; refusing to drive a browser nobody asked "
                  "for".format(", ".join(replied)))


def _powershell(cmd: str, timeout: int = 30) -> str:
    """Run a PowerShell query, returning "" when PowerShell cannot answer.

    The empty string is a MEANINGFUL return, not a swallowed error: it reaches
    choose_host() as an absent listener table, which downgrades the pick to
    UNVERIFIED and says so on stderr. That is the intended behaviour off Windows.
    The exception list is explicit so a genuine bug here (a bad format string, a
    quoting error building `cmd`) still raises instead of silently degrading
    every caller to the unverified path.
    """
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout).stdout
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError,
            subprocess.TimeoutExpired, UnicodeDecodeError):
        return ""


def resolve_host(port: int | None = None, verbose: bool = True) -> tuple[str | None, str]:
    """Decide which loopback address serves THIS profile's debug port."""
    port = PORT if port is None else port
    answered = {h: alive(timeout=1.0, host=h) is not None for h in HOST_CANDIDATES}
    listeners = parse_listeners(
        _powershell("Get-NetTCPConnection -State Listen -LocalPort {} | "
                    "ForEach-Object {{ \"$($_.LocalAddress) $($_.LocalPort) "
                    "$($_.OwningProcess)\" }}".format(port)), port)
    profile_pids = parse_profile_pids(
        _powershell("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                    "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"),
        "automation-chrome-profile")
    host, why = choose_host(answered, listeners, profile_pids)
    if verbose:
        print("cdp: port {} -> {} ({})".format(port, host or "NONE", why), file=sys.stderr)
    return host, why


def _running_debug_ports() -> list[int]:
    """Debug ports of Chrome processes already using our automation profile.

    This exists because of a Chrome behaviour that costs an hour if you have not
    hit it before: a second chrome.exe pointed at a user-data-dir that is
    already open does not start a browser. It hands its arguments to the running
    instance and exits, so --remote-debugging-port=9222 is silently discarded
    and the process you launched is gone. The port the profile is actually
    serving is whatever the FIRST instance was given, so it has to be read off
    that process rather than assumed.
    """
    ports: list[int] = []
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
             "ForEach-Object { $_.CommandLine }"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ports
    for line in out.splitlines():
        if "automation-chrome-profile" not in line:
            continue
        marker = "--remote-debugging-port="
        if marker not in line:
            continue
        tail = line.split(marker, 1)[1]
        digits = ""
        for ch in tail:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits and int(digits) not in ports:
            ports.append(int(digits))
    return ports


def launch(wait_s: float = 25.0) -> dict:
    """Bring the debug endpoint up, idempotently.

    Order matters: adopt a live endpoint, then adopt a live-but-differently-
    ported one, and only spawn as a last resort. Spawning when the profile is
    already open is the one case that looks like a launch failure but is not.
    """
    global PORT, HOST
    host, why = resolve_host(verbose=False)
    if host:
        HOST = host
        got = alive()
        if got:
            if "WARNING" in why or "UNVERIFIED" in why:
                print("note: {}".format(why), file=sys.stderr)
            return got
    elif "not this profile" in why:
        # Something is on the port and it is not ours. Silently spawning here
        # would leave two browsers on one port, which is the state that
        # produced this check in the first place.
        raise SystemExit("cdp: {}".format(why))
    for candidate in _running_debug_ports():
        if candidate == PORT:
            continue
        PORT = candidate
        host, _ = resolve_host(candidate, verbose=False)
        HOST = host or HOST
        got = alive(timeout=2.0)
        if got:
            print("note: adopted the Chrome already serving this profile on port "
                  "{}".format(PORT), file=sys.stderr)
            return got
    PORT = DEFAULT_PORT
    exe = chrome_path()
    os.makedirs(PROFILE, exist_ok=True)
    args = [
        exe,
        "--remote-debugging-port={}".format(PORT),
        "--user-data-dir={}".format(PROFILE),
        # A brand-new profile otherwise burns the first navigation on a welcome
        # page and a default-browser prompt, which reads as a page-load failure.
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate",
        "--window-size=1400,1800",
        "about:blank",
    ]
    proc = subprocess.Popen(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    with open(PIDFILE, "w", encoding="utf-8") as fh:
        fh.write(str(proc.pid))
    deadline = time.time() + wait_s
    while time.time() < deadline:
        got = alive()
        if got:
            return got
        time.sleep(0.4)
    raise SystemExit("chrome did not open the debug port within {:.0f}s".format(wait_s))


def new_tab(url: str) -> dict:
    """Open a tab. Recent Chrome requires PUT on /json/new and 405s a GET, so
    the PUT is tried first and the GET is kept only as a fallback for older
    builds rather than the other way round."""
    target = "/json/new?" + urllib.parse.quote(url, safe=":/?&=#%")
    req = urllib.request.Request("http://{}:{}{}".format(HOST, PORT, target), method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError:
        return _endpoint(target, timeout=10)


def close_tab(tid: str) -> None:
    try:
        _endpoint("/json/close/" + tid, timeout=5)
    except Exception:
        pass


# ----------------------------------------------------------- WebSocket side

def split_ws_url(url: str) -> tuple[str, int, str]:
    """Split ws://HOST:PORT/PATH into (host, port, path), IPv6 included.

    An IPv6 literal is bracketed in a URL and must be UNbracketed for
    socket.create_connection, which wants the bare address. The Host header
    wants it bracketed again (see ws_host_header), so the two forms are kept
    apart rather than one being reused for both.
    """
    assert url.startswith("ws://"), url
    rest = url[len("ws://"):]
    hostport, _, path = rest.partition("/")
    if hostport.startswith("["):
        host, _, tail = hostport[1:].partition("]")
        port = tail.lstrip(":")
    else:
        host, _, port = hostport.partition(":")
    return host, int(port or 80), path


def ws_host_header(host: str, port: int) -> str:
    """Host header value: IPv6 literals go back in brackets, per RFC 3986."""
    literal = "[{}]".format(host) if ":" in host else host
    return "{}:{}".format(literal, port)



class WS:
    """The smallest WebSocket client that can carry CDP correctly.

    Only what CDP needs: a text channel, client frames masked, server frames
    reassembled across continuations, ping answered so the connection is not
    dropped mid-screenshot.
    """
    # URL parsing lives in split_ws_url below, because `hostport.partition(":")`
    # on ws://[::1]:9224/... yields host='[' and port=':1]:9224'. That went
    # unnoticed for as long as every endpoint was hardcoded to 127.0.0.1; the
    # moment the HTTP layer started resolving to IPv6 correctly, every websocket
    # command in this file broke at once.

    def __init__(self, url: str, timeout: float = 60.0):
        host, port, path = split_ws_url(url)
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            "GET /{} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).format(path, ws_host_header(host, port), key)
        self.sock.sendall(handshake.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise SystemExit("websocket handshake closed early")
            buf += chunk
        head, _, tail = buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise SystemExit("websocket handshake refused: " + head.split(b"\r\n")[0].decode())
        self.buf = tail
        self.next_id = 0
        # CDP interleaves unsolicited events with command replies. The original
        # version of call() dropped them, which is fine for "fetch me this page"
        # and useless for testing: a console exception and a failed request are
        # events, and they are exactly what a flow audit is looking for. So they
        # are kept here instead, and a caller that enabled Runtime/Network/Log
        # reads them out of this list.
        self.events: list[dict] = []

    # -- framing

    def _recv_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self.buf)))
            if not chunk:
                raise SystemExit("websocket closed while reading")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _recv_frame(self) -> tuple[int, bool, bytes]:
        b0, b1 = self._recv_exact(2)
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        length = b1 & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]
        # A server frame must not be masked, so no unmasking path is needed.
        payload = self._recv_exact(length) if length else b""
        return opcode, fin, payload

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 1 << 16:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _recv_message(self) -> str:
        parts: list[bytes] = []
        while True:
            opcode, fin, payload = self._recv_frame()
            if opcode == 0x9:            # ping: answer or the peer hangs up
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:            # pong
                continue
            if opcode == 0x8:
                raise SystemExit("websocket closed by chrome")
            parts.append(payload)
            if fin:
                return b"".join(parts).decode("utf-8", "replace")

    # -- CDP

    def call(self, method: str, params: dict | None = None, timeout_s: float = 60.0) -> dict:
        self.next_id += 1
        mid = self.next_id
        self._send_frame(0x1, json.dumps(
            {"id": mid, "method": method, "params": params or {}}).encode())
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            msg = json.loads(self._recv_message())
            # CDP interleaves unsolicited events with replies. Anything that is
            # not the reply to this id is an event: keep it, do not drop it.
            if msg.get("id") != mid:
                if "method" in msg:
                    self.events.append(msg)
                continue
            if "error" in msg:
                raise SystemExit("CDP {} failed: {}".format(method, msg["error"]))
            return msg.get("result", {})
        raise SystemExit("CDP {} timed out".format(method))

    def pump(self, seconds: float) -> None:
        """Read events for a fixed window without issuing a command.

        Needed because events arrive on their own schedule: a page can throw
        200ms after readyState goes complete, and if nothing is reading the
        socket at that moment the exception is still in the kernel buffer when
        the audit decides the page was clean. Sending a cheap no-op command
        would also work, but this does not perturb the page.
        """
        end = time.time() + seconds
        original = self.sock.gettimeout()
        try:
            while True:
                left = end - time.time()
                if left <= 0:
                    return
                self.sock.settimeout(left)
                try:
                    msg = json.loads(self._recv_message())
                except (socket.timeout, TimeoutError):
                    return
                except (OSError, ValueError):
                    return
                if "method" in msg:
                    self.events.append(msg)
        finally:
            try:
                self.sock.settimeout(original)
            except OSError:
                pass

    def take_events(self, *names: str) -> list[dict]:
        """Events seen so far, optionally filtered by CDP method name."""
        if not names:
            return list(self.events)
        want = set(names)
        return [e for e in self.events if e.get("method") in want]

    def close(self) -> None:
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# ------------------------------------------------------------------ actions

READY_JS = "document.readyState"

# Visible text, not innerText of body, because innerText on body drags in
# script and style content on some pages and loses the heading structure that
# makes the dump readable.
TEXT_JS = r"""
(() => {
  const skip = new Set(['SCRIPT','STYLE','NOSCRIPT','SVG','TEMPLATE']);
  const out = [];
  const walk = (n) => {
    if (n.nodeType === 3) {
      const t = n.nodeValue.replace(/\s+/g, ' ').trim();
      if (t) out.push(t);
      return;
    }
    if (n.nodeType !== 1) return;
    if (skip.has(n.tagName)) return;
    const cs = getComputedStyle(n);
    if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return;
    const block = cs && /^(block|flex|grid|list-item|table|table-row)$/.test(cs.display);
    if (block && out.length && out[out.length-1] !== '\n') out.push('\n');
    for (const c of n.childNodes) walk(c);
    if (block && out.length && out[out.length-1] !== '\n') out.push('\n');
  };
  walk(document.body);
  return (document.title + '\n' + '='.repeat(60) + '\n' + out.join(' '))
    .replace(/ ?\n ?/g, '\n').replace(/\n{3,}/g, '\n\n');
})()
""".strip()


def _attach(url: str, settle_s: float = 2.5) -> tuple[WS, str]:
    launch()
    tab = new_tab(url)
    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise SystemExit("tab has no webSocketDebuggerUrl: " + json.dumps(tab)[:300])
    ws = WS(ws_url)
    ws.call("Page.enable")
    ws.call("Runtime.enable")
    deadline = time.time() + 30
    while time.time() < deadline:
        res = ws.call("Runtime.evaluate", {"expression": READY_JS, "returnByValue": True})
        if res.get("result", {}).get("value") == "complete":
            break
        time.sleep(0.5)
    # Client-rendered pages finish loading before they finish painting, so a
    # short settle beats reading an empty shell.
    time.sleep(settle_s)
    return ws, tab["id"]


def cmd_text(url: str) -> int:
    ws, tid = _attach(url)
    try:
        res = ws.call("Runtime.evaluate", {"expression": TEXT_JS, "returnByValue": True})
        cur = ws.call("Runtime.evaluate",
                      {"expression": "location.href", "returnByValue": True})
        print("URL: {}".format(cur.get("result", {}).get("value")))
        print(res.get("result", {}).get("value") or "(no text extracted)")
    finally:
        ws.close()
        close_tab(tid)
    return 0


def cmd_shot(url: str, out: str) -> int:
    ws, tid = _attach(url)
    try:
        res = ws.call("Page.captureScreenshot",
                      {"format": "png", "captureBeyondViewport": True}, timeout_s=90)
        data = res.get("data")
        if not data:
            raise SystemExit("no screenshot data returned")
        raw = base64.b64decode(data)
        with open(out, "wb") as fh:
            fh.write(raw)
        cur = ws.call("Runtime.evaluate",
                      {"expression": "location.href", "returnByValue": True})
        print("URL: {}".format(cur.get("result", {}).get("value")))
        print("wrote {} ({} bytes)".format(out, len(raw)))
    finally:
        ws.close()
        close_tab(tid)
    return 0


def cmd_eval(url: str, js: str) -> int:
    ws, tid = _attach(url)
    try:
        res = ws.call("Runtime.evaluate",
                      {"expression": js, "returnByValue": True, "awaitPromise": True})
        print(json.dumps(res.get("result", {}).get("value"), indent=1, ensure_ascii=False))
    finally:
        ws.close()
        close_tab(tid)
    return 0


def cmd_selftest() -> int:
    """Assert the endpoint-identity logic, with no browser and no network.

    Self-contained on purpose: tools/audit/mutate.py runs this verb against a
    MUTATED COPY of this file, so a check that reached out to the real module or
    to tests/ would keep passing while the copy was broken.
    """
    ours, stranger = 4242, 9999
    fails: list[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            fails.append("{}: got {!r}, want {!r}".format(name, got, want))

    check("listeners map address to pid",
          parse_listeners("127.0.0.1 9224 19604\n::1 9224 10396\n", 9224),
          {"127.0.0.1": 19604, "::1": 10396})
    check("listeners ignore other ports",
          parse_listeners("127.0.0.1 9222 111\n::1 9224 222\n", 9224), {"::1": 222})
    check("profile pids select on the marker",
          parse_profile_pids("10396\tchrome --user-data-dir=x/automation-chrome-profile\n"
                             "19604\tchrome --user-data-dir=x/cdp-prof-v2tree\n",
                             "automation-chrome-profile"), {10396})

    host, why = choose_host({"[::1]": True}, {"::1": ours}, {ours})
    check("ours is adopted", host, "[::1]")

    # The live defect: both answer, one is a stranger.
    host, why = choose_host({"127.0.0.1": True, "[::1]": True},
                            {"127.0.0.1": stranger, "::1": ours}, {ours})
    check("the stranger is not chosen", host, "[::1]")
    if "WARNING" not in why:
        fails.append("a second browser on the same port was not reported: " + why)

    # Reachable is not ours.
    host, why = choose_host({"127.0.0.1": True}, {"127.0.0.1": stranger}, {ours})
    check("an answering stranger is refused", host, None)

    host, why = choose_host({}, {}, set())
    check("nothing listening yields no host", host, None)

    host, why = choose_host({"127.0.0.1": True}, {}, set())
    check("no listener table still resolves", host, "127.0.0.1")
    if "UNVERIFIED" not in why:
        fails.append("an unverified fallback did not say so: " + why)

    for line in fails:
        # Bracketed, and on STDOUT, both on purpose: tools/audit/mutate.py:173
        # scans stdout for a line starting "[FAIL]" and grades a mutation as a
        # STRONG signal only when the selftest names the check that broke. A
        # bare nonzero exit is downgraded to "confirm this is the intended
        # reason", which is a reviewer's job this can do mechanically instead.
        print("[FAIL] " + line)
    if fails:
        print("cdp selftest: {} failure(s)".format(len(fails)))
        return 1
    print("cdp selftest: 9 assertions, all passed")
    return 0


def cmd_stop() -> int:
    if not os.path.exists(PIDFILE):
        print("no pid recorded, nothing this tool launched")
        return 0
    pid = open(PIDFILE, encoding="utf-8").read().strip()
    subprocess.run(["taskkill", "/PID", pid, "/T", "/F"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(PIDFILE)
    print("killed pid {} and its children".format(pid))
    return 0


def main(argv: list[str]) -> int:
    # This machine's console codepage is cp1255, so any page containing a glyph
    # outside Hebrew-Latin (a command symbol, a smart quote, an arrow) raises
    # UnicodeEncodeError and loses the whole dump after it succeeded.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "selftest":
        return cmd_selftest()
    if cmd == "launch":
        print(json.dumps(launch(), indent=1))
        return 0
    if cmd == "status":
        global HOST
        host, why = resolve_host()
        HOST = host or HOST
        got = alive() if host else None
        print(json.dumps(got, indent=1) if got
              else "debug port {} on {}: {}".format(PORT, HOST, why))
        return 0 if got else 1
    if cmd == "text":
        return cmd_text(argv[2])
    if cmd == "shot":
        return cmd_shot(argv[2], argv[3] if len(argv) > 3 else "shot.png")
    if cmd == "eval":
        return cmd_eval(argv[2], argv[3])
    if cmd == "stop":
        return cmd_stop()
    print("unknown subcommand: " + cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
