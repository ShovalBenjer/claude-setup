# -*- coding: utf-8 -*-
"""Probe WhatsApp search with several queries; dump results pane text to file."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CDP_TAB", "whatsapp")
from cdp_driver import cmd, page_ws


def ev(ws, expr):
    r = cmd(ws, "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("value")

def click(ws, x, y):
    for t in ("mousePressed", "mouseReleased"):
        cmd(ws, "Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=1)
    time.sleep(1.0)

def type_text(ws, s):
    for ch in s:
        cmd(ws, "Input.dispatchKeyEvent", type="keyDown", text=ch)
        cmd(ws, "Input.dispatchKeyEvent", type="keyUp", text=ch)
        time.sleep(0.05)

def key(ws, keyname, code, vk, mods=0):
    cmd(ws, "Input.dispatchKeyEvent", type="rawKeyDown", key=keyname, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
    cmd(ws, "Input.dispatchKeyEvent", type="keyUp", key=keyname, code=code, windowsVirtualKeyCode=vk, modifiers=mods)

ws, tab = page_ws()
queries = sys.argv[1:] or ["myself"]
out = {}
for q in queries:
    rect = ev(ws, """(()=>{const el=document.querySelector('div[contenteditable="true"]'); if(!el) return null; const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};})()""")
    if not rect:
        rect = {"x": 1550, "y": 107}
    click(ws, rect["x"], rect["y"])
    key(ws, "a", "KeyA", 65, 2)   # Ctrl+A
    key(ws, "Backspace", "Backspace", 8)
    time.sleep(0.5)
    type_text(ws, q)
    time.sleep(2.5)
    out[q] = ev(ws, "document.querySelector('#pane-side')?.innerText?.slice(0,2500) || 'NO PANE'")
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_probe.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved", p)
