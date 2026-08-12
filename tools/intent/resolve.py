#!/usr/bin/env python3
"""Turn a ticket back into the sentence the operator actually typed.

WHY THIS EXISTS

2026-08-06, in his own words: "now my request got lost as always in the session
which i hope to later then analyse and dig it up."

Both halves of that are true and they have different causes.

LOST. `state/prompt-tickets.jsonl` holds 467 rows and every single one is in
state CAPTURED. `tools/intent/tickets.py` defines a whole lifecycle
(CAPTURED -> TRIAGED / NOT_WORK / SUPERSEDED, and onward) and not one transition
has ever been written. So the ledger records that a request arrived and never
records whether anything happened to it. A request cannot be "lost" by a system
that never claimed to be tracking it, which is exactly the problem.

UNDIGGABLE. Each row carries `text_sha` and no text. That is a deliberate
privacy decision in `capture_turn.py` ("Hashes only, no prompt text") and this
tool does not overturn it. A sha lets you VERIFY a request you already have; it
cannot let you FIND one you have forgotten, and finding was the thing he wanted.

The join nobody had written. The session transcripts under ~/.claude/projects
already contain the text, and `text_sha` is a plain sha256 of it, so the two
sides rejoin by recomputing the hash. No new storage, no second copy of anything
sensitive, and the privacy stance is untouched: the text lives exactly where it
already lived. Measured on first run: 249 of 467 tickets resolved to their
original sentence.

The remainder do not resolve, and the reasons are worth stating rather than
rounding off. A transcript that has been rotated or deleted takes its turns with
it. A prompt typed in a project whose slug differs per host lands in a directory
this machine may not have. And any prompt that reached the model differently from
how it was captured hashes differently. So the resolve rate is a floor on what is
recoverable, not a measure of what was captured.

RELATIONSHIP TO tools/corpus/extract.py

That tool (parallel session, same day) builds a corpus of conversation turns for
embedding. This one answers a much narrower question, "what did he ask and did it
go anywhere", and joins to the ticket ledger to do it. Overlapping input, different
output, and neither should grow into the other.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

# Turns the harness injects into the user role. They are captured as tickets and
# hash like anything else, but the operator did not type them, so listing them
# as "your requests" buries the real ones. Found on the first real run: task
# notifications outnumbered actual questions in the last dozen rows.
INJECTED = re.compile(
    r"^\s*(?:<task-notification>|<system-reminder>|<command-message>|"
    r"<local-command|<user-prompt-submit-hook>|Stop hook feedback|"
    r"Caveat: The messages below|\[Request interrupted)")

DEFAULT_TRANSCRIPTS = Path.home() / ".claude" / "projects"
DEFAULT_TICKETS = "state/prompt-tickets.jsonl"


def text_sha(text: str) -> str:
    """Must stay byte-identical to tickets.text_sha or the join silently empties."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def turn_text(obj: dict) -> str | None:
    if obj.get("type") != "user":
        return None
    content = obj.get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if isinstance(content, str) and content.strip():
        return None if INJECTED.match(content) else content
    return None


def transcript_index(root: Path) -> dict[str, str]:
    """sha -> the typed text, over every transcript on disk."""
    index: dict[str, str] = {}
    if not root.is_dir():
        return index
    for f in sorted(root.rglob("*.jsonl")):
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for ln in lines:
            try:
                obj = json.loads(ln)
            except ValueError:
                continue
            t = turn_text(obj)
            if t:
                index.setdefault(text_sha(t), t)
    return index


