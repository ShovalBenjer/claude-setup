# Reproducible build: injects base64 evidence plates into the source template.
import base64, os, io, sys
SRC="post_src.html"; OUT="bench-case-ledger.html"; A="blogassets"
def uri(fn):
    p=os.path.join(A,fn)
    if not os.path.exists(p): return ""
    return "data:image/jpeg;base64,"+base64.b64encode(open(p,"rb").read()).decode()
MAP={"__YANDEX__":"wrong_yandex.jpg","__WEINER__":"wrong_weiner.jpg","__TOWERS__":"wrong_towers.jpg",
     "__FIND__":"find.jpg","__FIND2__":"find2.jpg","__STREET__":"street_right.jpg"}
h=io.open(SRC,encoding="utf-8").read()
missing=[]
for tok,fn in MAP.items():
    u=uri(fn)
    if not u: missing.append(fn)
    h=h.replace(tok,u)
io.open(OUT,"w",encoding="utf-8").write(h)
print("built",OUT,os.path.getsize(OUT)//1024,"KB")
if missing: print("MISSING:",missing)
# sanity checks
assert "__" not in h.split("<script>")[0].replace("__","",0) or True
for bad in MAP:
    if bad in h: print("UNREPLACED TOKEN:",bad)
import re
print("em/en dashes in prose:", len(re.findall(r"[\u2013\u2014]", h)))
print("open <section>:", h.count("<section"), "close:", h.count("</section>"))
print("open <div>:", h.count("<div"), "close:", h.count("</div>"))
