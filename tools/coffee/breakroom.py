#!/usr/bin/env python3
"""The breakroom board: the durable half of coffee v2 (taste row 2026-08-12).

Cross-session messages (SendMessage) are ephemeral and point-to-point; a session
that was not running misses them. The breakroom is the append-only board that
survives: any session posts one short note (a brag, a gripe, a "who owns X"), and
every session reads the last N at boot. This is where anything said over
SendMessage that matters past the moment gets written down. Ledger for memory,
messages for liveness.

Commands: post, read, selftest. Append-only state/breakroom.jsonl.
"""
import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "lib"))
try:
    from tracing import inject as trace_inject  # noqa: E402
except ImportError:
    def trace_inject(row):
        return row

BOARD = Path("state/breakroom.jsonl")
KINDS = ("brag", "gripe", "question", "note")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def append_row(board: Path, row: dict) -> None:
    trace_inject(row)
    board.parent.mkdir(parents=True, exist_ok=True)
    with board.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def read_rows(board: Path) -> list[dict]:
    if not board.exists():
        return []
    return [json.loads(l) for l in board.read_text().splitlines() if l.strip()]


def cmd_post(a) -> int:
    if a.kind not in KINDS:
        print(f"REJECT: kind must be one of {KINDS}", file=sys.stderr)
        return 1
    append_row(a.board, {"ts": now(), "session": a.session, "kind": a.kind,
                         "text": a.text})
    print("posted")
    return 0


def cmd_read(a) -> int:
    rows = read_rows(a.board)[-a.n:] if a.n else []
    for r in rows:
        print(f"{r['ts']}  [{r['kind']}] {r['session']}: {r['text']}")
    if not rows:
        print("(breakroom empty)")
    return 0


def selftest() -> int:
    import tempfile
    fails = 0

    def check(name, ok):
        nonlocal fails
        if not ok:
            fails += 1
            print(f"FAIL {name}")

    with tempfile.TemporaryDirectory() as td:
        board = Path(td) / "breakroom.jsonl"
        ns = argparse.Namespace(board=board, session="qa-lab", kind="gripe",
                                text="the runner orphaned three listeners")
        check("post ok", cmd_post(ns) == 0)
        bad = argparse.Namespace(board=board, session="x", kind="rant", text="y")
        check("bad kind rejected", cmd_post(bad) == 1)
        check("row lands", read_rows(board)[-1]["kind"] == "gripe")
        for i in range(5):
            cmd_post(argparse.Namespace(board=board, session="s", kind="note",
                                        text=f"n{i}"))
        check("read tail bounded", len(read_rows(board)) == 6)
    print(f"breakroom selftest: {fails} checks failed")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--board", type=Path, default=BOARD)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post")
    p.add_argument("--session", required=True)
    p.add_argument("--kind", required=True, help=f"one of {KINDS}")
    p.add_argument("--text", required=True)
    r = sub.add_parser("read")
    r.add_argument("-n", type=int, default=20)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    return {"post": cmd_post, "read": cmd_read}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
