#!/usr/bin/env python3
"""Measure router-named vs actually-spawned agent agreement, as a number.

WHY THIS EXISTS

EXT-3 (TODO.md, 2026-08-17), from the external-landscape comparison's
"skill-routing accuracy as a measured number" adopt item
(docs/analysis/2026-08-17-external-landscape-comparison.md, citing Google
FunctionGemma's 46-90 percent selection-reliability metric). Router-vs-spawn
agreement was measured 0 of 20 in the week to 2026-08-12
(gastown-company-registry.md persona-spawn note); this makes that a
continuous, re-runnable number instead of a one-off manual count.

DATA SOURCE

Each row in `state/agent-spawns.jsonl` already carries both sides of the
comparison at spawn time: `subagent_type` (what was actually spawned) and
`router_named` (the personas the router named just before, from
`router_named_at`). That is the ground truth this oracle reads; no join
against `state/routing.jsonl` by session id is attempted, because
`routing.jsonl`'s `session` field is empty on every row in this repo's
history (checked directly: `python3 -c "import json;
print(set(json.loads(l)['session'] for l in
open('state/routing.jsonl')))"` returns `{''}`), so a session-keyed join
would silently join everything to everything. `state/routing.jsonl` is read
separately, only to report overall router-activation volume (how often the
router matched anything at all) as context alongside the agreement number,
not as a join key.

WHAT "AGREEMENT" MEANS

A spawn row agrees when its `subagent_type` (normalized: lowercased, hyphens
and spaces folded to one separator) matches at least one entry in its own
`router_named` list (same normalization). A row with an empty `router_named`
list is counted as a spawn with no router recommendation on record, reported
separately, since it is neither agreement nor disagreement, it is missing
data the router step did not populate.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

WINDOW_DAYS = 14
_NORM = re.compile(r"[\s_-]+")


def normalize(name: str) -> str:
    return _NORM.sub("-", name.strip().lower())


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class Result:
    total: int = 0
    with_router_signal: int = 0
    agreed: int = 0
    no_signal: int = 0
    mismatches: list[dict] = field(default_factory=list)

    @property
    def agreement_rate(self) -> float | None:
        if self.with_router_signal == 0:
            return None
        return self.agreed / self.with_router_signal


def score_spawns(rows: list[dict]) -> Result:
    r = Result()
    for row in rows:
        r.total += 1
        spawned = normalize(str(row.get("subagent_type", "")))
        named = [normalize(str(n)) for n in row.get("router_named", []) or []]
        if not named:
            r.no_signal += 1
            continue
        r.with_router_signal += 1
        if spawned in named:
            r.agreed += 1
        else:
            r.mismatches.append({
                "ts": row.get("ts"), "spawned": row.get("subagent_type"),
                "router_named": row.get("router_named"),
                "description": row.get("description"),
            })
    return r


def filter_recent(rows: list[dict], days: int, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    out = []
    for row in rows:
        ts = _parse_ts(str(row.get("ts", "")))
        if ts is not None and ts >= cutoff:
            out.append(row)
    return out


def fmt_rate(rate: float | None) -> str:
    if rate is None:
        return "n/a (no router signal)"
    return f"{rate:.0%}"


def cmd_report(a: argparse.Namespace) -> int:
    spawns_path = Path(a.spawns)
    routing_path = Path(a.routing)
    spawns = _read_jsonl(spawns_path)
    routing = _read_jsonl(routing_path)

    overall = score_spawns(spawns)
    recent = score_spawns(filter_recent(spawns, WINDOW_DAYS))

    router_matched = sum(1 for row in routing if row.get("matched"))
    router_total = len(routing)
    activation = (f"{router_matched}/{router_total} prompts matched "
                  f"({router_matched / router_total:.0%})") if router_total else \
                 "n/a (0 routing.jsonl rows)"

    print(f"routing_accuracy: overall {overall.agreed}/{overall.with_router_signal} "
          f"({fmt_rate(overall.agreement_rate)}) spawn agreement across {overall.total} "
          f"spawns ({overall.no_signal} with no router_named on record); "
          f"last {WINDOW_DAYS}d {recent.agreed}/{recent.with_router_signal} "
          f"({fmt_rate(recent.agreement_rate)}) across {recent.total} spawns; "
          f"router activation {activation}")

    if a.verbose and overall.mismatches:
        print("\nMismatches (spawned vs router_named):")
        for m in overall.mismatches:
            print(f"  {m['ts']}  spawned={m['spawned']!r}  "
                  f"router_named={m['router_named']!r}  desc={m['description']!r}")
    return 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    rc = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal rc
        print("  {}  {}".format("ok  " if ok else "MISS", label))
        if detail and not ok:
            print("        " + detail[:400])
        if not ok:
            rc = 1

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=30)).isoformat()
    new_ts = (now - timedelta(days=1)).isoformat()

    synthetic = [
        # agrees: spawned "engineering-firm" matches router_named "Engineering Firm"
        {"ts": new_ts, "subagent_type": "engineering-firm",
         "router_named": ["Engineering Firm", "QA Lab"], "description": "x"},
        # disagrees: spawned "general-purpose" not in router_named
        {"ts": new_ts, "subagent_type": "general-purpose",
         "router_named": ["Review Board"], "description": "y"},
        # no signal: empty router_named
        {"ts": new_ts, "subagent_type": "fork", "router_named": [], "description": "z"},
        # old row (outside 14d window): agrees
        {"ts": old_ts, "subagent_type": "qa-lab",
         "router_named": ["QA Lab"], "description": "w"},
    ]

    overall = score_spawns(synthetic)
    check("overall counts 4 total spawns", overall.total == 4, str(overall))
    check("overall counts 1 no-signal row", overall.no_signal == 1, str(overall))
    check("overall counts 3 with-signal rows", overall.with_router_signal == 3, str(overall))
    check("overall counts 2 agreements (engineering-firm, qa-lab)",
          overall.agreed == 2, str(overall))
    check("overall agreement rate is 2/3", overall.agreement_rate == 2 / 3, str(overall))
    check("the general-purpose row is recorded as a mismatch",
          any(m["spawned"] == "general-purpose" for m in overall.mismatches),
          json.dumps(overall.mismatches))

    recent = score_spawns(filter_recent(synthetic, WINDOW_DAYS, now=now))
    check("14-day window excludes the 30-day-old row",
          recent.total == 3, str(recent))
    check("14-day window agreement is 1/2 (only engineering-firm agrees within window)",
          recent.agreed == 1 and recent.with_router_signal == 2, str(recent))

    check("normalize folds case and separators",
          normalize("Engineering Firm") == normalize("engineering-firm") == "engineering-firm")

    # end-to-end: write synthetic files, run cmd_report, must not raise
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        spawns_path = Path(td) / "agent-spawns.jsonl"
        routing_path = Path(td) / "routing.jsonl"
        spawns_path.write_text(
            "\n".join(json.dumps(r) for r in synthetic) + "\n", encoding="utf-8")
        routing_path.write_text(
            json.dumps({"ts": new_ts, "matched": True}) + "\n"
            + json.dumps({"ts": new_ts, "matched": False}) + "\n",
            encoding="utf-8")
        args = argparse.Namespace(spawns=str(spawns_path), routing=str(routing_path),
                                   verbose=True)
        try:
            code = cmd_report(args)
            check("cmd_report runs end-to-end against synthetic fixtures", code == 0)
        except Exception as exc:  # noqa: BLE001
            check("cmd_report runs end-to-end against synthetic fixtures", False, repr(exc))

    # missing files fail closed to empty data, not an exception
    args = argparse.Namespace(spawns="/no/such/file.jsonl",
                               routing="/no/such/routing.jsonl", verbose=False)
    try:
        code = cmd_report(args)
        check("missing input files report n/a instead of raising", code == 0)
    except Exception as exc:  # noqa: BLE001
        check("missing input files report n/a instead of raising", False, repr(exc))

    print("\nVERDICT: {}".format(
        "agreement counts and window filtering match synthetic fixtures"
        if rc == 0 else "selftest has failures above"))
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_report = sub.add_parser("report", help="print the measured agreement summary")
    p_report.add_argument("--spawns", default="state/agent-spawns.jsonl")
    p_report.add_argument("--routing", default="state/routing.jsonl")
    p_report.add_argument("-v", "--verbose", action="store_true",
                           help="list each mismatch")
    p_report.set_defaults(func=cmd_report)

    p_self = sub.add_parser("selftest", help="score synthetic fixtures, verify counts")
    p_self.set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
