#!/usr/bin/env python
"""Reconstruct a session from its transcript: operator turns in full, assistant heads only.

Why this exists. Claude's internal compaction replaces the thread with a model-written
summary, and that summary is lossy in a specific direction: it keeps what the model
judged important and drops the operator's exact words. Every correction this session
turned on exact words ("the launcher shouldnt run specific lane", "dont touch pictures",
"i dont even use figma"), and a paraphrase of those is not the same instruction.

The transcript on disk is not lossy. This reads it directly.

state/prompt-tickets.jsonl cannot do this job: it stores text_sha and no prompt text, by
deliberate design, so it can prove 41 prompts happened and not what one of them said.

Filtering: hook feedback, system reminders, task notifications, local-command output and
tool results are excluded. They are harness chatter, not the conversation.

Usage:
  python tools/recall/session_recall.py --session <uuid> [--head 3] [--out FILE]
  python tools/recall/session_recall.py --latest [--head 3]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECT_DIR = (Path.home() / ".claude" / "projects" /
               "C--Users-shova-claude-setup")

# Harness chatter that is not conversation. Anchored at the start so a message that
# merely mentions one of these words is kept.
NOISE = re.compile(
    r"^\s*(?:Stop hook feedback|Caveat: The messages below|"
    r"\[Request interrupted|\[SYSTEM NOTIFICATION|<system-reminder>|"
    r"<task-notification>|<local-command|<command-name>|"
    r"This session is being continued|\(Re-invocation of)",
    re.I,
)


def text_of(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_tool_result(msg: dict) -> bool:
    c = msg.get("content")
    if isinstance(c, list):
        return any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
    return False


def head(text: str, n: int) -> str:
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines[:n])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--head", type=int, default=3,
                    help="lines of each assistant turn to keep")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.latest or not a.session:
        files = sorted(PROJECT_DIR.glob("*.jsonl"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            print("no transcripts under", PROJECT_DIR)
            return 1
        path = files[0]
    else:
        path = PROJECT_DIR / (a.session + ".jsonl")
    if not path.is_file():
        print("no such transcript:", path)
        return 1

    turns = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        role = ev.get("type")
        if role not in ("user", "assistant"):
            continue
        msg = ev.get("message") or {}
        if is_tool_result(msg):
            continue
        t = text_of(msg).strip()
        if not t or NOISE.match(t):
            continue
        turns.append((role, ev.get("timestamp", "")[:19], t))

    ops = [t for t in turns if t[0] == "user"]
    outs = [t for t in turns if t[0] == "assistant"]

    buf = []
    w = buf.append
    w("# Session recall: {}".format(path.name))
    w("")
    w("Source: the transcript on disk, {:,} bytes. NOT a model summary.".format(
        path.stat().st_size))
    w("Operator turns: {}. Assistant turns: {} (first {} lines each).".format(
        len(ops), len(outs), a.head))
    if turns:
        w("Span: {} to {}".format(turns[0][1], turns[-1][1]))
    w("")
    n_op = 0
    for role, ts, t in turns:
        if role == "user":
            n_op += 1
            w("")
            w("## [{}] OPERATOR {}".format(ts, n_op))
            w("")
            w(" ".join(t.split()))
        else:
            w("")
            w("    > " + head(t, a.head).replace("\n", "\n    > "))

    text = "\n".join(buf)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print("wrote {} ({:,} bytes, {} operator turns)".format(
            a.out, len(text.encode("utf-8")), len(ops)))
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
