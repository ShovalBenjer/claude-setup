#!/usr/bin/env python3
"""Session dashboard: a LENS over on-disk state, owning nothing.

Pattern adopted from amirfish1/claude-command-center (docs/analysis/
2026-08-13-repo-compare-ui-ux.md): the transcript tree is the source of truth,
the dashboard only reads. Sources: ~/.claude/projects/*/*.jsonl (Claude Code's
own transcripts) and this repo's state/*.jsonl ledgers. Stdlib only, per the
repo convention (no server frameworks, no deps).

Run:  python3 tools/dashboard/serve.py [--port 8377]
Then open http://localhost:8377 . /events is an SSE stream re-polling every
2s; the page updates live without a refresh.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLAUDE_DIR = os.path.expanduser("~/.claude")
HERE = os.path.dirname(os.path.abspath(__file__))

# A session whose transcript grew in the last N seconds counts as active.
ACTIVE_WINDOW_S = 120
# The last assistant line ending in a question, or a pending permission ask,
# reads as needs-you. Heuristic on purpose: the transcript is the only truth
# we have, and a wrong "needs you" costs a glance, not a wrong action.
NEEDS_YOU_MARKERS = ("needs input:", "NEEDS OPERATOR", "AskUserQuestion")


def _tail_lines(path: str, max_bytes: int = 65536) -> list[str]:
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.seek(max(0, size - max_bytes))
            return fh.read().decode("utf-8", "replace").splitlines()[1:]
    except OSError:
        return []


def _last_assistant_text(lines: list[str]) -> str:
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content
                     if isinstance(c, dict) and c.get("type") == "text"]
            joined = " ".join(t for t in texts if t).strip()
            if joined:
                return joined[-500:]
    return ""


def sessions() -> list[dict]:
    """Every transcript under ~/.claude/projects, newest activity first."""
    rows = []
    projects = os.path.join(CLAUDE_DIR, "projects")
    if not os.path.isdir(projects):
        return rows
    now = time.time()
    for proj in sorted(os.listdir(projects)):
        pdir = os.path.join(projects, proj)
        if not os.path.isdir(pdir):
            continue
        for name in os.listdir(pdir):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(pdir, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            age = now - mtime
            if age > 86400 * 3:  # older than 3 days: not worth a row
                continue
            lines = _tail_lines(path)
            last = _last_assistant_text(lines)
            needs_you = any(m in last for m in NEEDS_YOU_MARKERS)
            rows.append({
                "project": proj.replace("-home-shov-", "").strip("-"),
                "session": name[:-6][:12],
                "age_s": int(age),
                "active": age < ACTIVE_WINDOW_S,
                "needs_you": needs_you,
                "last": last[-240:],
            })
    rows.sort(key=lambda r: r["age_s"])
    return rows[:40]


def ledgers() -> dict:
    """Headline counts from the harness's own state ledgers, if present."""
    out = {}
    repo_state = os.path.abspath(os.path.join(HERE, "..", "..", "state"))
    for name in ("gate-runs.jsonl", "skill-use.jsonl", "agent-spawns.jsonl"):
        path = os.path.join(repo_state, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = [l for l in fh if l.strip()]
            out[name] = {"rows": len(lines)}
            if name == "gate-runs.jsonl" and lines:
                last = json.loads(lines[-1])
                out[name]["last_verdict"] = last.get("verdict")
                out[name]["blocking"] = last.get("blocking")
        except (OSError, ValueError):
            out[name] = {"rows": 0}
    return out


def snapshot() -> dict:
    return {"ts": int(time.time()), "sessions": sessions(), "ledgers": ledgers()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet by default; this is a lens, not a logger
        pass

    def _send(self, code: int, ctype: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as fh:
                    self._send(200, "text/html; charset=utf-8", fh.read())
            except OSError:
                self._send(500, "text/plain", b"index.html missing next to serve.py")
        elif self.path == "/api/snapshot":
            self._send(200, "application/json",
                       json.dumps(snapshot()).encode())
        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    payload = json.dumps(snapshot())
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(2)
            except (BrokenPipeError, ConnectionResetError):
                return
        else:
            self._send(404, "text/plain", b"not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8377)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"session dashboard: http://localhost:{args.port}  (ctrl-c stops)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
