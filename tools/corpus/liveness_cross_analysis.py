#!/usr/bin/env python3
"""Liveness cross-analysis: liveness patterns across dimensions.

Cross-tabulates sources.liveness against source kind, publisher,
license, and chunk metrics to reveal which dimensions correlate
with staleness and archival.

Usage:
    python tools/corpus/liveness_cross_analysis.py by-kind [--db PATH] [--json]
    python tools/corpus/liveness_cross_analysis.py by-publisher [--db PATH] [--json]
    python tools/corpus/liveness_cross_analysis.py by-license [--db PATH] [--json]
    python tools/corpus/liveness_cross_analysis.py summary [--db PATH] [--json]
    python tools/corpus/liveness_cross_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def liveness_by_kind(conn) -> list[dict]:
    """Liveness distribution per source kind."""
    rows = conn.execute(
        "SELECT kind, liveness, count(*) AS cnt "
        "FROM sources GROUP BY kind, liveness "
        "ORDER BY kind, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_kind: dict[str, dict] = {}
    for kind, liveness, cnt in rows:
        if kind not in by_kind:
            by_kind[kind] = {"total": 0, "breakdown": {}}
        by_kind[kind]["total"] += cnt
        by_kind[kind]["breakdown"][liveness] = cnt

    results = []
    for kind, info in by_kind.items():
        t = info["total"]
        live = info["breakdown"].get("live", 0)
        results.append({
            "kind": kind,
            "source_count": t,
            "live": live,
            "live_rate": round(live / t, 4) if t > 0 else 0.0,
            "breakdown": info["breakdown"],
        })

    results.sort(key=lambda r: r["live_rate"])
    return results


def liveness_by_publisher(conn) -> list[dict]:
    """Liveness distribution per publisher."""
    rows = conn.execute(
        "SELECT COALESCE(publisher, '(unknown)') AS pub, "
        "liveness, count(*) AS cnt "
        "FROM sources GROUP BY pub, liveness "
        "ORDER BY pub, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_pub: dict[str, dict] = {}
    for pub, liveness, cnt in rows:
        if pub not in by_pub:
            by_pub[pub] = {"total": 0, "breakdown": {}}
        by_pub[pub]["total"] += cnt
        by_pub[pub]["breakdown"][liveness] = cnt

    results = []
    for pub, info in by_pub.items():
        t = info["total"]
        live = info["breakdown"].get("live", 0)
        results.append({
            "publisher": pub,
            "source_count": t,
            "live": live,
            "live_rate": round(live / t, 4) if t > 0 else 0.0,
            "breakdown": info["breakdown"],
        })

    results.sort(key=lambda r: -r["source_count"])
    return results


def liveness_by_license(conn) -> list[dict]:
    """Liveness distribution per license."""
    rows = conn.execute(
        "SELECT COALESCE(license_spdx, '(unknown)') AS lic, "
        "liveness, count(*) AS cnt "
        "FROM sources GROUP BY lic, liveness "
        "ORDER BY lic, cnt DESC"
    ).fetchall()

    if not rows:
        return []

    by_lic: dict[str, dict] = {}
    for lic, liveness, cnt in rows:
        if lic not in by_lic:
            by_lic[lic] = {"total": 0, "breakdown": {}}
        by_lic[lic]["total"] += cnt
        by_lic[lic]["breakdown"][liveness] = cnt

    results = []
    for lic, info in by_lic.items():
        t = info["total"]
        live = info["breakdown"].get("live", 0)
        results.append({
            "license": lic,
            "source_count": t,
            "live": live,
            "live_rate": round(live / t, 4) if t > 0 else 0.0,
            "breakdown": info["breakdown"],
        })

    results.sort(key=lambda r: -r["source_count"])
    return results


def liveness_summary(conn) -> dict:
    """Aggregate liveness cross-analysis statistics."""
    rows = conn.execute(
        "SELECT liveness, kind, "
        "COALESCE(publisher, '(unknown)') AS pub, "
        "COALESCE(license_spdx, '(unknown)') AS lic, "
        "bytes "
        "FROM sources"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "liveness_counts": {},
            "live_rate": 0.0,
            "kinds_with_non_live": 0,
            "publishers_with_non_live": 0,
            "non_live_bytes": 0,
            "live_bytes": 0,
        }

    n = len(rows)
    liveness_counts: dict[str, int] = {}
    kinds_non_live: set[str] = set()
    pubs_non_live: set[str] = set()
    non_live_bytes = 0
    live_bytes = 0

    for liveness, kind, pub, lic, byt in rows:
        liveness_counts[liveness] = liveness_counts.get(liveness, 0) + 1
        b = byt or 0
        if liveness != "live":
            kinds_non_live.add(kind)
            pubs_non_live.add(pub)
            non_live_bytes += b
        else:
            live_bytes += b

    live_count = liveness_counts.get("live", 0)

    return {
        "total_sources": n,
        "liveness_counts": liveness_counts,
        "live_rate": round(live_count / n, 4) if n > 0 else 0.0,
        "kinds_with_non_live": len(kinds_non_live),
        "publishers_with_non_live": len(pubs_non_live),
        "non_live_bytes": non_live_bytes,
        "live_bytes": live_bytes,
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
            ("s1", "paper", "Acme", "CC-BY-4.0", "live", 5000),
            ("s2", "paper", "Acme", "CC-BY-4.0", "stale", 3000),
            ("s3", "paper", "Beta", "MIT", "live", 2000),
            ("s4", "local_md", "Acme", "CC-BY-4.0", "live", 1000),
            ("s5", "local_md", None, "MIT", "archived", 4000),
            ("s6", "repo", "Beta", "Apache-2.0", "dead", 6000),
            ("s7", "repo", "Beta", "Apache-2.0", "live", 8000),
        ]
        for sid, kind, pub, lic, liveness, byt in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 lic, "vendor", "declared", pub,
                 now, now, "", "", liveness, f"sha_{sid}", byt, None),
            )

        conn.commit()

        # 1: by-kind returns entries
        bk = liveness_by_kind(conn)
        assert len(bk) > 0
        checks += 1

        # 2: paper kind has 2 live out of 3 (s1 live, s2 stale, s3 live) -> wrong
        # paper: s1 live, s2 stale, s3 live = 3 total, 2 live
        paper = next(k for k in bk if k["kind"] == "paper")
        assert paper["source_count"] == 3
        assert paper["live"] == 2
        checks += 1

        # 3: repo kind has 1 live, 1 dead
        repo = next(k for k in bk if k["kind"] == "repo")
        assert repo["source_count"] == 2
        assert repo["live"] == 1
        assert repo["breakdown"]["dead"] == 1
        checks += 1

        # 4: sorted by live_rate ascending (worst first)
        rates = [k["live_rate"] for k in bk]
        assert rates == sorted(rates)
        checks += 1

        # 5: by-publisher returns entries
        bp = liveness_by_publisher(conn)
        assert len(bp) > 0
        checks += 1

        # 6: Acme has 2 live, 1 stale
        acme = next(p for p in bp if p["publisher"] == "Acme")
        assert acme["source_count"] == 3
        assert acme["live"] == 2
        checks += 1

        # 7: Beta has 2 live, 1 dead
        beta = next(p for p in bp if p["publisher"] == "Beta")
        assert beta["live"] == 2
        assert beta["breakdown"].get("dead", 0) == 1
        checks += 1

        # 8: by-license returns entries
        bl = liveness_by_license(conn)
        assert len(bl) > 0
        checks += 1

        # 9: CC-BY-4.0 has 2 live, 1 stale
        cc = next(l for l in bl if l["license"] == "CC-BY-4.0")
        assert cc["source_count"] == 3
        assert cc["live"] == 2
        checks += 1

        # 10: Apache-2.0 has 1 live, 1 dead
        apache = next(l for l in bl if l["license"] == "Apache-2.0")
        assert apache["live"] == 1
        assert apache["breakdown"].get("dead", 0) == 1
        checks += 1

        # 11: summary has correct totals
        summary = liveness_summary(conn)
        assert summary["total_sources"] == 7
        assert summary["liveness_counts"]["live"] == 4
        checks += 1

        # 12: non-live bytes and kinds
        assert summary["non_live_bytes"] == 13000
        assert summary["kinds_with_non_live"] == 3
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(bk)
        _ = json.dumps(bp)
        _ = json.dumps(bl)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = liveness_by_kind(conn2)
        assert empty == []
        empty_summary = liveness_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS liveness_cross_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Liveness cross-analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_kind = sub.add_parser("by-kind",
                            help="Liveness per source kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_pub = sub.add_parser("by-publisher",
                           help="Liveness per publisher")
    p_pub.add_argument("--db", default=DEFAULT_DB)
    p_pub.add_argument("--json", action="store_true")

    p_lic = sub.add_parser("by-license",
                           help="Liveness per license")
    p_lic.add_argument("--db", default=DEFAULT_DB)
    p_lic.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Liveness cross-analysis statistics")
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

    if args.cmd == "by-kind":
        results = liveness_by_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  n={r['source_count']:3d}  "
                      f"live={r['live']}  rate={r['live_rate']:.0%}  "
                      f"{r['breakdown']}")

    elif args.cmd == "by-publisher":
        results = liveness_by_publisher(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['publisher'][:20]:20s}  n={r['source_count']:3d}  "
                      f"live={r['live']}  rate={r['live_rate']:.0%}")

    elif args.cmd == "by-license":
        results = liveness_by_license(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['license'][:20]:20s}  n={r['source_count']:3d}  "
                      f"live={r['live']}  rate={r['live_rate']:.0%}")

    elif args.cmd == "summary":
        result = liveness_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"Live: {result['liveness_counts'].get('live', 0)} "
                  f"({result['live_rate']:.1%})")
            print(f"  Non-live kinds: {result['kinds_with_non_live']}  "
                  f"Non-live publishers: "
                  f"{result['publishers_with_non_live']}")
            print(f"  Live bytes: {result['live_bytes']:,}  "
                  f"Non-live bytes: {result['non_live_bytes']:,}")

    conn.close()


if __name__ == "__main__":
    main()
