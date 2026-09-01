#!/usr/bin/env python3
"""The futures board: sessions bet persona reputation on each other's riskiest assumptions.

Coffee-break v2, the stakes half (taste ledger row 2026-08-12). A session posts its
riskiest current assumption with a named falsifier; other sessions bet for or against;
settlement is manual but must carry evidence, and reputation is computed from the
ledger, never stored. Rows are append-only in state/futures.jsonl.

Commands: post, bet, settle, board, selftest. Exit 0 on success, 1 on a rejected
operation, 2 on usage error.
"""
import argparse
import fcntl
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "lib"))
try:
    from tracing import inject as trace_inject  # noqa: E402
except ImportError:
    def trace_inject(row):
        return row

LEDGER = Path("state/futures.jsonl")
START_REPUTATION = 100


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def read_rows(ledger: Path) -> list[dict]:
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]


def append_row(ledger: Path, row: dict) -> None:
    trace_inject(row)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def cmd_post(args, ledger: Path) -> int:
    row = {
        "kind": "post",
        "id": uuid.uuid4().hex[:12],
        "ts": now(),
        "session": args.session,
        "claim": args.claim,
        "falsifier": args.falsifier,
        "settle_by": args.settle_by,
    }
    append_row(ledger, row)
    print(row["id"])
    return 0


def cmd_bet(args, ledger: Path) -> int:
    if args.stake <= 0:
        print(f"REJECT: stake must be positive, got {args.stake}", file=sys.stderr)
        return 1
    rows = read_rows(ledger)
    posts = {r["id"] for r in rows if r["kind"] == "post"}
    settled = {r["id"] for r in rows if r["kind"] == "settle"}
    if args.id not in posts:
        print(f"REJECT: no post with id {args.id}", file=sys.stderr)
        return 1
    if args.id in settled:
        print(f"REJECT: post {args.id} is already settled", file=sys.stderr)
        return 1
    append_row(ledger, {
        "kind": "bet", "id": args.id, "ts": now(), "session": args.session,
        "side": args.side, "stake": args.stake,
    })
    print(f"bet recorded: {args.session} {args.side} {args.id} stake {args.stake}")
    return 0


def cmd_settle(args, ledger: Path) -> int:
    rows = read_rows(ledger)
    posts = {r["id"] for r in rows if r["kind"] == "post"}
    settled = {r["id"] for r in rows if r["kind"] == "settle"}
    if args.id not in posts:
        print(f"REJECT: no post with id {args.id}", file=sys.stderr)
        return 1
    if args.id in settled:
        print(f"REJECT: post {args.id} is already settled", file=sys.stderr)
        return 1
    append_row(ledger, {
        "kind": "settle", "id": args.id, "ts": now(),
        "outcome": args.outcome == "true", "evidence": args.evidence,
    })
    print(f"settled {args.id} outcome={args.outcome}")
    return 0


def standings(rows: list[dict]) -> dict[str, int]:
    outcomes = {r["id"]: r["outcome"] for r in rows if r["kind"] == "settle"}
    rep: dict[str, int] = {}
    for r in rows:
        if r["kind"] in ("post", "bet"):
            rep.setdefault(r["session"], START_REPUTATION)
        if r["kind"] == "bet" and r["id"] in outcomes:
            won = (r["side"] == "for") == outcomes[r["id"]]
            rep[r["session"]] += r["stake"] if won else -r["stake"]
    return rep


def cmd_board(args, ledger: Path) -> int:
    rows = read_rows(ledger)
    settled_ids = {r["id"] for r in rows if r["kind"] == "settle"}
    open_posts = [r for r in rows if r["kind"] == "post" and r["id"] not in settled_ids]
    print("open positions:")
    for p in open_posts:
        bets = [r for r in rows if r["kind"] == "bet" and r["id"] == p["id"]]
        print(f"  {p['id']}  {p['session']}: {p['claim']}  "
              f"(falsifier: {p['falsifier']}, settle by {p['settle_by']}, {len(bets)} bet(s))")
    print("reputation:")
    for session, rep in sorted(standings(rows).items(), key=lambda kv: -kv[1]):
        print(f"  {rep:>4}  {session}")
    return 0


def selftest() -> int:
    import tempfile
    failures = 0

    def check(name: str, ok: bool) -> None:
        nonlocal failures
        if not ok:
            failures += 1
            print(f"FAIL {name}")

    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "futures.jsonl"
        ns = argparse.Namespace(session="qa-lab", claim="gate stays green",
                                falsifier="gate-run", settle_by="2026-08-13")
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check("post exits 0", cmd_post(ns, ledger) == 0)
        pid = buf.getvalue().strip()
        check("post id is 12 hex chars", len(pid) == 12)
        neg = argparse.Namespace(id=pid, session="x", side="for", stake=-20)
        check("negative stake rejected", cmd_bet(neg, ledger) == 1)
        zero = argparse.Namespace(id=pid, session="x", side="for", stake=0)
        check("zero stake rejected", cmd_bet(zero, ledger) == 1)
        bet = argparse.Namespace(id=pid, session="eng-firm", side="against", stake=10)
        check("bet on open post accepted", cmd_bet(bet, ledger) == 0)
        ghost = argparse.Namespace(id="deadbeef", session="x", side="for", stake=1)
        check("bet on missing post rejected", cmd_bet(ghost, ledger) == 1)
        st = argparse.Namespace(id=pid, outcome="true", evidence="gate PASS row")
        check("settle with evidence accepted", cmd_settle(st, ledger) == 0)
        check("double settle rejected", cmd_settle(st, ledger) == 1)
        late = argparse.Namespace(id=pid, session="late", side="for", stake=5)
        check("bet after settle rejected", cmd_bet(late, ledger) == 1)
        rep = standings(read_rows(ledger))
        check("losing against-bet costs its stake", rep["eng-firm"] == START_REPUTATION - 10)
        check("poster keeps start reputation without bets", rep["qa-lab"] == START_REPUTATION)
    print(f"futures selftest: {failures} checks failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("post")
    p.add_argument("--session", required=True)
    p.add_argument("--claim", required=True)
    p.add_argument("--falsifier", required=True,
                   help="what settles this: a gate run, refute row, PR outcome")
    p.add_argument("--settle-by", required=True, dest="settle_by")
    b = sub.add_parser("bet")
    b.add_argument("--id", required=True)
    b.add_argument("--session", required=True)
    b.add_argument("--side", required=True, choices=["for", "against"])
    b.add_argument("--stake", required=True, type=int)
    s = sub.add_parser("settle")
    s.add_argument("--id", required=True)
    s.add_argument("--outcome", required=True, choices=["true", "false"])
    s.add_argument("--evidence", required=True)
    sub.add_parser("board")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    return {"post": cmd_post, "bet": cmd_bet, "settle": cmd_settle,
            "board": cmd_board}[args.cmd](args, args.ledger)


if __name__ == "__main__":
    sys.exit(main())
