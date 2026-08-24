# -*- coding: utf-8 -*-
"""Minimal CDP driver for the automation Chrome profile (port 9224).
Usage:
  uv run --with websocket-client python cdp_driver.py shot out.png      # screenshot active tab
  uv run --with websocket-client python cdp_driver.py url               # current URL + title
  uv run --with websocket-client python cdp_driver.py nav <url>         # navigate
  uv run --with websocket-client python cdp_driver.py text              # visible innerText of body
  uv run --with websocket-client python cdp_driver.py eval "<js>"       # evaluate JS, print result
"""
import base64, json, os, sys, time, urllib.request
import websocket  # websocket-client

PORT = int(os.environ.get("CDP_PORT", "9224"))
TAB = os.environ.get("CDP_TAB", "")  # substring match on tab URL, else first page

def page_ws():
    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5).read())
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
        tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5).read())
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
