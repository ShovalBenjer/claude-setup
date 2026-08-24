# -*- coding: utf-8 -*-
"""Render a URL at several viewport widths and save screenshots.

Responsive bugs are invisible in source and obvious in a picture, so this exists
to be run before calling a post done, not after someone reports it looks wrong.

    python shots.py <url> [--widths 1440,834,390] [--out DIR] [--full]

Uses whatever Chrome is listening on a debug port. Chrome 136+ refuses
--remote-debugging-port on the default profile, so this expects a dedicated
automation profile; several may be listening on the same port across IPv4 and
IPv6, and any of them will do for rendering.
"""
import argparse
import base64
import json
import os
import time
import urllib.request

import websocket  # type: ignore[import-not-found]

HOSTS = ["127.0.0.1", "[::1]"]
PORTS = [9224, 9222, 9225, 9226, 9231, 9232]
_id = [0]


def _cmd(ws, method, **params):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": method, "params": params}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _id[0]:
            if "error" in m:
                raise RuntimeError(m["error"])
            return m.get("result", {})


def ev(ws, expr):
    r = _cmd(ws, "Runtime.evaluate", expression=expr, returnByValue=True,
             awaitPromise=True)
    if "exceptionDetails" in r:
        d = r["exceptionDetails"]
        raise RuntimeError(d.get("exception", {}).get("description") or d.get("text"))
    return r.get("result", {}).get("value")


def connect():
    """Any debuggable Chrome will do; prefer a blank/new tab over a real one."""
    for port in PORTS:
        for host in HOSTS:
            try:
                raw = urllib.request.urlopen(
                    f"http://{host}:{port}/json", timeout=3).read()
            except Exception:
                continue
            pages = [t for t in json.loads(raw) if t.get("type") == "page"]
            if not pages:
                continue
            # never hijack a WhatsApp session tab
            pages = [p for p in pages if "whatsapp" not in (p.get("url") or "")]
            if not pages:
                continue
            ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                             timeout=45, suppress_origin=True)
            _cmd(ws, "Page.enable")
            _cmd(ws, "Runtime.enable")
            # Without this, re-rendering the same URL after an edit serves the
            # cached copy and the screenshot silently shows the previous
            # version: identical page height, identical pixels, and an hour
            # spent wondering why a CSS change had no effect. It is also why
            # ?v= cache-busters kept getting hand-rolled.
            try:
                _cmd(ws, "Network.enable")
                _cmd(ws, "Network.setCacheDisabled", cacheDisabled=True)
            except Exception:
                pass
            print(f"using {host}:{port} -> {pages[0].get('url','')[:60]}")
            return ws
    raise SystemExit("no debuggable Chrome found")