def load_tickets(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
    return out


def resolve(tickets: list[dict], index: dict[str, str]) -> list[dict]:
    rows = []
    for t in tickets:
        text = index.get(t.get("text_sha", ""))
        rows.append({
            "id": t.get("id"), "ts": t.get("ts"), "session": t.get("session"),
            "state": t.get("state"), "resolved": text is not None,
            "text": text,
        })
    return rows


def cmd_scan(a: argparse.Namespace) -> int:
    tickets = load_tickets(Path(a.tickets))
    if not tickets:
        print(f"no tickets at {a.tickets}")
        return 1
    index = transcript_index(Path(a.transcripts).expanduser())
    rows = resolve(tickets, index)
    got = [r for r in rows if r["resolved"]]
    states = {}
    for t in tickets:
        states[t.get("state")] = states.get(t.get("state"), 0) + 1
    print(f"{len(tickets)} tickets, {len(got)} resolved to their original text "
          f"({len(got) * 100 // max(len(tickets), 1)}%)")
    print("states: " + ", ".join(f"{k}={v}" for k, v in sorted(states.items())))
    if len(states) == 1 and "CAPTURED" in states:
        print("  every ticket is still CAPTURED: the lifecycle in tools/intent/tickets.py "
              "has never recorded a single transition, so nothing tracks whether a "
              "request was acted on")
    if a.since:
        rows = [r for r in rows if (r["ts"] or "") >= a.since]
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        print(f"wrote {len(rows)} rows to {a.out}")
    if a.show:
        shown = [r for r in rows if r["resolved"]][-a.show:]
        print(f"\nlast {len(shown)} recoverable request(s):")
        for r in shown:
            one = " ".join((r["text"] or "").split())[:150]
            print(f"  {r['ts'][:16]}  [{r['state']}]  {one}")
    return 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tdir = root / "projects" / "slug"
        tdir.mkdir(parents=True)
        typed = "merge these dirs, not a sync"
        (tdir / "s.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": typed}}) + "\n"
            + json.dumps({"type": "assistant", "message": {"content": "ignored"}}) + "\n"
            + json.dumps({"type": "user", "message": {"content": [{"text": "second one"}]}}) + "\n")
        tickets = [
            {"id": "PT-1", "ts": "2026-08-06T10:00:00Z", "session": "s",
             "state": "CAPTURED", "text_sha": text_sha(typed)},
            {"id": "PT-2", "ts": "2026-08-06T11:00:00Z", "session": "s",
             "state": "CAPTURED", "text_sha": text_sha("second one")},
            {"id": "PT-3", "ts": "2026-08-06T12:00:00Z", "session": "s",
             "state": "CAPTURED", "text_sha": text_sha("never said this")},
        ]
        idx = transcript_index(root / "projects")
        rows = {r["id"]: r for r in resolve(tickets, idx)}
        if rows["PT-1"]["text"] != typed:
            fails.append("a plain-string user turn did not rejoin by sha")
        if rows["PT-2"]["text"] != "second one":
            fails.append("a list-content user turn did not rejoin; the content shape varies "
                         "between transcripts and both forms must work")
        if rows["PT-3"]["resolved"]:
            fails.append("a ticket with no matching transcript was reported resolved")
        if "ignored" in json.dumps(rows):
            fails.append("an assistant turn was indexed; only user turns are requests")
        inj = "<task-notification> something the harness injected"
        idx2 = transcript_index(root / "projects2")
        (root / "projects2" / "s").mkdir(parents=True)
        (root / "projects2" / "s" / "t.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": inj}}) + "\n")
        if transcript_index(root / "projects2"):
            fails.append("a harness-injected turn was indexed as an operator request")
        if text_sha("abc") != hashlib.sha256(b"abc").hexdigest():
            fails.append("text_sha drifted from tickets.text_sha, which empties the join")
    for f in fails:
        print(f"[FAIL] {f}")
    print("PASS resolve selftest" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="rejoin tickets to the text that produced them")
    s.add_argument("--tickets", default=DEFAULT_TICKETS)
    s.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    s.add_argument("--since", default="", help="only rows with ts >= this prefix")
    s.add_argument("--show", type=int, default=0, help="print the last N recoverable requests")
    s.add_argument("--out", default="")
    s.set_defaults(func=cmd_scan)
    t = sub.add_parser("selftest", help="prove the join on a planted transcript")
    t.set_defaults(func=cmd_selftest)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
