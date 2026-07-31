# -*- coding: utf-8 -*-
"""Drive WhatsApp Web over CDP: read, react, reply, send.

Companion to wa_query.py (which reads the decrypted local store). This one talks
to the live session, which matters for two reasons: the DOM carries real sender
attribution that the decrypted store drops, and it is the only way to act.

Everything is dry-run by default. Nothing leaves the machine without --go.

    wa_act.py chats                                  list chats
    wa_act.py tail   --chat X [-n 20]                recent messages, attributed
    wa_act.py find   --chat X --match REGEX          locate a message
    wa_act.py react  --chat X --match REGEX --emoji EMOJI [--go]
    wa_act.py send   --chat X --file lines.txt [--quote REGEX] [--go]

send treats each non-empty line of the file as its own message, which is how a
burst is actually sent. --quote makes the FIRST message a reply to the matched
message; the rest follow as normal sends.

Host discovery: several Chrome instances can bind the same debug port on
different address families, and only one may be logged in. Guessing wrong looks
exactly like "WhatsApp is logged out", so every candidate is probed for a real
chat list rather than assuming the first hit is right.
"""
import argparse
import json
import re
import sys
import time
import urllib.request

import websocket  # type: ignore[import-not-found]

HOSTS = ["[::1]", "127.0.0.1"]
PORTS = [9224, 9222, 9225, 9226, 9231, 9232]
_id = [0]


# ----------------------------------------------------------------- transport

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
        # .text is just "Uncaught"; the useful message is on the exception object
        detail = (d.get("exception", {}).get("description")
                  or d.get("exception", {}).get("value")
                  or d.get("text"))
        raise RuntimeError(f"JS: {detail}")
    return r.get("result", {}).get("value")


def _targets(host, port):
    try:
        raw = urllib.request.urlopen(f"http://{host}:{port}/json", timeout=3).read()
        return json.loads(raw)
    except Exception:
        return []


def connect(verbose=True):
    """Find a Chrome with a LOGGED-IN WhatsApp and return its websocket."""
    tried = []
    for port in PORTS:
        for host in HOSTS:
            for t in _targets(host, port):
                if t.get("type") != "page" or "whatsapp" not in (t.get("url") or ""):
                    continue
                try:
                    ws = websocket.create_connection(
                        t["webSocketDebuggerUrl"], timeout=45, suppress_origin=True)
                    _cmd(ws, "Page.enable")
                    _cmd(ws, "Runtime.enable")
                    ok = ev(ws, "!!document.querySelector('#pane-side')")
                    tried.append(f"{host}:{port} logged_in={ok}")
                    if ok:
                        if verbose:
                            print(f"connected: {host}:{port}")
                        return ws
                    ws.close()
                except Exception as e:
                    tried.append(f"{host}:{port} {type(e).__name__}")
    raise SystemExit("no logged-in WhatsApp found. probed:\n  " + "\n  ".join(tried)
                     or "no WhatsApp tab at all")