def capture(ws, url, width, out, full=False, height=900, dpr=2, scroll=0):
    _cmd(ws, "Emulation.setDeviceMetricsOverride", width=width, height=height,
         deviceScaleFactor=dpr, mobile=width < 700)
    # Headless and emulated contexts default to reduced motion, which hides
    # anything that only appears once an animation or transition has run.
    try:
        _cmd(ws, "Emulation.setEmulatedMedia",
             features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
    except Exception:
        pass
    _cmd(ws, "Page.navigate", url=url)
    time.sleep(3.0)
    for _ in range(30):
        if ev(ws, "document.readyState") == "complete":
            break
        time.sleep(0.3)
    time.sleep(1.5)
    # Scroll-reveal sections use an IntersectionObserver, and an instant jump to
    # an offset never makes the middle sections pass through the viewport, so
    # they stay stuck at opacity 0 in the screenshot even though they render
    # fine for a real reader who scrolls. Step down the page in viewport-sized
    # increments so every section is actually intersected once, then go to the
    # requested offset.
    h = ev(ws, "document.documentElement.scrollHeight") or 0
    step = max(1, int(h) // max(1, height))
    for i in range(step + 1):
        ev(ws, f"window.scrollTo(0,{i*height})")
        time.sleep(0.12)
    time.sleep(0.6)
    ev(ws, f"window.scrollTo(0,{int(scroll)})")
    time.sleep(1.0)

    params = {"format": "png"}
    if full:
        params["captureBeyondViewport"] = True
        h = ev(ws, "document.documentElement.scrollHeight")
        _cmd(ws, "Emulation.setDeviceMetricsOverride", width=width,
             height=min(int(h), 12000), deviceScaleFactor=1, mobile=width < 700)
        time.sleep(0.8)
    r = _cmd(ws, "Page.captureScreenshot", **params)
    tag = "-full" if full else (f"-s{int(scroll)}" if scroll else "")
    path = os.path.join(out, f"w{width}{tag}.png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(r["data"]))
    metrics = ev(ws, "JSON.stringify({iw:innerWidth,"
                     "sw:document.documentElement.scrollWidth,"
                     "cw:document.documentElement.clientWidth,"
                     "sh:document.documentElement.scrollHeight})")
    m = json.loads(metrics)
    overflow = m["sw"] > m["cw"] + 1

    # Two failures the scrollWidth check cannot see, both found the hard way:
    #
    #  - Content clipped inside an overflow-x:auto container. The page does not
    #    overflow, because the container absorbs it, so the metric says ok while
    #    the reader sees a truncated sentence and no scroll affordance.
    #  - Scroll-reveal elements stuck at opacity 0. An IntersectionObserver that
    #    never fires leaves whole sections invisible, and the layout metrics are
    #    perfectly healthy.
    # Scoped to what is actually on screen. An earlier version scanned the whole
    # document and reported every scroll-reveal section below the fold as
    # "stuck invisible", which is the design working: they are meant to be at
    # opacity 0 until scrolled to. A detector has to key on the real failure
    # condition, which is invisible *while in the viewport*.
    audit = ev(ws, """JSON.stringify((()=>{
      const clipped=[],hidden=[];
      const onScreen=(r)=>r.bottom>0 && r.top<innerHeight && r.width>2 && r.height>2;
      document.querySelectorAll('*').forEach(e=>{
        const r=e.getBoundingClientRect();
        if(!onScreen(r)) return;
        const s=getComputedStyle(e);
        // a code block or diagram that scrolls sideways is intentional; a text
        // container that does it is a reader staring at a truncated sentence
        const intentional=/^(PRE|CODE)$/.test(e.tagName)||
                          /graph|scroll|swipe/i.test(e.className||'');
        if(!intentional && /auto|scroll|hidden/.test(s.overflowX)
           && e.scrollWidth>e.clientWidth+2)
          clipped.push((e.className||e.tagName).toString().slice(0,28)
                       +' +'+(e.scrollWidth-e.clientWidth)+'px');
        // A reveal element mid-transition already carries its shown-state class
        // ("on") and is fading in, not stuck. Only flag the genuinely stuck:
        // low opacity AND not yet marked revealed, i.e. the observer never
        // fired. Flagging transitioning elements produced false positives that
        // could mask a real stuck section.
        if(parseFloat(s.opacity)<0.15 && e.textContent.trim().length>60
           && !e.classList.contains('on'))
          hidden.push((e.className||e.tagName).toString().slice(0,28));
      });
      return {clipped:[...new Set(clipped)].slice(0,6),
              hidden:[...new Set(hidden)].slice(0,6)};
    })())""")
    a = json.loads(audit)
    print(f"  w={width:<5} innerWidth={m['iw']:<5} scrollW={m['sw']:<5} "
          f"height={m['sh']:<6} {'HORIZONTAL OVERFLOW' if overflow else 'ok'} "
          f"-> {path}")
    if a["clipped"]:
        print(f"    CLIPPED inside a scroll container: {a['clipped']}")
    if a["hidden"]:
        print(f"    STUCK INVISIBLE (opacity<0.15 with text): {a['hidden']}")
    return path, overflow or bool(a["clipped"]) or bool(a["hidden"])


# Walks up from the element reporting each ancestor's used width and the
# properties that set it. Guessing which container constrains a box is how an
# hour disappears; this answers it in one call.
MEASURE = """(()=>{
  const el=document.querySelector(%s);
  if(!el) return 'selector matched nothing';
  const out=[];
  let n=el, depth=0;
  while(n && n.tagName!=='HTML' && depth<9){
    const s=getComputedStyle(n), r=n.getBoundingClientRect();
    out.push('    '+'  '.repeat(depth)
      +(n.tagName+'.'+(n.className||'').toString().trim().split(/\\s+/).join('.')).slice(0,34)
      +'  used='+Math.round(r.width)+'px'
      +'  display='+s.display
      +'  width='+s.width+'  min='+s.minWidth+'  max='+s.maxWidth);
    n=n.parentElement; depth++;
  }
  return out.join('\\n');
})()"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--widths", default="1440,834,390")
    p.add_argument("--out", default=".")
    p.add_argument("--full", action="store_true", help="full-page, not viewport")
    p.add_argument("--scroll", default="0", help="comma-separated scroll offsets")
    p.add_argument("--measure", help="CSS selector: report its box and the chain "
                                     "of ancestor widths, for working out which "
                                     "container is actually constraining it")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ws = connect()
    bad = []
    offsets = [int(x) for x in str(a.scroll).split(",")]
    for w in [int(x) for x in a.widths.split(",")]:
        for off in offsets:
            _, ov = capture(ws, a.url, w, a.out, full=a.full, scroll=off)
            if ov and w not in bad:
                bad.append(w)
        if a.measure:
            print(f"  measuring {a.measure!r} at w={w}:")
            print(ev(ws, MEASURE % json.dumps(a.measure)))
    _cmd(ws, "Emulation.clearDeviceMetricsOverride")
    print("\nhorizontal overflow at: " + (", ".join(map(str, bad)) if bad else "none"))


if __name__ == "__main__":
    main()
