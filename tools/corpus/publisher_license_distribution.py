#!/usr/bin/env python3
"""Publisher and license distribution analysis.

Analyses the publisher and license_spdx columns of the sources table
to reveal concentration patterns, top contributors, license type
breakdown, and cross-tabulations.

Usage:
    python tools/corpus/publisher_license_distribution.py publishers [--db PATH] [--top N] [--json]
    python tools/corpus/publisher_license_distribution.py licenses [--db PATH] [--json]
    python tools/corpus/publisher_license_distribution.py cross-tab [--db PATH] [--json]
    python tools/corpus/publisher_license_distribution.py summary [--db PATH] [--json]
    python tools/corpus/publisher_license_distribution.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _gini(values: list[int]) -> float:
    if not values or sum(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    total = sum(sorted_v)
    cumulative = 0.0
    weighted_sum = 0.0
    for i, v in enumerate(sorted_v):
        cumulative += v
        weighted_sum += (2 * (i + 1) - n - 1) * v
    return round(weighted_sum / (n * total), 4)


def top_publishers(conn, top_n: int = 20) -> list[dict]:
    """Publishers ranked by source count and total bytes."""
    rows = conn.execute(
        "SELECT COALESCE(publisher, '(unknown)') AS pub, "
        "count(*) AS source_count, "
        "sum(bytes) AS total_bytes, "
        "count(DISTINCT kind) AS kind_count "
        "FROM sources "
        "GROUP BY pub "
        "ORDER BY source_count DESC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    if not rows:
        return []

    grand_total = sum(r[1] for r in rows)
    return [
        {
            "publisher": r[0],
            "source_count": r[1],
            "share": round(r[1] / grand_total, 4) if grand_total > 0 else 0.0,
            "total_bytes": r[2],
            "kind_count": r[3],
        }
        for r in rows
    ]


def license_breakdown(conn) -> list[dict]:
    """License type distribution across sources."""
    rows = conn.execute(
        "SELECT license_spdx, license_verdict, "
        "count(*) AS source_count, "
        "sum(bytes) AS total_bytes "
        "FROM sources "
        "GROUP BY license_spdx, license_verdict "
        "ORDER BY source_count DESC"
    ).fetchall()

    if not rows:
        return []

    grand_total = sum(r[2] for r in rows)
    return [
        {
            "license_spdx": r[0],
            "verdict": r[1],
            "source_count": r[2],
            "share": round(r[2] / grand_total, 4) if grand_total > 0 else 0.0,
            "total_bytes": r[3],
        }
        for r in rows
    ]


def cross_tabulation(conn) -> list[dict]:
    """Publisher-license cross-tabulation."""
    rows = conn.execute(
        "SELECT COALESCE(publisher, '(unknown)') AS pub, "
        "license_spdx, "
        "count(*) AS source_count "
        "FROM sources "
        "GROUP BY pub, license_spdx "
        "ORDER BY source_count DESC"
    ).fetchall()

    if not rows:
        return []

    return [
        {
            "publisher": r[0],
            "license_spdx": r[1],
            "source_count": r[2],
        }
        for r in rows
    ]


def publisher_license_summary(conn) -> dict:
    """Aggregate publisher and license statistics."""
    rows = conn.execute(
        "SELECT COALESCE(publisher, '(unknown)'), license_spdx, "
        "license_verdict, bytes FROM sources"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "distinct_publishers": 0,
            "distinct_licenses": 0,
            "distinct_verdicts": 0,
            "unknown_publisher_count": 0,
            "publisher_gini": 0.0,
            "top_publisher": None,
            "top_license": None,
        }

    pubs: dict[str, int] = {}
    licenses: dict[str, int] = {}
    verdicts: set[str] = set()
    unknown_pub = 0

    for pub, lic, verdict, _ in rows:
        pubs[pub] = pubs.get(pub, 0) + 1
        licenses[lic] = licenses.get(lic, 0) + 1
        verdicts.add(verdict)
        if pub == "(unknown)":
            unknown_pub += 1

    top_pub = max(pubs, key=pubs.get)
    top_lic = max(licenses, key=licenses.get)

    return {
        "total_sources": len(rows),
        "distinct_publishers": len(pubs),
        "distinct_licenses": len(licenses),
        "distinct_verdicts": len(verdicts),
        "unknown_publisher_count": unknown_pub,
        "publisher_gini": _gini(list(pubs.values())),
        "top_publisher": top_pub,
        "top_license": top_lic,
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

        sources = [
            ("s1", "https://s1.com", "paper", "Paper 1",
             "CC-BY-4.0", "vendor", "declared", "Acme Press",
             5000),
            ("s2", "https://s2.com", "paper", "Paper 2",
             "CC-BY-4.0", "vendor", "declared", "Acme Press",
             8000),
            ("s3", "https://s3.com", "paper", "Paper 3",
             "MIT", "vendor", "declared", "Acme Press",
             3000),
            ("s4", "https://s4.com", "local_md", "Doc 1",
             "CC-BY-4.0", "vendor", "declared", "Beta Labs",
             2000),
            ("s5", "https://s5.com", "repo", "Repo 1",
             "Apache-2.0", "index_only", "spdx", None,
             15000),
            ("s6", "https://s6.com", "hf_dataset", "Dataset 1",
             "CC-BY-4.0", "vendor", "declared", "Beta Labs",
             50000),
        ]
        for sid, uri, kind, title, lic, verdict, ev, pub, sz in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, kind, title, lic, verdict, ev, pub,
                 now, now, "", "", "live", f"sha_{sid}", sz, None),
            )

        conn.commit()

        # 1: publishers returns entries
        pubs = top_publishers(conn)
        assert len(pubs) > 0
        checks += 1

        # 2: Acme Press is top publisher with 3 sources
        assert pubs[0]["publisher"] == "Acme Press"
        assert pubs[0]["source_count"] == 3
        checks += 1

        # 3: shares sum to approximately 1.0
        total_share = sum(p["share"] for p in pubs)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 4: unknown publisher present (s5 has None)
        unknown = next(
            (p for p in pubs if p["publisher"] == "(unknown)"), None
        )
        assert unknown is not None
        assert unknown["source_count"] == 1
        checks += 1

        # 5: licenses returns entries
        lics = license_breakdown(conn)
        assert len(lics) > 0
        checks += 1

        # 6: CC-BY-4.0 is most common (4 sources)
        assert lics[0]["license_spdx"] == "CC-BY-4.0"
        assert lics[0]["source_count"] == 4
        checks += 1

        # 7: license shares sum to approximately 1.0
        lic_share = sum(l["share"] for l in lics)
        assert abs(lic_share - 1.0) < 0.01
        checks += 1

        # 8: cross-tab returns entries
        xtab = cross_tabulation(conn)
        assert len(xtab) > 0
        checks += 1

        # 9: cross-tab has Acme+CC-BY-4.0 with 2 sources
        acme_cc = next(
            (x for x in xtab
             if x["publisher"] == "Acme Press"
             and x["license_spdx"] == "CC-BY-4.0"),
            None,
        )
        assert acme_cc is not None
        assert acme_cc["source_count"] == 2
        checks += 1

        # 10: summary has correct totals
        summary = publisher_license_summary(conn)
        assert summary["total_sources"] == 6
        assert summary["distinct_publishers"] == 3
        checks += 1

        # 11: unknown publisher count is 1
        assert summary["unknown_publisher_count"] == 1
        checks += 1

        # 12: gini is between 0 and 1
        assert 0.0 <= summary["publisher_gini"] <= 1.0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(pubs)
        _ = json.dumps(lics)
        _ = json.dumps(xtab)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = top_publishers(conn2)
        assert empty == []
        empty_summary = publisher_license_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS publisher_license_distribution selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publisher and license distribution analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_pub = sub.add_parser("publishers",
                           help="Top publishers by source count")
    p_pub.add_argument("--db", default=DEFAULT_DB)
    p_pub.add_argument("--top", type=int, default=20)
    p_pub.add_argument("--json", action="store_true")

    p_lic = sub.add_parser("licenses",
                           help="License type distribution")
    p_lic.add_argument("--db", default=DEFAULT_DB)
    p_lic.add_argument("--json", action="store_true")

    p_xtab = sub.add_parser("cross-tab",
                            help="Publisher-license cross-tabulation")
    p_xtab.add_argument("--db", default=DEFAULT_DB)
    p_xtab.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Publisher and license statistics")
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

    if args.cmd == "publishers":
        results = top_publishers(conn, args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['publisher']:20s}  {r['source_count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "licenses":
        results = license_breakdown(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['license_spdx']:16s}  "
                      f"{r['verdict']:10s}  "
                      f"n={r['source_count']:3d}  "
                      f"{r['share']:5.1%}")

    elif args.cmd == "cross-tab":
        results = cross_tabulation(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['publisher']:20s}  "
                      f"{r['license_spdx']:16s}  "
                      f"n={r['source_count']:3d}")

    elif args.cmd == "summary":
        result = publisher_license_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}")
            print(f"  Publishers: {result['distinct_publishers']}  "
                  f"(unknown: {result['unknown_publisher_count']})  "
                  f"Gini: {result['publisher_gini']:.3f}")
            print(f"  Licenses: {result['distinct_licenses']}  "
                  f"Verdicts: {result['distinct_verdicts']}")
            print(f"  Top publisher: {result['top_publisher']}  "
                  f"Top license: {result['top_license']}")

    conn.close()


if __name__ == "__main__":
    main()