def click(ws, x, y, settle=0.3):
    _cmd(ws, "Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    time.sleep(settle)
    for t in ("mousePressed", "mouseReleased"):
        _cmd(ws, "Input.dispatchMouseEvent", type=t, x=x, y=y,
             button="left", clickCount=1)
        time.sleep(0.05)
    time.sleep(settle)


def shot(ws, path):
    """Save a screenshot. UI automation that reasons only from the DOM goes
    wrong quietly; looking at the pixels is how the wrong assumption surfaces."""
    import base64
    r = _cmd(ws, "Page.captureScreenshot", format="png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(r["data"]))
    print(f"    shot -> {path}")


def hover(ws, x, y, settle=0.8):
    _cmd(ws, "Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    time.sleep(settle)


def wait_for(ws, expr, timeout=5.0, step=0.2):
    """Poll a JS predicate instead of sleeping a guessed interval.

    The reaction bar animates in: its emoji exist in the DOM before they have
    been laid out, so a width filter run at a fixed delay sees zero-width
    elements and concludes the bar never opened. One check at 1.6s said "no bar"
    while the very next call, a tenth of a second later, listed all six.
    """
    end = time.time() + timeout
    while time.time() < end:
        v = ev(ws, expr)
        if v:
            return v
        time.sleep(step)
    return None


def key(ws, k, code, vk):
    for t in ("keyDown", "keyUp"):
        _cmd(ws, "Input.dispatchKeyEvent", type=t, key=k, code=code,
             windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk)
        time.sleep(0.04)


# --------------------------------------------------------------------- pieces

JS_CHATS = """(()=>[...document.querySelectorAll('#pane-side [role="row"]')]
  .slice(0,%d).map(r=>{const t=r.querySelector('span[title]');
    return t?t.getAttribute('title'):null;}).filter(Boolean))()"""

JS_OPEN = """(()=>{
  const want=%s;
  const r=[...document.querySelectorAll('#pane-side [role="row"]')]
    .find(x=>{const t=x.querySelector('span[title]');
              return t && t.getAttribute('title')===want;});
  if(!r) return null;
  const el=r.querySelector('[role="gridcell"]')||r;
  el.scrollIntoView({block:'center'});
  const b=el.getBoundingClientRect();
  return JSON.stringify({x:Math.round(b.x+b.width/2), y:Math.round(b.y+b.height/2)});
})()"""

JS_HEADER = """(()=>{const m=document.querySelector('#main');
  if(!m) return null; const h=m.querySelector('header');
  return h?h.innerText.replace(/\\s+/g,' ').slice(0,50):null;})()"""

# Emoji render as <img alt>, which innerText drops; clone and substitute.
# Declared INSIDE each IIFE, never at top level: a top-level binding in
# Runtime.evaluate persists in the page's global scope, so the second call in a
# session dies with "Identifier already declared" and the page stays poisoned
# until reload.
JS_TEXT = """const _t=(el)=>{const c=el.cloneNode(true);
  c.querySelectorAll('img').forEach(i=>i.replaceWith(
      document.createTextNode(i.getAttribute('alt')||'')));
  c.querySelectorAll('br').forEach(b=>b.replaceWith(document.createTextNode(' / ')));
  return c.textContent;};"""

JS_TAIL = """(()=>{""" + JS_TEXT + """
  const m=document.querySelector('#main');
  if(!m) return JSON.stringify({err:'no chat open'});
  const rows=[...m.querySelectorAll('[role="row"]')];
  return JSON.stringify(rows.slice(-%d).map(r=>{
    const c=r.querySelector('[data-pre-plain-text]');
    const meta=c?c.getAttribute('data-pre-plain-text'):null;
    let who=null, at=null;
    if(meta){const g=meta.match(/^\\[([^\\]]+)\\]\\s*(.*?):\\s*$/);
             if(g){at=g[1]; who=g[2];}}
    return {at, who, body:_t(r.querySelector('.copyable-text')||r)
                        .replace(/\\s+/g,' ').trim().slice(0,240)};
  }).filter(x=>x.body));
})()"""

JS_FIND = """(()=>{""" + JS_TEXT + """
  const rx=new RegExp(%s,'i');
  const m=document.querySelector('#main');
  if(!m) return JSON.stringify({err:'no chat open'});
  const rows=[...m.querySelectorAll('[role="row"]')];
  for(const r of rows){
    if(!rx.test(r.innerText||'')) continue;
    r.scrollIntoView({block:'center'});
    const b=r.getBoundingClientRect();
    const c=r.querySelector('[data-pre-plain-text]');
    return JSON.stringify({found:true, meta:c?c.getAttribute('data-pre-plain-text'):null,
      text:_t(r).replace(/\\s+/g,' ').slice(0,140),
      x:Math.round(b.x+b.width/2), y:Math.round(b.y+b.height/2)});
  }
  return JSON.stringify({found:false, loaded:rows.length});
})()"""

JS_SCROLL_UP = """(()=>{
  const p=[...document.querySelectorAll('#main div')]
    .filter(d=>d.scrollHeight>d.clientHeight+50 && d.clientHeight>200)[0];
  if(!p) return 'no pane';
  p.scrollTop=Math.max(0,p.scrollTop-p.clientHeight*1.2);
  return p.scrollTop+'/'+p.scrollHeight;
})()"""

# row affordances: aria-labels are localised, so match on the icon where possible
JS_ROWBTN = """(()=>{
  const rx=new RegExp(%s,'i');
  const r=[...document.querySelectorAll('#main [role="row"]')]
    .find(x=>rx.test(x.innerText||''));
  if(!r) return null;
  const want=%s;
  const b=[...r.querySelectorAll('[role="button"],button')].find(e=>{
    const l=e.getAttribute('aria-label')||'';
    return want.some(w=>l.includes(w));
  });
  if(!b) return null;
  const q=b.getBoundingClientRect();
  return JSON.stringify({x:Math.round(q.x+q.width/2), y:Math.round(q.y+q.height/2),
                         label:b.getAttribute('aria-label')});
})()"""

JS_ICON = """(()=>{
  const s=[...document.querySelectorAll('span[data-icon="%s"]')]
    .find(e=>e.getBoundingClientRect().width>0);
  if(!s) return null;
  const b=s.closest('button')||s;
  const r=b.getBoundingClientRect();
  return JSON.stringify({x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)});
})()"""

# "Is the reaction bar open" is defined as: six or more emoji images sharing one
# y. That is unique to the bar. Two earlier detectors were both wrong and the
# screenshot is what settled it:
#   - any of 🙏/😮/😢 anywhere  -> false positive on a reaction already sitting
#     on some other message in the thread, so it always answered yes
#   - span[data-icon="ic-add"] -> answered no while the bar was plainly open in
#     the screenshot, so the add button is not reliably tagged that way
JS_BARROW = """(()=>{
  const rows={};
  [...document.querySelectorAll('img[alt]')].forEach(e=>{
    const r=e.getBoundingClientRect();
    if(r.width<14||r.width>44||r.top<=0) return;
    const k=Math.round(r.y/4)*4;
    (rows[k]=rows[k]||[]).push({alt:e.getAttribute('alt'),
                                x:Math.round(r.x+r.width/2),
                                y:Math.round(r.y+r.height/2)});
  });
  let best=null;
  for(const k in rows) if(rows[k].length>=6 &&
      (!best||rows[k].length>best.length)) best=rows[k];
  if(!best) return null;
  best.sort((a,b)=>a.x-b.x);
  return JSON.stringify({y:best[0].y, minx:best[0].x,
                         emoji:best.map(e=>e.alt)});
})()"""

JS_QUICKBAR = """(()=>{
  const rows={};
  [...document.querySelectorAll('img[alt]')].forEach(e=>{
    const r=e.getBoundingClientRect();
    if(r.width<14||r.width>44||r.top<=0) return;
    const k=Math.round(r.y/4)*4; rows[k]=(rows[k]||0)+1;
  });
  return Object.values(rows).some(n=>n>=6);
})()"""

# The emoji picker's search field, distinguished from the message composer by
# sitting above it. Typing without focusing this is what put "goat" in the chat
# box on the first attempt.
JS_PICKER_SEARCH = """(()=>{
  const c=[...document.querySelectorAll('input,[contenteditable="true"],[role="textbox"]')]
    .map(e=>{const r=e.getBoundingClientRect();
             return {e, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2),
                     w:r.width, top:r.y};})
    .filter(o=>o.w>60 && o.top>0);
  if(!c.length) return null;
  const box=document.querySelector('#main [contenteditable="true"]');
  const boxTop=box?box.getBoundingClientRect().y:1e9;
  const above=c.filter(o=>o.top<boxTop-30);
  const pick=above.length?above[above.length-1]:null;
  return pick?JSON.stringify({x:pick.x, y:pick.y}):null;
})()"""

# Element-level clicks. A synthesised mouse click has to land on a moving,
# animating target and toggles the bar if it arrives twice; .click() on the
# resolved node does not.
JS_CLICK_REACT = """(()=>{
  const rx=new RegExp(%s,'i');
  const r=[...document.querySelectorAll('#main [role="row"]')]
    .find(x=>rx.test(x.innerText||''));
  if(!r) return false;
  const b=[...r.querySelectorAll('[role="button"],button')]
    .find(e=>/אמוג|react|reaction/i.test(e.getAttribute('aria-label')||''));
  if(!b) return false;
  b.click();
  return true;
})()"""

# The add button sits one slot left of the leftmost quick emoji, on the same
# row. Located by geometry: its data-icon is not dependable.
JS_CLICK_PLUS = """(()=>{
  const em=[...document.querySelectorAll('img[alt]')]
    .map(e=>({e, r:e.getBoundingClientRect()}))
    .filter(o=>o.r.width>14 && o.r.width<44 && o.r.top>0);
  const buckets={};
  em.forEach(o=>{const k=Math.round(o.r.y/4)*4;(buckets[k]=buckets[k]||[]).push(o);});
  let row=null;
  for(const k in buckets) if(buckets[k].length>=6 &&
      (!row||buckets[k].length>row.length)) row=buckets[k];
  if(!row) return false;
  row.sort((a,b)=>a.r.x-b.r.x);
  const y=row[0].r.y+row[0].r.height/2, x=row[0].r.x-20;
  const el=document.elementFromPoint(x,y);
  const b=el&&(el.closest('button')||el.closest('[role="button"]'));
  if(!b) return false;
  b.click();
  return true;
})()"""

# Message-body emoji are <img alt="🐐">, but picker results are sprite elements
# that carry the character in an attribute or as text instead, so matching only
# on img[alt] finds the emoji in the conversation and misses it in the picker.
JS_CLICK_EMOJI = """(()=>{
  const want=%s;
  const vis=(e)=>{const r=e.getBoundingClientRect();
                  return r.width>10 && r.width<80 && r.top>0 && r.left>0;};
  const fire=(e)=>{const b=e.closest('button')||e.closest('[role="button"]')||
                          e.closest('li')||e.parentElement;
                   (b||e).click(); return true;};
  let hit=[...document.querySelectorAll('img[alt]')]
    .filter(vis).find(e=>e.getAttribute('alt')===want);
  if(hit) return fire(hit);
  for(const e of document.querySelectorAll('[aria-label],[title],[data-emoji],[data-name]')){
    if(!vis(e)) continue;
    const v=(e.getAttribute('data-emoji')||e.getAttribute('aria-label')||
             e.getAttribute('title')||e.getAttribute('data-name')||'');
    if(v===want||v.includes(want)) return fire(e);
  }
  for(const e of document.querySelectorAll('button,[role="button"],li,span')){
    if(!vis(e)) continue;
    if((e.textContent||'').trim()===want) return fire(e);
  }
  return false;
})()"""

# There is no reply button on the row. "הודעה מצוטטת" is the label of a quoted
# preview *inside* a bubble that is itself a reply, which is why matching it
# found an element and clicking it did nothing. Reply lives in the per-message
# context menu, so that is opened first and the item picked from it.
JS_CLICK_CTXMENU = """(()=>{
  const rx=new RegExp(%s,'i');
  const r=[...document.querySelectorAll('#main [role="row"]')]
    .find(x=>rx.test(x.innerText||''));
  if(!r) return false;
  const b=[...r.querySelectorAll('[role="button"],button')]
    .find(e=>/תפריט הקשר|context menu/i.test(e.getAttribute('aria-label')||''));
  if(!b) return false;
  b.click();
  return true;
})()"""

JS_CLICK_REPLY = """(()=>{
  const items=[...document.querySelectorAll('[role="menuitem"],li,button,div')]
    .filter(e=>{const r=e.getBoundingClientRect();
                return r.width>40 && r.height>10 && r.height<70 && r.top>0;});
  const hit=items.find(e=>/^(מענה|השב|Reply)$/i.test((e.textContent||'').trim()));
  if(!hit) return false;
  const r=hit.getBoundingClientRect();
  return JSON.stringify({x:Math.round(r.x+r.width/2),
                         y:Math.round(r.y+r.height/2),
                         t:(hit.textContent||'').trim().slice(0,20)});
})()"""

JS_MENU_DUMP = """(()=>[...document.querySelectorAll('[role="menuitem"],li')]
  .filter(e=>e.getBoundingClientRect().width>40)
  .map(e=>(e.textContent||'').trim().slice(0,24)).slice(0,15))()"""

# A quoted reply puts a cancel-quote control above the composer. Confirming it
# is present is what separates "clicked reply" from "reply actually attached".
JS_QUOTE_ACTIVE = """(()=>{
  const f=document.querySelector('footer')||document.querySelector('#main');
  if(!f) return false;
  return !!f.querySelector('[data-icon="x"],[data-icon="ic-x"],[aria-label*="ביטול"],'
                          +'[aria-label*="Cancel"],[data-icon="x-alt"]');
})()"""

JS_EMOJI_RECT = """(()=>{
  const want=%s;
  const vis=(e)=>{const r=e.getBoundingClientRect();
                  return r.width>10 && r.width<80 && r.top>0 && r.left>0;};
  const box=(e,how)=>{const r=e.getBoundingClientRect();
    return JSON.stringify({x:Math.round(r.x+r.width/2),
                           y:Math.round(r.y+r.height/2), how});};
  let hit=[...document.querySelectorAll('img[alt]')]
    .filter(vis).find(e=>e.getAttribute('alt')===want);
  if(hit) return box(hit,'img[alt]');
  for(const e of document.querySelectorAll('[data-emoji],[aria-label],[title],[data-name]')){
    if(!vis(e)) continue;
    const v=(e.getAttribute('data-emoji')||e.getAttribute('aria-label')||
             e.getAttribute('title')||e.getAttribute('data-name')||'');
    if(v===want||v.includes(want)) return box(e,'attr');
  }
  for(const e of document.querySelectorAll('button,[role="button"],li,span')){
    if(!vis(e)) continue;
    if((e.textContent||'').trim()===want) return box(e,'text');
  }
  return null;
})()"""

JS_IMG_DUMP = """(()=>{
  const out=[];
  document.querySelectorAll('*').forEach(e=>{
    const r=e.getBoundingClientRect();
    if(r.width<12||r.width>60||r.height<12||r.height>60) return;
    if(r.top<0||r.top>innerHeight) return;
    const lab=e.getAttribute('aria-label')||'';
    const alt=e.getAttribute('alt')||'';
    const di=e.getAttribute('data-icon')||'';
    if(!lab && !alt && !di) return;
    out.push({t:e.tagName, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2),
              w:Math.round(r.width), a:alt, l:lab.slice(0,24), d:di});
  });
  return out.slice(0,30);
})()"""

JS_ICONS_SEEN = """(()=>[...document.querySelectorAll('[data-icon]')]
  .filter(e=>e.getBoundingClientRect().width>0)
  .map(e=>e.getAttribute('data-icon')).slice(0,25))()"""

JS_EMOJI_AT = """(()=>{
  const want=%s;
  const hit=[...document.querySelectorAll('img[alt]')]
    .filter(e=>{const r=e.getBoundingClientRect();
                return r.width>10 && r.width<70 && r.top>0;})
    .find(e=>e.getAttribute('alt')===want);
  if(!hit) return null;
  const r=hit.getBoundingClientRect();
  return JSON.stringify({x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)});
})()"""

JS_BOX = """(()=>{
  const b=[...document.querySelectorAll('#main [contenteditable="true"]')]
    .filter(e=>e.getBoundingClientRect().width>150).pop();
  if(!b) return null;
  const r=b.getBoundingClientRect();
  return JSON.stringify({x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2),
                         text:(b.innerText||'').slice(0,60)});
})()"""


def open_chat(ws, name):
    pos = ev(ws, JS_OPEN % json.dumps(name, ensure_ascii=False))
    if not pos:
        names = ev(ws, JS_CHATS % 40) or []
        raise SystemExit(f"chat {name!r} not in the loaded list.\n"
                         f"visible: {[n[:24] for n in names[:15]]}")
    p = json.loads(pos)
    click(ws, p["x"], p["y"])
    time.sleep(1.4)


def find_row(ws, pattern, scrolls=12):
    for i in range(scrolls):
        d = json.loads(ev(ws, JS_FIND % json.dumps(pattern)))
        if d.get("err"):
            raise SystemExit(d["err"])
        if d.get("found"):
            return d
        ev(ws, JS_SCROLL_UP)
        time.sleep(1.3)
    return None


# ------------------------------------------------------------------ commands

def cmd_chats(ws, a):
    for n in ev(ws, JS_CHATS % a.n) or []:
        print(" ", n[:70])


def cmd_tail(ws, a):
    open_chat(ws, a.chat)
    print("header:", ev(ws, JS_HEADER), "\n")
    for m in json.loads(ev(ws, JS_TAIL % a.n)):
        print(f"[{m['at']}] {(m['who'] or '?')[:14]:<14} {m['body']}")


def cmd_find(ws, a):
    open_chat(ws, a.chat)
    d = find_row(ws, a.match, a.scrolls)
    print(json.dumps(d, ensure_ascii=False, indent=1) if d else "not found")


def cmd_react(ws, a):
    open_chat(ws, a.chat)
    row = find_row(ws, a.match, a.scrolls)
    if not row:
        raise SystemExit(f"no message matching {a.match!r}")
    print("target:", row["meta"], "|", row["text"][:70])
    if a.emoji in row["text"]:
        print(f"{a.emoji} already present on this row; nothing to do")
        return
    if not a.go:
        print("DRY RUN. pass --go to apply.")
        return

    # Synthesised mouse clicks proved unreliable here: the affordance only
    # exists while hovered, the bar animates in, and a second coordinate click
    # toggles it shut again, so attempts raced between opening and closing.
    # Calling .click() on the resolved element is deterministic. The mouse is
    # still moved over the row first, because the button is not rendered at all
    # until the row is hovered.
    # Clear any overlay left open by a previous run. A picker still on screen
    # swallows the next click and the failure reads as "the bar would not open".
    # Escape also backs out of the conversation itself, so the chat is reopened
    # afterwards rather than assumed still open.
    for _ in range(2):
        key(ws, "Escape", "Escape", 27)
        time.sleep(0.4)
    open_chat(ws, a.chat)

    row = find_row(ws, a.match, a.scrolls)
    if not row:
        raise SystemExit(f"lost the row matching {a.match!r} after resetting state")
    hover(ws, row["x"], row["y"], settle=1.0)
    if not ev(ws, JS_CLICK_REACT % json.dumps(a.match)):
        raise SystemExit("react affordance never appeared on hover")
    bar_raw = wait_for(ws, JS_BARROW, timeout=8.0)
    if not bar_raw:
        if a.shot:
            shot(ws, "react_nobar.png")
        raise SystemExit("reaction bar would not open; nothing applied")
    bar = json.loads(bar_raw)
    print(f"  bar open: {' '.join(bar['emoji'])}")

    if a.emoji not in bar["emoji"]:
        print(f"  {a.emoji} is not one of the quick six; opening the full picker")
        if not ev(ws, JS_CLICK_PLUS):
            raise SystemExit("plus button not found in the open bar")
        if not wait_for(ws, JS_PICKER_SEARCH, timeout=8.0):
            if a.shot:
                shot(ws, "react_nopicker.png")
            raise SystemExit("picker search box never appeared; nothing typed")
        # focus the picker's own field, or the term goes into the chat composer
        s = json.loads(ev(ws, JS_PICKER_SEARCH))
        click(ws, s["x"], s["y"], settle=0.4)
        _cmd(ws, "Input.insertText", text=a.term)
        if a.shot:
            time.sleep(1.2)
            shot(ws, "react_search.png")
    # Locate then click with a real mouse event. .click() works for the row
    # affordance and the plus, but picker results are sprite nodes whose
    # handlers are on pointer events, so a synthetic .click() resolves without
    # applying anything and the run reports success while nothing happened.
    raw = wait_for(ws, JS_EMOJI_RECT % json.dumps(a.emoji), timeout=6.0)
    if not raw:
        if a.shot:
            shot(ws, "react_nohit.png")
        raise SystemExit(f"{a.emoji} not found after searching {a.term!r}; "
                         f"nothing clicked")
    h = json.loads(raw)
    print(f"  clicking {a.emoji} at ({h['x']},{h['y']}) via {h['how']}")
    click(ws, h["x"], h["y"], settle=0.4)
    time.sleep(2.0)
    d = json.loads(ev(ws, JS_FIND % json.dumps(a.match)))
    print("after:", d.get("text"))
    print("applied" if a.emoji in (d.get("text") or "") else "NOT confirmed")


def cmd_send(ws, a):
    lines = [l.strip() for l in open(a.file, encoding="utf-8").read().split("\n")
             if l.strip()]
    if not lines:
        raise SystemExit("nothing to send")
    open_chat(ws, a.chat)
    print("header:", ev(ws, JS_HEADER))
    quote = None
    if a.quote:
        quote = find_row(ws, a.quote, a.scrolls)
        if not quote:
            raise SystemExit(f"quote target {a.quote!r} not found")
        print("quoting:", quote["meta"], "|", quote["text"][:60])
    print(f"\n{len(lines)} message(s) to send:")
    for i, l in enumerate(lines, 1):
        print(f"  {i:>2}. {l}")
    if not a.go:
        print("\nDRY RUN. pass --go to send.")
        return

    for i, line in enumerate(lines):
        if i == 0 and quote:
            # Same shape as the react affordance: it only exists while hovered,
            # and a coordinate click races its animation. Hover to materialise
            # it, then .click() the resolved node, then confirm the composer is
            # actually showing a quoted preview before typing anything.
            # Right-click opens the per-message menu directly. The hover
            # affordance is unreliable: on an outgoing bubble the chevron often
            # never renders, and hunting for it wasted a long time.
            hover(ws, quote["x"], quote["y"], settle=0.8)
            _cmd(ws, "Input.dispatchMouseEvent", type="mousePressed",
                 x=quote["x"], y=quote["y"], button="right", clickCount=1)
            _cmd(ws, "Input.dispatchMouseEvent", type="mouseReleased",
                 x=quote["x"], y=quote["y"], button="right", clickCount=1)
            time.sleep(1.0)
            if not wait_for(ws, JS_CLICK_REPLY, timeout=4.0):
                # fall back to the hover chevron if right-click was swallowed
                ev(ws, JS_CLICK_CTXMENU % json.dumps(a.quote))
                time.sleep(0.8)
            raw = wait_for(ws, JS_CLICK_REPLY, timeout=6.0)
            if not raw:
                print(f"    menu items: {ev(ws, JS_MENU_DUMP)}")
                raise SystemExit("no Reply item in the menu; nothing sent")
            m = json.loads(raw)
            click(ws, m["x"], m["y"], settle=0.4)
            if not wait_for(ws, JS_QUOTE_ACTIVE, timeout=6.0):
                raise SystemExit("reply box did not attach a quote; nothing sent")
            print(f"    quote attached via {m['t']!r}")
        box = ev(ws, JS_BOX)
        if not box:
            raise SystemExit(f"composer not found before message {i+1}; "
                             f"{i} sent so far")
        p = json.loads(box)
        click(ws, p["x"], p["y"], settle=0.25)
        # insertText APPENDS. Anything already in the box (a half-typed word, or
        # a failed emoji search that landed here) would prefix the first
        # message, so the box is emptied before every send.
        if p["text"].strip():
            print(f"    clearing composer residue {p['text']!r}")
            for _ in range(len(p["text"]) + 5):
                key(ws, "Backspace", "Backspace", 8)
        _cmd(ws, "Input.insertText", text=line)
        time.sleep(0.35)
        key(ws, "Enter", "Enter", 13)
        time.sleep(a.gap)
        print(f"  sent {i+1}/{len(lines)}")
    time.sleep(1.2)
    print("\ntail after send:")
    for m in json.loads(ev(ws, JS_TAIL % min(len(lines) + 2, 20))):
        print(f"  [{m['at']}] {(m['who'] or '?')[:12]:<12} {m['body'][:60]}")


def cmd_composer(ws, a):
    """Inspect, and optionally clear, the message box.

    Exists because a failed emoji-picker search types its term into the
    composer instead: the picker's search field was never focused, so
    Input.insertText landed in the chat box. Stray text there is one Enter away
    from being sent, so it needs checking after any aborted interaction.
    """
    open_chat(ws, a.chat)
    box = ev(ws, JS_BOX)
    if not box:
        raise SystemExit("composer not found")
    p = json.loads(box)
    print(f"composer contains: {p['text']!r}")
    if not p["text"].strip():
        return
    if not a.clear:
        print("pass --clear to empty it (nothing is ever sent by this command)")
        return
    click(ws, p["x"], p["y"], settle=0.3)
    _cmd(ws, "Input.dispatchKeyEvent", type="keyDown", key="a",
         code="KeyA", windowsVirtualKeyCode=65, nativeVirtualKeyCode=65,
         modifiers=2)
    _cmd(ws, "Input.dispatchKeyEvent", type="keyUp", key="a",
         code="KeyA", windowsVirtualKeyCode=65, nativeVirtualKeyCode=65,
         modifiers=2)
    time.sleep(0.2)
    key(ws, "Backspace", "Backspace", 8)
    time.sleep(0.5)
    after = json.loads(ev(ws, JS_BOX))
    print(f"after clear: {after['text']!r}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scrolls", type=int, default=12)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("chats"); c.add_argument("-n", type=int, default=30)
    c.set_defaults(fn=cmd_chats)

    t = sub.add_parser("tail"); t.add_argument("--chat", required=True)
    t.add_argument("-n", type=int, default=20); t.set_defaults(fn=cmd_tail)

    f = sub.add_parser("find"); f.add_argument("--chat", required=True)
    f.add_argument("--match", required=True); f.set_defaults(fn=cmd_find)

    r = sub.add_parser("react"); r.add_argument("--chat", required=True)
    r.add_argument("--match", required=True); r.add_argument("--emoji", required=True)
    r.add_argument("--term", default="goat", help="search word in the full picker")
    r.add_argument("--go", action="store_true")
    r.add_argument("--shot", action="store_true", help="save screenshots at each step")
    r.set_defaults(fn=cmd_react)

    k = sub.add_parser("composer"); k.add_argument("--chat", required=True)
    k.add_argument("--clear", action="store_true"); k.set_defaults(fn=cmd_composer)

    s = sub.add_parser("send"); s.add_argument("--chat", required=True)
    s.add_argument("--file", required=True); s.add_argument("--quote")
    s.add_argument("--gap", type=float, default=0.9)
    s.add_argument("--go", action="store_true"); s.set_defaults(fn=cmd_send)

    a = p.parse_args()
    ws = connect()
    _cmd(ws, "Page.bringToFront")
    time.sleep(0.5)
    a.fn(ws, a)


if __name__ == "__main__":
    main()
