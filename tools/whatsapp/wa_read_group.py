# -*- coding: utf-8 -*-
"""Read the 'reminder for myself' WhatsApp group: reload, open archive if needed,
find group row, open, scroll history, extract messages. Read-only (clicks only)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CDP_TAB", "whatsapp")
from cdp_driver import page_ws, cmd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_reminder_group.json")
PAT = ["תזכורת", "עצמי", "reminder", "myself", "notes", "self"]

def ev(ws, expr):
    r = cmd(ws, "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    return r.get("result", {}).get("value")

JSCLICK = """function jsclick(el){
  for(const t of ['mousedown','mouseup','click']){
    el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window}));
  }
}"""

def rows(ws):
    return json.loads(ev(ws, """(()=>{
      const rs=[...document.querySelectorAll('#pane-side [role="row"]')];
      return JSON.stringify(rs.map((el,i)=>({i, t: el.innerText.split('\\n').slice(0,2).join(' | ')})));
    })()""") or "[]")

def click_row_by_text(ws, needle):
    return ev(ws, JSCLICK + f"""
    (()=>{{
      const rs=[...document.querySelectorAll('#pane-side [role="row"]')];
      for(const el of rs){{
        if((el.innerText||'').includes({json.dumps(needle)})){{
          const cell = el.querySelector('[role="gridcell"]') || el;
          jsclick(cell.firstElementChild || cell);
          jsclick(el);
          return 'clicked '+el.innerText.split('\\n')[0];
        }}
      }}
      return 'NOT FOUND';
    }})()""")

ws, tab = page_ws()
cmd(ws, "Page.enable")
cmd(ws, "Page.navigate", url="https://web.whatsapp.com")
time.sleep(14)

all_rows = rows(ws)
print("main rows:", len(all_rows))

def find_target(rlist):
    for r in rlist:
        low = r["t"].lower()
        if any(p in low for p in PAT):
            return r
    return None

target = find_target(all_rows)
where = "main"
if not target:
    # scroll main list to collect more rows
    seen = {r["t"] for r in all_rows}
    for _ in range(15):
        ev(ws, "(()=>{const p=document.querySelector('#pane-side');if(p){p.scrollTop+=450}})()")
        time.sleep(0.6)
        for r in rows(ws):
            if r["t"] not in seen:
                seen.add(r["t"]); all_rows.append(r)
        target = find_target(all_rows)
        if target: break
if not target:
    # open archive
    print(ev(ws, JSCLICK + """
    (()=>{
      const els=[...document.querySelectorAll('#pane-side button, #pane-side [role="button"], #pane-side div')];
      for(const el of els){
        const t=(el.innerText||'').trim().split('\\n')[0];
        const h=el.getBoundingClientRect().height;
        if(t==='בארכיון' && h>15 && h<120){ jsclick(el); return 'archive clicked'; }
      }
      return 'archive NOT FOUND';
    })()"""))
    time.sleep(2.5)
    arch_rows = rows(ws)
    seen = {r["t"] for r in arch_rows}
    for _ in range(15):
        ev(ws, "(()=>{const p=document.querySelector('#pane-side');if(p){p.scrollTop+=450}})()")
        time.sleep(0.6)
        for r in rows(ws):
            if r["t"] not in seen:
                seen.add(r["t"]); arch_rows.append(r)
    with open(os.path.join(os.path.dirname(OUT), "wa_archive_names.json"), "w", encoding="utf-8") as f:
        json.dump([r["t"] for r in arch_rows], f, ensure_ascii=False, indent=1)
    print("archive rows:", len(arch_rows))
    target = find_target(arch_rows)
    where = "archive"

if not target:
    print("TARGET NOT FOUND anywhere"); sys.exit(1)
print("TARGET:", json.dumps(target, ensure_ascii=False), "in", where)
print(click_row_by_text(ws, target["t"].split(" | ")[0]))
time.sleep(3)

# scroll conversation up to load history
for _ in range(10):
    ev(ws, """(()=>{
      const m=document.querySelector('#main');
      if(!m) return 'no-main';
      const scrollers=[...m.querySelectorAll('div')].filter(d=>d.scrollHeight>d.clientHeight+50);
      const s=scrollers[0];
      if(s){s.scrollTop=0;return 'ok'}
      return 'no-scroller';
    })()""")
    time.sleep(1.2)

msgs = ev(ws, """(()=>{
  const main=document.querySelector('#main');
  if(!main) return JSON.stringify({error:'no #main'});
  const out=[];
  for(const row of main.querySelectorAll('[data-pre-plain-text], .message-in, .message-out')){
    const pre=row.getAttribute?row.getAttribute('data-pre-plain-text'):null;
    const el=row.querySelector?(row.querySelector('span.selectable-text')||row):row;
    const txt=(el.innerText||'').trim();
    if(txt) out.push({meta:pre, text:txt.slice(0,1000)});
  }
  const ded=[];
  for(const m of out){ if(!ded.length||ded[ded.length-1].text!==m.text) ded.push(m); }
  return JSON.stringify({title:(main.querySelector('header')?.innerText||'').split('\\n')[0], count:ded.length, messages:ded});
})()""")
data = json.loads(msgs or "{}")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print("SAVED", OUT, "count:", data.get("count"), "title:", json.dumps(data.get("title"), ensure_ascii=False))
