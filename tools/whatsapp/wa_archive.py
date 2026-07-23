# -*- coding: utf-8 -*-
"""Open WhatsApp archive via JS clicks, scroll, list all chat names."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CDP_TAB", "whatsapp")
from cdp_driver import page_ws, cmd

def ev(ws, expr):
    r = cmd(ws, "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("value")

JSCLICK = """function jsclick(el){
  for(const t of ['mousedown','mouseup','click']){
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));
  }
}"""

ws, tab = page_ws()
for _ in range(2):
    cmd(ws, "Input.dispatchKeyEvent", type="rawKeyDown", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    cmd(ws, "Input.dispatchKeyEvent", type="keyUp", key="Escape", code="Escape", windowsVirtualKeyCode=27)
    time.sleep(0.7)

r = ev(ws, JSCLICK + """
(()=>{
  const cands=[...document.querySelectorAll('#pane-side *')].filter(el=>{
    const t=(el.innerText||'').trim();
    return t && t.split('\\n')[0].includes('בארכיון') && el.getBoundingClientRect().height<120 && el.getBoundingClientRect().height>25;
  });
  if(!cands.length) return 'NOT FOUND';
  const el=cands[cands.length-1];
  jsclick(el);
  return 'clicked: '+el.innerText.slice(0,40);
})()""")
print("archive:", json.dumps(r, ensure_ascii=False))
time.sleep(2)

names = []
seen = set()
for i in range(20):
    chunk = ev(ws, """(()=>{
      const rows=[...document.querySelectorAll('#pane-side [role="listitem"]')];
      return JSON.stringify(rows.map(el=>el.innerText.split('\\n').slice(0,2).join(' | ')).filter(Boolean));
    })()""")
    for n in json.loads(chunk or "[]"):
        if n not in seen:
            seen.add(n); names.append(n)
    ev(ws, "(()=>{const p=document.querySelector('#pane-side');if(p){p.scrollTop+=450;return p.scrollTop}return -1})()")
    time.sleep(0.7)

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_archive_names.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(names, f, ensure_ascii=False, indent=1)
print("saved", p, len(names))
