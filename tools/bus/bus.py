#!/usr/bin/env python3
"""Cross-terminal A2A bus for parallel Claude Code sessions.

Six terminals run at once and none can see the others. Today the operator IS
the message bus: he copy-pastes one session's question into another session's
prompt. This is that bus, made durable and automatic.

Design constraints that came from real failures:
  - Lane is DERIVED from cwd, never declared. A session that must remember to
    announce itself will forget (23 personas sat undeployed for the same
    reason: the step that required someone to remember never ran).
  - Append-only JSONL. No lock, no db, no daemon. Concurrent appends of a
    single short line are atomic enough on NTFS at this volume.
  - Per-lane read cursor, so a session sees each message exactly once and a
    long-running session does not re-read its whole inbox every prompt.
  - Reading is a hook, not a habit. If it needs the operator to run a command,
    it is not a bus.

  bus.py send --to C --kind ask --subject "..." --body "..."
  bus.py inbox                 # unread for THIS lane, advances the cursor
  bus.py inbox --peek          # unread, cursor untouched
  bus.py log --tail 20
  bus.py whoami
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUS = ROOT / "state" / "bus.jsonl"
CURSORS = ROOT / "state" / "bus-cursors"

# cwd prefix -> lane. Longest match wins, so a nested dir cannot be stolen by
# a shorter prefix. Lowercase compare: Windows paths vary in case.
LANE_MAP = {
    r"c:\users\shova\claude-setup": "B",
    r"c:\users\shova\downloads\new-recruit": "C",
    r"c:\users\shova\daily-deep-learning": "D",
    r"c:\users\shova\projects\daily-deep-learning": "D",
}
DEFAULT_LANE = "A"

LANE_NAMES = {
    "A": "concierge",
    "B": "claude-setup harness",
    "C": "resume / hiring engine",
    "D": "learning (hasadna)",
}

KINDS = ("fact", "ask", "answer", "claim", "warn", "done")


def lane_for(cwd: str) -> str:
    c = str(Path(cwd).resolve()).lower().rstrip("\\/")
    best, best_len = DEFAULT_LANE, -1
    for prefix, lane in LANE_MAP.items():
        p = prefix.lower().rstrip("\\/")
        if (c == p or c.startswith(p + "\\") or c.startswith(p + "/")) and len(p) > best_len:
            best, best_len = lane, len(p)
    return best


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_all() -> list[dict]:
    if not BUS.exists():
        return []
    out = []
    for line in BUS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A torn concurrent append. Skip the row, never crash the hook that
            # reads this file on every prompt. Silence here is deliberate: a
            # hook that errors blocks the session.
            continue
    return out


def cursor_path(lane: str) -> Path:
    return CURSORS / f"{lane}.txt"


def get_cursor(lane: str) -> int:
    p = cursor_path(lane)
    if not p.exists():
        return 0
    try:
        return int(p.read_text(encoding="utf-8").strip() or 0)
    except ValueError:
        return 0


def set_cursor(lane: str, n: int) -> None:
    CURSORS.mkdir(parents=True, exist_ok=True)
    cursor_path(lane).write_text(str(n), encoding="utf-8")


def cmd_send(a: argparse.Namespace) -> int:
    lane = a.from_lane or lane_for(os.getcwd())
    rec = {
        "id": f"{int(time.time())}-{uuid.uuid4().hex[:6]}",
        "ts": now_iso(),
        "from_lane": lane,
        "from_session": os.environ.get("CLAUDE_SESSION_ID", "")[:8],
        "to": a.to.upper() if a.to.lower() != "all" else "ALL",
        "kind": a.kind,
        "subject": a.subject,
        "body": a.body,
        "refs": [r for r in (a.ref or []) if r],
    }
    BUS.parent.mkdir(parents=True, exist_ok=True)
    with BUS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"sent {rec['id']} {lane} -> {rec['to']} [{rec['kind']}] {rec['subject']}")
    return 0


def cmd_inbox(a: argparse.Namespace) -> int:
    lane = a.lane or lane_for(os.getcwd())
    rows = read_all()
    start = get_cursor(lane)
    fresh = [
        r for r in rows[start:]
        if r.get("to") in (lane, "ALL") and r.get("from_lane") != lane
    ]
    if not a.peek:
        set_cursor(lane, len(rows))
    if not fresh:
        return 0
    print(f"=== A2A INBOX: lane {lane} ({LANE_NAMES.get(lane, '?')}), {len(fresh)} unread ===")
    for r in fresh:
        print(f"[{r.get('kind','?')}] from lane {r.get('from_lane','?')} {r.get('ts','')}")
        print(f"  {r.get('subject','')}")
        body = (r.get("body") or "").strip()
        for ln in body.splitlines():
            print(f"  {ln}")
        for ref in r.get("refs") or []:
            print(f"  ref: {ref}")
        print(f"  reply: bus.py send --to {r.get('from_lane')} --kind answer --subject \"re: {r.get('subject','')}\" --body \"...\"")
        print()
    return 0


def cmd_log(a: argparse.Namespace) -> int:
    rows = read_all()
    for r in rows[-a.tail:]:
        print(f"{r.get('ts','')} {r.get('from_lane','?')}->{r.get('to','?')} [{r.get('kind','?')}] {r.get('subject','')}")
    return 0


def cmd_whoami(_a: argparse.Namespace) -> int:
    lane = lane_for(os.getcwd())
    rows = read_all()
    print(f"cwd:    {os.getcwd()}")
    print(f"lane:   {lane} ({LANE_NAMES.get(lane, '?')})")
    print(f"bus:    {BUS} ({len(rows)} messages)")
    print(f"cursor: {get_cursor(lane)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="bus.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send")
    s.add_argument("--to", required=True, help="lane letter or 'all'")
    s.add_argument("--kind", default="fact", choices=KINDS)
    s.add_argument("--subject", required=True)
    s.add_argument("--body", required=True)
    s.add_argument("--ref", action="append", help="file path, URL, or command (repeatable)")
    s.add_argument("--from-lane", dest="from_lane", help="override derived lane")
    s.set_defaults(func=cmd_send)

    i = sub.add_parser("inbox")
    i.add_argument("--lane")
    i.add_argument("--peek", action="store_true")
    i.set_defaults(func=cmd_inbox)

    l = sub.add_parser("log")
    l.add_argument("--tail", type=int, default=20)
    l.set_defaults(func=cmd_log)

    w = sub.add_parser("whoami")
    w.set_defaults(func=cmd_whoami)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
