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

DELIVERY RULE, and why it is not "skip your own lane":
  The first version filtered out any message whose from_lane equalled the
  reading lane, on the theory that a session should not be shown its own
  sends. That filter made 8 of the first 9 messages on this bus permanently
  undeliverable: lane B had addressed them to lane B as durable notes for its
  own later sessions, and no lane B session could ever read them. The cursor
  already provides exactly-once, so the filter was guarding a property that
  was not at risk and destroying one that mattered.

  A message addressed to a lane is delivered to that lane. The only cost is
  that a session which sends to its own lane sees that message once on its
  next inbox read, because a per-lane cursor cannot distinguish two sessions
  in the same lane. CLAUDE_SESSION_ID is not exported into the hook
  environment on this machine, so from_session is recorded but always empty
  and must not be used as a filter key.

  bus.py send --to C --kind ask --subject "..." --body "..."
  bus.py inbox                 # unread for THIS lane, advances the cursor
  bus.py inbox --peek          # unread, cursor untouched
  bus.py log --tail 20
  bus.py whoami
  bus.py selftest              # plants known traffic and asserts delivery
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


def append_row(rec: dict) -> None:
    """Append one message, healing a torn predecessor first.

    A crashed write leaves a partial line with no trailing newline. The next
    append would concatenate onto it, so the combined line fails to parse and
    ONE crashed write silently eats TWO messages: the fragment and its
    successor. Writing a newline first confines the damage to the fragment.
    Found by bus.py selftest; the docstring had claimed torn lines were already
    handled, and they were only half handled.
    """
    BUS.parent.mkdir(parents=True, exist_ok=True)
    try:
        if BUS.exists() and BUS.stat().st_size:
            with BUS.open("rb") as fh:
                fh.seek(-1, os.SEEK_END)
                torn = fh.read(1) != b"\n"
            if torn:
                with BUS.open("ab") as fh:
                    fh.write(b"\n")
    except OSError:
        pass
    with BUS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


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
    append_row(rec)
    print(f"sent {rec['id']} {lane} -> {rec['to']} [{rec['kind']}] {rec['subject']}")
    return 0


def cmd_inbox(a: argparse.Namespace) -> int:
    """Deliver unread messages for this lane.

    Registered directly as a SessionStart and UserPromptSubmit hook, so it must
    never exit nonzero: a UserPromptSubmit hook that fails blocks the operator's
    prompt, and an A2A bus that can wedge a session is worse than no bus. Every
    failure path returns 0 with no output. The selftest still catches real
    breakage because it asserts on delivered CONTENT, not on the exit code.
    """
    try:
        return _inbox(a)
    except Exception:  # noqa: BLE001
        return 0


def _inbox(a: argparse.Namespace) -> int:
    lane = a.lane or lane_for(os.getcwd())
    rows = read_all()
    start = get_cursor(lane)
    # Addressed to this lane, or broadcast. Deliberately NOT filtered on
    # from_lane: see the DELIVERY RULE in the module docstring.
    fresh = [r for r in rows[start:] if r.get("to") in (lane, "ALL")]
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


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Plant known traffic on a throwaway bus and assert what comes back.

    Every case here is a property this bus had already broken in production or
    could break silently: the self-lane message that was undeliverable, the
    cursor that must make delivery exactly-once, the torn line that must not
    crash a hook running on every prompt.
    """
    import io
    import shutil
    import tempfile
    from contextlib import redirect_stdout

    global BUS, CURSORS
    real_bus, real_cursors = BUS, CURSORS
    tmp = Path(tempfile.mkdtemp(prefix="bus-selftest-"))
    BUS, CURSORS = tmp / "bus.jsonl", tmp / "cursors"

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print("  [{}] {}{}".format("ok" if ok else "FAIL", name,
                                   "" if ok else "  <- " + detail))
        if not ok:
            failures.append(name)

    def plant(from_lane: str, to: str, subject: str) -> None:
        # Goes through append_row, the same path cmd_send uses, so the torn-line
        # case below tests production behaviour and not the test's own writer.
        append_row({
            "id": subject, "ts": now_iso(), "from_lane": from_lane,
            "from_session": "", "to": to, "kind": "fact",
            "subject": subject, "body": "b", "refs": [],
        })

    def inbox(lane: str, peek: bool = False) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_inbox(argparse.Namespace(lane=lane, peek=peek))
        return buf.getvalue()

    try:
        print("bus.py selftest")

        # The regression that motivated this selftest. Lane B addressed 8 real
        # messages to lane B; the old from_lane filter dropped every one.
        plant("B", "B", "self-lane-note")
        out = inbox("B", peek=True)
        check("self-lane message is delivered to its own lane",
              "self-lane-note" in out,
              "a lane cannot leave durable notes for its own later sessions")

        # Addressing must still be honoured.
        plant("B", "C", "for-c-only")
        check("message addressed to C is not delivered to D",
              "for-c-only" not in inbox("D", peek=True))
        check("message addressed to C is delivered to C",
              "for-c-only" in inbox("C", peek=True))

        # Broadcast.
        plant("A", "ALL", "broadcast-msg")
        check("ALL is delivered to an unrelated lane",
              "broadcast-msg" in inbox("D", peek=True))

        # --peek must not consume.
        before = get_cursor("C")
        inbox("C", peek=True)
        check("--peek leaves the cursor untouched", get_cursor("C") == before,
              "cursor moved {} -> {}".format(before, get_cursor("C")))

        # Exactly-once: a real read consumes, a second read returns nothing.
        first = inbox("C")
        second = inbox("C")
        check("a real read delivers", "for-c-only" in first)
        check("the same message is not delivered twice", second.strip() == "",
              "second read returned: " + second[:80])

        # A torn concurrent append must not crash the reader, because this runs
        # as a hook on every prompt and a crashing hook blocks the session.
        with BUS.open("a", encoding="utf-8") as fh:
            fh.write('{"to": "D", "subj')  # no newline, truncated mid-object
        plant("A", "D", "after-torn-line")
        try:
            out = inbox("D", peek=True)
            check("a torn line is skipped, not fatal", "after-torn-line" in out,
                  "reader stopped at the torn line")
        except Exception as exc:  # noqa: BLE001
            check("a torn line is skipped, not fatal", False, repr(exc))

        # Lane derivation is by longest prefix, so a nested path is not stolen.
        check("cwd inside claude-setup derives lane B",
              lane_for(r"c:\users\shova\claude-setup\tools\bus") == "B")
        check("cwd inside new-recruit derives lane C",
              lane_for(r"c:\users\shova\downloads\new-recruit") == "C")
        check("an unmapped cwd falls back to lane A",
              lane_for(r"c:\windows\temp") == "A")

        # A corrupt cursor must not wedge the bus.
        set_cursor("D", 0)
        cursor_path("D").write_text("not-a-number", encoding="utf-8")
        check("a corrupt cursor reads as 0 rather than raising",
              get_cursor("D") == 0)
    finally:
        BUS, CURSORS = real_bus, real_cursors
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print("FAILED {}: {}".format(len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
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

    t = sub.add_parser("selftest")
    t.set_defaults(func=cmd_selftest)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
