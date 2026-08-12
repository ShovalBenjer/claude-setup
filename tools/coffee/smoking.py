#!/usr/bin/env python3
"""The smoking area: frustration-triggered coffee, and the gripe ledger it feeds.

Coffee-break v2, the trigger half (taste ledger row 2026-08-12). Breaks are not
scheduled; they fire when the telemetry shows real friction. `scan` reads
state/gate-runs.jsonl for recent FAIL rows and prints trigger candidates; `gripe`
and `takeaway` append to state/coffee.jsonl; `mine` turns unmined gripes into
bar-talk TODO candidates (leads, not findings, per calibrated-claims). A `mine`
marker row is appended rather than rewriting anything: the ledger stays
append-only and the cursor is derivable from it.

Commands: scan, gripe, takeaway, mine, selftest.
"""
import argparse
import fcntl
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

COFFEE = Path("state/coffee.jsonl")
GATE_RUNS = Path("state/gate-runs.jsonl")


def now_dt() -> datetime:
    return datetime.now(timezone.utc)


def now() -> str:
    return now_dt().strftime("%Y-%m-%dT%H:%M:%S")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def scan(gate_runs: Path, window_hours: float, ref: datetime | None = None) -> list[dict]:
    """FAIL rows inside the window, grouped by project: the annoyed candidates."""
    ref = ref or now_dt()
    cutoff = ref - timedelta(hours=window_hours)
    grouped: dict[str, dict] = {}
    for r in read_rows(gate_runs):
        if r.get("verdict") != "FAIL":
            continue
        ts = datetime.fromisoformat(r["ts"]).replace(tzinfo=timezone.utc)
        if ts < cutoff:
            continue
        g = grouped.setdefault(r.get("project", "?"), {"project": r.get("project", "?"),
                                                       "fails": 0, "last_ts": r["ts"]})
        g["fails"] += 1
        g["last_ts"] = max(g["last_ts"], r["ts"])
    return sorted(grouped.values(), key=lambda g: -g["fails"])


def cmd_scan(args) -> int:
    candidates = scan(args.gate_runs, args.window_hours)
    for c in candidates:
        print(json.dumps(c))
    if len(candidates) >= 2:
        print(f"TRIGGER: {len(candidates)} project(s) frustrated inside "
              f"{args.window_hours}h, smoking area is on", file=sys.stderr)
    return 0


def cmd_gripe(args) -> int:
    append_row(args.coffee, {"kind": "gripe", "ts": now(), "session": args.session,
                             "text": args.text, "about": args.about})
    print("gripe recorded")
    return 0


def cmd_takeaway(args) -> int:
    append_row(args.coffee, {"kind": "takeaway", "ts": now(), "session": args.session,
                             "learned": args.learned, "affects": args.affects,
                             "steal": args.steal})
    print("takeaway recorded")
    return 0


def unmined_gripes(rows: list[dict]) -> list[dict]:
    epoch = "0000-01-01T00:00:00"
    last_mine = max((r["ts"] for r in rows if r["kind"] == "mine"), default=epoch)
    return [r for r in rows if r["kind"] == "gripe" and r["ts"] > last_mine]


def cmd_mine(args) -> int:
    rows = read_rows(args.coffee)
    fresh = unmined_gripes(rows)
    if not fresh:
        print("nothing to mine")
        return 0
    for g in fresh:
        about = f" (about: {g['about']})" if g.get("about") else ""
        print(f"- [ ] [bar-talk] {g['session']}: {g['text']}{about}")
    append_row(args.coffee, {"kind": "mine", "ts": now(), "count": len(fresh)})
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
        gate_runs = Path(td) / "gate-runs.jsonl"
        ref = datetime(2026, 8, 12, 12, 0, 0, tzinfo=timezone.utc)
        for ts, project, verdict in [
            ("2026-08-12T11:00:00", "a", "FAIL"),
            ("2026-08-12T11:30:00", "a", "FAIL"),
            ("2026-08-12T11:45:00", "b", "FAIL"),
            ("2026-08-12T11:50:00", "b", "PASS"),
            ("2026-08-10T09:00:00", "old", "FAIL"),
        ]:
            append_row(gate_runs, {"ts": ts, "project": project, "verdict": verdict})
        cands = scan(gate_runs, 24, ref=ref)
        check("two projects inside window", {c["project"] for c in cands} == {"a", "b"})
        check("PASS rows do not count", next(c for c in cands if c["project"] == "b")["fails"] == 1)
        check("stale FAIL outside window excluded", all(c["project"] != "old" for c in cands))
        check("most frustrated first", cands[0]["project"] == "a")

        coffee = Path(td) / "coffee.jsonl"
        ns = argparse.Namespace(coffee=coffee, session="qa-lab",
                                text="the gate fingerprint invalidated itself again",
                                about="gate.py")
        check("gripe exits 0", cmd_gripe(ns) == 0)
        rows = read_rows(coffee)
        check("gripe lands in ledger", rows[-1]["kind"] == "gripe")
        check("fresh gripe is unmined", len(unmined_gripes(rows)) == 1)
        mine_ns = argparse.Namespace(coffee=coffee)
        check("mine exits 0", cmd_mine(mine_ns) == 0)
        rows = read_rows(coffee)
        check("mine marker appended", rows[-1]["kind"] == "mine" and rows[-1]["count"] == 1)
        check("mined gripe not re-mined", len(unmined_gripes(rows)) == 0)
    print(f"smoking selftest: {failures} checks failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--coffee", type=Path, default=COFFEE)
    ap.add_argument("--gate-runs", type=Path, default=GATE_RUNS, dest="gate_runs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan")
    sc.add_argument("--window-hours", type=float, default=24, dest="window_hours")
    g = sub.add_parser("gripe")
    g.add_argument("--session", required=True)
    g.add_argument("--text", required=True)
    g.add_argument("--about", default="")
    t = sub.add_parser("takeaway")
    t.add_argument("--session", required=True)
    t.add_argument("--learned", required=True)
    t.add_argument("--affects", required=True)
    t.add_argument("--steal", required=True)
    sub.add_parser("mine")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    return {"scan": cmd_scan, "gripe": cmd_gripe, "takeaway": cmd_takeaway,
            "mine": cmd_mine}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
