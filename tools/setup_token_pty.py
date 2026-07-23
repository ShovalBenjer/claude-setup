# -*- coding: utf-8 -*-
"""Drive `claude setup-token` in a real Windows PTY.
Writes screen output to ~/.claude/.token-flow/out.log (token scrubbed),
waits for ~/.claude/.token-flow/code.txt, types the code, saves the token
to token.txt (never printed). Marker file `done` on exit."""
import os, re, time, pathlib
from winpty import PtyProcess

d = pathlib.Path.home() / ".claude" / ".token-flow"
d.mkdir(parents=True, exist_ok=True)
out = d / "out.log"; codef = d / "code.txt"; tokf = d / "token.txt"; done = d / "done"
for f in (out, tokf, done):
    if f.exists(): f.unlink()

proc = PtyProcess.spawn("claude setup-token", dimensions=(40, 120))
buf = ""
fed = False
TOKEN_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")
start = time.time()
while proc.isalive() and time.time() - start < 600:
    try:
        chunk = proc.read(4096)
    except Exception:
        chunk = ""
    if chunk:
        buf += chunk
        scrubbed = TOKEN_RE.sub("[TOKEN-CAPTURED]", buf)
        out.write_text(scrubbed[-8000:], encoding="utf-8", errors="replace")
        m = TOKEN_RE.search(buf)
        if m and not tokf.exists():
            tokf.write_text(m.group(0), encoding="ascii")
    if not fed and codef.exists():
        code = codef.read_text().strip()
        if code:
            proc.write(code + "\r")
            fed = True
    time.sleep(0.3)
# final scrub + save
m = TOKEN_RE.search(buf)
if m and not tokf.exists():
    tokf.write_text(m.group(0), encoding="ascii")
out.write_text(TOKEN_RE.sub("[TOKEN-CAPTURED]", buf)[-8000:], encoding="utf-8", errors="replace")
done.write_text("exited")
