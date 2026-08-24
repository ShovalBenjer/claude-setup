# -*- coding: utf-8 -*-
# VENDORED FORK. Upstream: C:\Users\shova\new-recruit\cdp_driver.py (Windows side).
# Delta from upstream, and the only one: a CDP_HOST env var plus a BASE constant,
# because upstream hardcodes http://127.0.0.1:{PORT} in three places and under WSL
# the endpoint is the relay on the default-route address instead. Re-apply the same
# two-line change if upstream moves; do not diverge further here without saying so.
"""Minimal CDP driver for the automation Chrome profile (port 9224).
Usage:
  uv run --with websocket-client python cdp_driver.py shot out.png      # screenshot active tab
  uv run --with websocket-client python cdp_driver.py url               # current URL + title
  uv run --with websocket-client python cdp_driver.py nav <url>         # navigate
  uv run --with websocket-client python cdp_driver.py text              # visible innerText of body
  uv run --with websocket-client python cdp_driver.py eval "<js>"       # evaluate JS, print result
"""
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

# This reads arbitrary web pages and prints them, on a machine whose console is
# cp1255. Inheriting that encoding means dying at the last step on a character
# the page happened to contain, after the CDP round-trip already succeeded --
# U+2264 in a task brief did exactly that. So the driver picks its own output
# encoding instead. stderr is left alone: it belongs to whoever reads the
# traceback, not to this module.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PORT = int(os.environ.get("CDP_PORT", "9224"))
# Under WSL, Chrome lives on the Windows side behind cdp-relay.py, so the
# endpoint is the default-route address and the relay port, not loopback.
# Chrome builds webSocketDebuggerUrl from the request Host header, so once
# the HTTP base is right the ws URL comes back already pointing at the relay
# and needs no rewriting here.
HOST = os.environ.get("CDP_HOST", "127.0.0.1")
BASE = f"http://{HOST}:{PORT}"
TAB = os.environ.get("CDP_TAB", "")  # substring match on tab URL, else first page

def new_tab_ws(url):
    """Open a NEW tab at `url` and return (ws, tab_id).

    Separate from page_ws on purpose. page_ws filters existing tabs by a URL
    substring and, when nothing matches, silently falls back to `pages[0]`. That
    is fine for a read (look at whatever is open) and wrong for a write: caught
    2026-07-29 pre-flighting a scheduled LinkedIn send, when the LinkedIn tab had
    been closed overnight, the filter matched nothing, and pages[0] resolved to a
    local file the operator had open. The send would have navigated that tab.

    Callers that TYPE somewhere should use this and own their surface. It also
    keeps the HTTP client here, where the CDP transport already lives, rather
    than in hiring_engine/, where test_no_auto_submit forbids an executor from
    importing one at all.
    """
    import websocket  # type: ignore[import-not-found]  # websocket-client

    q = urllib.parse.quote(url, safe="")
    req = urllib.request.Request(
        f"{BASE}/json/new?{q}", method="PUT")
    tab = json.loads(urllib.request.urlopen(req, timeout=15).read())
    ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=30,
                                     suppress_origin=True)
    return ws, tab.get("id")


def page_ws():
    # Imported here, not at module scope: websocket-client is supplied per
    # invocation by `uv run --with websocket-client`, so it is absent from the
    # interpreter that runs the test suite. A top-level import would make the
    # module unimportable there, and therefore untestable anywhere.
    import websocket  # type: ignore[import-not-found]  # websocket-client

    tabs = json.loads(urllib.request.urlopen(f"{BASE}/json", timeout=5).read())
    pages = [t for t in tabs if t.get("type") == "page" and not t["url"].startswith("devtools://")]
    if not pages:
        raise SystemExit("no page targets")
    if TAB:
        matched = [t for t in pages if TAB in t["url"]]
        if matched:
            pages = matched
    return websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=30, suppress_origin=True), pages[0]

_id = [0]
def cmd(ws, method, **params):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": method, "params": params}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            if "error" in msg:
                raise RuntimeError(msg["error"])
            return msg.get("result", {})

def main():
    op = sys.argv[1] if len(sys.argv) > 1 else "url"
    ws, tab = page_ws()
    if op == "url":
        r = cmd(ws, "Runtime.evaluate", expression="JSON.stringify({url:location.href,title:document.title})", returnByValue=True)
        print(r["result"]["value"])
    elif op == "nav":
        cmd(ws, "Page.enable")
        cmd(ws, "Page.navigate", url=sys.argv[2])
        time.sleep(4)
        r = cmd(ws, "Runtime.evaluate", expression="location.href", returnByValue=True)
        print("now at:", r["result"]["value"])
    elif op == "shot":
        out = sys.argv[2] if len(sys.argv) > 2 else "shot.png"
        r = cmd(ws, "Page.captureScreenshot", format="png")
        with open(out, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        print("saved", out)
    elif op == "text":
        r = cmd(ws, "Runtime.evaluate", expression="document.body.innerText.slice(0,8000)", returnByValue=True)
        print(r["result"]["value"])
    elif op == "eval":
        r = cmd(ws, "Runtime.evaluate", expression=sys.argv[2], returnByValue=True, awaitPromise=True)
        print(json.dumps(r.get("result", {}).get("value"), ensure_ascii=False)[:8000])
    elif op == "tabs":
        tabs = json.loads(urllib.request.urlopen(f"{BASE}/json", timeout=5).read())
        for t in tabs:
            if t.get("type") == "page":
                print(t["url"][:110])
    elif op == "rect":
        expr = f"(()=>{{const e=document.querySelector({json.dumps(sys.argv[2])});if(!e)return null;const r=e.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}}}})()"
        r = cmd(ws, "Runtime.evaluate", expression=expr, returnByValue=True)
        print(json.dumps(r.get("result", {}).get("value")))
    elif op == "click":
        x, y = float(sys.argv[2]), float(sys.argv[3])
        for t, c in [("mousePressed", 1), ("mouseReleased", 1)]:
            cmd(ws, "Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=c)
        time.sleep(2)
        print("clicked", x, y)
    ws.close()

if __name__ == "__main__":
    main()
