#!/usr/bin/env python3
"""Query state/*.jsonl ledgers by run_id.

The observability gap this closes: 19 ledger files record events from gate
runs, bus messages, corpus ingests, intent captures, and more. None of them
carried a run_id until tools/lib/trace.py was wired in, so "every event of
run X in order" was unanswerable without grepping timestamps and hoping they
aligned. Now each ledger row carries run_id (and optionally span_id /
parent_span_id), and this tool reads them back.

Usage:
  python tools/trace/query.py events --run-id <hex16>
  python tools/trace/query.py spans  --run-id <hex16>
  python tools/trace/query.py runs   [--last N]
  python tools/trace/query.py selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"


def _all_ledgers() -> list[Path]:
    if not STATE.is_dir():
        return []
    out = sorted(STATE.glob("*.jsonl"))
    sub = STATE / "timetravel"
    if sub.is_dir():
        out.extend(sorted(sub.glob("*.jsonl")))
    return out


def _scan(run_id: str) -> list[dict]:
    hits: list[dict] = []
    for ledger in _all_ledgers():
        stem = ledger.relative_to(STATE).as_posix()
        with ledger.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("run_id") == run_id:
                    row["_source"] = stem
                    row["_line"] = lineno
                    hits.append(row)
    hits.sort(key=lambda r: r.get("ts", ""))
    return hits


def cmd_events(args: argparse.Namespace) -> int:
    rows = _scan(args.run_id)
    if not rows:
        print(f"no events found for run_id={args.run_id}")
        return 1
    print(f"{len(rows)} event(s) for run_id={args.run_id}:\n")
    for r in rows:
        src = r.pop("_source", "?")
        r.pop("_line", None)
        ts = r.get("ts", "?")
        span = r.get("span_name", "")
        label = f"  [{ts}] {src}"
        if span:
            label += f"  span={span}"
        print(label)
        for k in ("verdict", "domain", "kind", "subject", "status", "state"):
            if k in r:
                print(f"    {k}: {r[k]}")
    return 0


def cmd_spans(args: argparse.Namespace) -> int:
    rows = _scan(args.run_id)
    spans = [r for r in rows if r.get("span_id")]
    if not spans:
        print(f"no spans found for run_id={args.run_id}")
        if rows:
            print(f"  ({len(rows)} event(s) exist but none carry span_id)")
        return 1
    by_id: dict[str, list[dict]] = {}
    for r in spans:
        by_id.setdefault(r["span_id"], []).append(r)

    roots = [sid for sid, rs in by_id.items()
             if not rs[0].get("parent_span_id")]
    printed: set[str] = set()

    def _print_tree(sid: str, depth: int = 0) -> None:
        if sid in printed:
            return
        printed.add(sid)
        rs = by_id.get(sid, [])
        name = rs[0].get("span_name", sid) if rs else sid
        src = rs[0].get("_source", "?") if rs else "?"
        indent = "  " * depth
        print(f"{indent}{name} ({src}, {len(rs)} event(s))")
        children = [s for s, evts in by_id.items()
                    if evts[0].get("parent_span_id") == sid and s != sid]
        for child in children:
            _print_tree(child, depth + 1)

    for root in roots:
        _print_tree(root)
    for sid in by_id:
        if sid not in printed:
            _print_tree(sid)
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    seen: dict[str, dict] = {}
    for ledger in _all_ledgers():
        stem = ledger.relative_to(STATE).as_posix()
        with ledger.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rid = row.get("run_id")
                if not rid:
                    continue
                if rid not in seen:
                    seen[rid] = {
                        "run_id": rid,
                        "first_ts": row.get("ts", ""),
                        "sources": set(),
                        "count": 0,
                    }
                seen[rid]["sources"].add(stem)
                seen[rid]["count"] += 1
                ts = row.get("ts", "")
                if ts > seen[rid].get("last_ts", ""):
                    seen[rid]["last_ts"] = ts
    if not seen:
        print("no runs with run_id found in state/*.jsonl")
        return 1
    runs = sorted(seen.values(), key=lambda r: r.get("last_ts", ""), reverse=True)
    limit = args.last or 20
    for r in runs[:limit]:
        sources = ", ".join(sorted(r["sources"]))
        print(f"  {r['run_id']}  {r.get('last_ts', '?')}  {r['count']} event(s)  [{sources}]")
    if len(runs) > limit:
        print(f"  ... {len(runs) - limit} more (use --last to show more)")
    return 0


def cmd_selftest(_args: argparse.Namespace | None = None) -> int:
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from tracing import run_context, span, inject, current_run_id, generate_run_id

    with tempfile.TemporaryDirectory() as td:
        ledger = Path(td) / "test.jsonl"
        rid = generate_run_id()
        assert len(rid) == 16
        assert current_run_id() is None or current_run_id() != rid

        rows_written = []
        with run_context(rid) as active:
            assert active == rid
            assert current_run_id() == rid

            row1 = inject({"ts": "2026-01-01T00:00:00", "kind": "gate-start"})
            assert row1["run_id"] == rid
            assert "span_id" not in row1
            rows_written.append(row1)

            with span("domain:unit") as sid:
                row2 = inject({"ts": "2026-01-01T00:00:01", "kind": "domain-result"})
                assert row2["run_id"] == rid
                assert row2["span_id"] == sid
                assert row2["span_name"] == "domain:unit"
                assert "parent_span_id" not in row2
                rows_written.append(row2)

                with span("subcheck") as sid2:
                    row3 = inject({"ts": "2026-01-01T00:00:02", "kind": "sub"})
                    assert row3["span_id"] == sid2
                    assert row3["parent_span_id"] == sid
                    rows_written.append(row3)

        assert current_run_id() != rid or current_run_id() is None

        with ledger.open("w", encoding="utf-8") as fh:
            for r in rows_written:
                fh.write(json.dumps(r) + "\n")

        # Verify scan by temporarily pointing the module-level STATE at the temp dir
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("_query_self", Path(__file__))
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.STATE = Path(td)
        hits = _mod._scan(rid)
        assert len(hits) == 3, f"expected 3 hits, got {len(hits)}"
        assert hits[0]["kind"] == "gate-start"
        assert hits[1]["span_name"] == "domain:unit"
        assert hits[2]["parent_span_id"] == hits[1]["span_id"]

        no_overwrite = {"run_id": "keep-me", "span_id": "keep-span"}
        inject(no_overwrite)
        assert no_overwrite["run_id"] == "keep-me"
        assert no_overwrite["span_id"] == "keep-span"

    print("trace selftest: PASS (context, inject, span nesting, scan, no-overwrite)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query state/*.jsonl ledgers by run_id")
    sub = parser.add_subparsers(dest="command")

    p_events = sub.add_parser("events", help="Show all events for a run")
    p_events.add_argument("--run-id", required=True)

    p_spans = sub.add_parser("spans", help="Show span tree for a run")
    p_spans.add_argument("--run-id", required=True)

    p_runs = sub.add_parser("runs", help="List recent runs")
    p_runs.add_argument("--last", type=int, default=20)

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()
    if args.command == "events":
        return cmd_events(args)
    elif args.command == "spans":
        return cmd_spans(args)
    elif args.command == "runs":
        return cmd_runs(args)
    elif args.command == "selftest":
        return cmd_selftest(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
