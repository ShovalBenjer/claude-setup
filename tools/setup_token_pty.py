# -*- coding: utf-8 -*-
"""Drive `claude setup-token` in a Windows PTY, robustly.
Feeder thread: waits until the 'paste code' prompt actually appears in the output,
THEN types the code char-by-char with small delays (how readline reliably accepts
input) and sends CR. The code file's content is fed verbatim minus surrounding
whitespace. Token saved to token.txt, never printed: every write to out.log passes
through redact() first.

The PTY work is Windows-only (winpty is declared in no manifest here, a documented
build-domain exclusion), so everything importable lives at module level with no side
effects and the procedural flow runs only under __main__. tests/test_setup_token_pty.py
pins the pure pieces on any host.
"""
import os
import pathlib
import re
import threading
import time

TOKEN_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")


def redact(buf):
    """The last 8000 chars of the buffer with every token shape replaced."""
    return TOKEN_RE.sub("[TOKEN-CAPTURED]", buf)[-8000:]


def prompt_seen(buf):
    b = buf.lower().replace(" ", "")
    return "pastecode" in b or "code:" in b or "paste" in b


def main():
    from winpty import PtyProcess

    d = pathlib.Path.home() / ".claude" / ".token-flow"
    d.mkdir(parents=True, exist_ok=True)
    out = d / "out.log"; codef = d / "code.txt"; tokf = d / "token.txt"; done = d / "done"
    for f in (out, tokf, done):
        if f.exists(): f.unlink()

    proc = PtyProcess.spawn("claude setup-token", dimensions=(40, 120))
    state = {"buf": ""}
    _stop = threading.Event()

    def feeder():
        fed = False
        while not _stop.is_set() and proc.isalive():
            if not fed and codef.exists() and prompt_seen(state["buf"]):
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
            out.write_text(redact(state["buf"]), encoding="utf-8", errors="replace")
            m = TOKEN_RE.search(state["buf"])
            if m and not tokf.exists():
                tokf.write_text(m.group(0), encoding="ascii")
        time.sleep(0.15)

    _stop.set()
    m = TOKEN_RE.search(state["buf"])
    if m and not tokf.exists():
        tokf.write_text(m.group(0), encoding="ascii")
    out.write_text(redact(state["buf"]), encoding="utf-8", errors="replace")
    done.write_text("exited")


if __name__ == "__main__":
    main()
