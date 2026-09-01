#!/usr/bin/env python3
"""Supersession analysis: sources.supersedes distribution and chain statistics.

Analyses the sources.supersedes column which had only chain-walking
queries (source_chain.py) but no statistical distribution analysis,
revealing supersession rates, chain depths, and patterns by source kind.

Usage:
    python tools/corpus/supersession_analysis.py rates [--db PATH] [--json]
    python tools/corpus/supersession_analysis.py chains [--db PATH] [--json]
    python tools/corpus/supersession_analysis.py by-kind [--db PATH] [--json]
    python tools/corpus/supersession_analysis.py summary [--db PATH] [--json]
    python tools/corpus/supersession_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def supersession_rates(conn) -> dict:
    """Supersession population rates."""
    rows = conn.execute(
        "SELECT source_id, supersedes FROM sources"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "with_supersedes": 0,
            "supersession_rate": 0.0,
            "superseded_sources": 0,
            "head_sources": 0,
        }

    n = len(rows)
    with_sup = sum(1 for _, s in rows if s)
    superseded_ids = {s for _, s in rows if s}
    all_ids = {sid for sid, _ in rows}
    superseded_count = len(superseded_ids & all_ids)
    heads = len(all_ids - superseded_ids)

    return {
        "total_sources": n,
        "with_supersedes": with_sup,
        "supersession_rate": round(with_sup / n, 4) if n > 0 else 0.0,
        "superseded_sources": superseded_count,
        "head_sources": heads,
    }


def chain_distribution(conn) -> list[dict]:
    """Distribution of supersession chain depths."""
    rows = conn.execute(
        "SELECT source_id, supersedes FROM sources"
    ).fetchall()

    if not rows:
        return []

    parent_of: dict[str, str] = {}
    all_ids: set[str] = set()
    for sid, sup in rows:
        all_ids.add(sid)
        if sup:
            parent_of[sid] = sup

    if not parent_of:
        return []

    superseded = set(parent_of.values()) & all_ids
    heads = {sid for sid in parent_of if sid not in superseded}

    depths: dict[int, int] = {}
    for head in heads:
        depth = 1
        current = head
        while current in parent_of and depth < 100:
            depth += 1
            current = parent_of[current]
        depths[depth] = depths.get(depth, 0) + 1

    for sid in parent_of:
        if sid not in heads:
            depth = 1
            current = sid
            while current in parent_of and depth < 100:
                depth += 1
                current = parent_of[current]
            depths[depth] = depths.get(depth, 0) + 1

    results = [
        {"depth": d, "count": c}
        for d, c in sorted(depths.items())
    ]
    return results


def supersession_by_kind(conn) -> list[dict]:
    """Supersession rates per source kind."""
    rows = conn.execute(
        "SELECT kind, "
        "count(*) AS total, "
        "sum(CASE WHEN supersedes IS NOT NULL "
        "    AND supersedes != '' THEN 1 ELSE 0 END) AS with_sup "
        "FROM sources GROUP BY kind "
        "ORDER BY total DESC"
    ).fetchall()

    if not rows:
        return []

    results = [
        {
            "kind": kind,
            "total": total,
            "with_supersedes": with_sup,
            "supersession_rate": (
                round(with_sup / total, 4) if total > 0 else 0.0
            ),
        }
        for kind, total, with_sup in rows
    ]
    return results


def supersession_summary(conn) -> dict:
    """Aggregate supersession statistics."""
    rates = supersession_rates(conn)
    chains = chain_distribution(conn)
    by_kind = supersession_by_kind(conn)

    max_depth = max((c["depth"] for c in chains), default=0)
    total_chains = sum(c["count"] for c in chains)

    kinds_with_sup = sum(
        1 for k in by_kind if k["with_supersedes"] > 0
    )

    return {
        **rates,
        "max_chain_depth": max_depth,
        "total_chains": total_chains,
        "kinds_with_supersession": kinds_with_sup,
        "total_kinds": len(by_kind),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Chain: s3 -> s2 -> s1 (depth 3)
        # Chain: s5 -> s4 (depth 2)
        # Standalone: s6, s7
        sources = [
            ("s1", "paper", None),
            ("s2", "paper", "s1"),
            ("s3", "paper", "s2"),
            ("s4", "repo", None),
            ("s5", "repo", "s4"),
            ("s6", "local_md", None),
            ("s7", "local_md", None),
        ]
        for sid, kind, sup in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, sup),
            )

        conn.commit()

        # 1: rates return correct totals
        rates = supersession_rates(conn)
        assert rates["total_sources"] == 7
        assert rates["with_supersedes"] == 3
        checks += 1

        # 2: supersession rate is 3/7
        assert abs(rates["supersession_rate"] - 3 / 7) < 0.01
        checks += 1

        # 3: superseded sources count (s1, s2, s4 are superseded)
        assert rates["superseded_sources"] == 3
        checks += 1

        # 4: head sources (s3, s5, s6, s7 are not superseded)
        assert rates["head_sources"] == 4
        checks += 1

        # 5: chain distribution returns entries
        chains = chain_distribution(conn)
        assert len(chains) > 0
        checks += 1

        # 6: depth 2 chain exists (s5 -> s4)
        depth2 = next(
            (c for c in chains if c["depth"] == 2), None
        )
        assert depth2 is not None
        checks += 1

        # 7: depth 3 chain exists (s3 -> s2 -> s1)
        depth3 = next(
            (c for c in chains if c["depth"] == 3), None
        )
        assert depth3 is not None
        checks += 1

        # 8: by-kind returns entries
        bk = supersession_by_kind(conn)
        assert len(bk) > 0
        checks += 1

        # 9: paper kind has 2 with supersedes (s2, s3)
        paper = next(k for k in bk if k["kind"] == "paper")
        assert paper["with_supersedes"] == 2
        checks += 1

        # 10: local_md has 0 supersedes
        lmd = next(k for k in bk if k["kind"] == "local_md")
        assert lmd["with_supersedes"] == 0
        checks += 1

        # 11: repo has 1 supersedes (s5)
        repo = next(k for k in bk if k["kind"] == "repo")
        assert repo["with_supersedes"] == 1
        checks += 1

        # 12: summary has correct aggregates
        summary = supersession_summary(conn)
        assert summary["max_chain_depth"] == 3
        assert summary["kinds_with_supersession"] == 2
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(rates)
        _ = json.dumps(chains)
        _ = json.dumps(bk)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = supersession_rates(conn2)
        assert empty["total_sources"] == 0
        empty_summary = supersession_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS supersession_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Supersession analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_rates = sub.add_parser("rates",
                             help="Supersession population rates")
    p_rates.add_argument("--db", default=DEFAULT_DB)
    p_rates.add_argument("--json", action="store_true")

    p_chains = sub.add_parser("chains",
                              help="Chain depth distribution")
    p_chains.add_argument("--db", default=DEFAULT_DB)
    p_chains.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("by-kind",
                            help="Supersession per source kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Supersession statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "rates":
        result = supersession_rates(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"With supersedes: {result['with_supersedes']} "
                  f"({result['supersession_rate']:.1%})")
            print(f"  Superseded: {result['superseded_sources']}  "
                  f"Heads: {result['head_sources']}")

    elif args.cmd == "chains":
        results = chain_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  depth={r['depth']}  count={r['count']}")

    elif args.cmd == "by-kind":
        results = supersession_by_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  n={r['total']:3d}  "
                      f"sup={r['with_supersedes']}  "
                      f"rate={r['supersession_rate']:.0%}")

    elif args.cmd == "summary":
        result = supersession_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"Supersedes: {result['with_supersedes']} "
                  f"({result['supersession_rate']:.1%})")
            print(f"  Max chain: {result['max_chain_depth']}  "
                  f"Chains: {result['total_chains']}  "
                  f"Kinds with sup: "
                  f"{result['kinds_with_supersession']}/"
                  f"{result['total_kinds']}")

    conn.close()


if __name__ == "__main__":
    main()
