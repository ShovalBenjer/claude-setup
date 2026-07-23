# -*- coding: utf-8 -*-
"""Drive `claude setup-token` in a Windows PTY, robustly.
Feeder thread: waits until the 'paste code' prompt actually appears in the output,
THEN types the code char-by-char with small delays (how readline reliably accepts
input) and sends CR. Strips any '#state' suffix. Token saved to token.txt, never printed.
"""
import os, re, time, pathlib, threading
from winpty import PtyProcess

d = pathlib.Path.home() / ".claude" / ".token-flow"
d.mkdir(parents=True, exist_ok=True)
out = d / "out.log"; codef = d / "code.txt"; tokf = d / "token.txt"; done = d / "done"
for f in (out, tokf, done):
    if f.exists(): f.unlink()

proc = PtyProcess.spawn("claude setup-token", dimensions=(40, 120))
TOKEN_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
state = {"buf": ""}
_stop = threading.Event()


def prompt_seen():
    b = state["buf"].lower().replace(" ", "")
    return "pastecode" in b or "code:" in b or "paste" in b


def feeder():
    fed = False
    while not _stop.is_set() and proc.isalive():
        if not fed and codef.exists() and prompt_seen():
            code = codef.read_text().strip()
            if code:
                time.sleep(0.8)
                for ch in code:
                    proc.write(ch)
                    time.sleep(0.03)
                time.sleep(0.3)
                proc.write("\r")
                fed = True
        time.sleep(0.3)


threading.Thread(target=feeder, daemon=True).start()

start = time.time()
while proc.isalive() and time.time() - start < 600:
    try:
        chunk = proc.read(2048)
    except Exception:
        chunk = ""
    if chunk:
        state["buf"] += chunk
        out.write_text(TOKEN_RE.sub("[TOKEN-CAPTURED]", state["buf"])[-8000:], encoding="utf-8", errors="replace")
        m = TOKEN_RE.search(state["buf"])
        if m and not tokf.exists():
            tokf.write_text(m.group(0), encoding="ascii")
    time.sleep(0.15)

_stop.set()
m = TOKEN_RE.search(state["buf"])
if m and not tokf.exists():
    tokf.write_text(m.group(0), encoding="ascii")
out.write_text(TOKEN_RE.sub("[TOKEN-CAPTURED]", state["buf"])[-8000:], encoding="utf-8", errors="replace")
done.write_text("exited")
