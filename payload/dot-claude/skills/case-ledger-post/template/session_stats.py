import json, os, datetime, collections
P=r"C:\Users\shova\.claude\projects\C--Users-shova-Downloads-new-recruit\f551cbf4-2dd7-4fb2-8871-1780e6b4bd0a.jsonl"
print("size:", os.path.getsize(P)//1024, "KB")
tot=collections.Counter(); models=collections.Counter(); efforts=collections.Counter()
first=last=None; nmsg=0; tools=collections.Counter()
with open(P, encoding="utf-8") as f:
    for line in f:
        try: d=json.loads(line)
        except: continue
        nmsg+=1
        ts=d.get("timestamp")
        if ts:
            if not first: first=ts
            last=ts
        m=d.get("message") or {}
        if isinstance(m,dict):
            if m.get("model"): models[m["model"]]+=1
            u=m.get("usage") or {}
            for k in ("input_tokens","output_tokens","cache_creation_input_tokens","cache_read_input_tokens"):
                if u.get(k): tot[k]+=u[k]
            c=m.get("content")
            if isinstance(c,list):
                for b in c:
                    if isinstance(b,dict) and b.get("type")=="tool_use":
                        tools[b.get("name","?")]+=1
print("records:",nmsg)
print("first:",first)
print("last:",last)
if first and last:
    a=datetime.datetime.fromisoformat(first.replace("Z","+00:00"))
    b=datetime.datetime.fromisoformat(last.replace("Z","+00:00"))
    dur=(b-a)
    print("wall duration:",dur, "=", round(dur.total_seconds()/3600,2),"h")
print("\nTOKENS:")
for k,v in tot.items(): print(f"  {k}: {v:,}")
print(f"  TOTAL billable-ish (in+out): {tot['input_tokens']+tot['output_tokens']:,}")
print(f"  TOTAL incl cache: {sum(tot.values()):,}")
print("\nMODELS:", dict(models))
print("\nTOP TOOLS:", dict(tools.most_common(12)))
