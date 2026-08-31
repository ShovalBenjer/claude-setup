#!/usr/bin/env python3
"""Upstream provenance analysis: revision and modification time patterns.

Analyses the upstream_rev and upstream_mtime columns of sources to
reveal version tracking completeness, modification time distribution,
and staleness patterns across the corpus.

Usage:
    python tools/corpus/upstream_provenance.py completeness [--db PATH] [--json]
    python tools/corpus/upstream_provenance.py age-distribution [--db PATH] [--json]
    python tools/corpus/upstream_provenance.py per-kind [--db PATH] [--json]
    python tools/corpus/upstream_provenance.py summary [--db PATH] [--json]
    python tools/corpus/upstream_provenance.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _parse_utc(s: str | None) -> datetime.datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt).replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            continue
    return None


def _age_bucket(days: int) -> str:
    if days < 0:
        return "future"
    if days <= 7:
        return "<=7d"
    if days <= 30:
        return "8-30d"
    if days <= 90:
        return "31-90d"
    if days <= 180:
        return "91-180d"
    if days <= 365:
        return "181-365d"
    return ">365d"


def completeness(conn) -> list[dict]:
    """Upstream field completeness per source kind."""
    rows = conn.execute(
        "SELECT source_id, kind, upstream_rev, upstream_mtime "
        "FROM sources"
    ).fetchall()

    if not rows:
        return []

    by_kind: dict[str, dict] = {}
    for _sid, kind, rev, mtime in rows:
        if kind not in by_kind:
            by_kind[kind] = {
                "total": 0,
                "has_rev": 0,
                "has_mtime": 0,
                "has_both": 0,
                "has_neither": 0,
            }
        k = by_kind[kind]
        k["total"] += 1
        has_r = bool(rev and rev.strip())
        has_m = bool(mtime and mtime.strip())
        if has_r:
            k["has_rev"] += 1
        if has_m:
            k["has_mtime"] += 1
        if has_r and has_m:
            k["has_both"] += 1
        if not has_r and not has_m:
            k["has_neither"] += 1

    results = []
    for kind, info in by_kind.items():
        t = info["total"]
        results.append({
            "kind": kind,
            "source_count": t,
            "has_rev": info["has_rev"],
            "rev_rate": round(info["has_rev"] / t, 4) if t > 0 else 0.0,
            "has_mtime": info["has_mtime"],
            "mtime_rate": round(info["has_mtime"] / t, 4) if t > 0 else 0.0,
            "has_both": info["has_both"],
            "has_neither": info["has_neither"],
        })

    results.sort(key=lambda r: -r["source_count"])
    return results


def age_distribution(conn) -> list[dict]:
    """Distribution of upstream modification ages."""
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = conn.execute(
        "SELECT upstream_mtime FROM sources WHERE upstream_mtime IS NOT NULL "
        "AND upstream_mtime != ''"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, int] = {}
    for (mtime_str,) in rows:
        dt = _parse_utc(mtime_str)
        if dt is None:
            continue
        days = (now - dt).days
        bucket = _age_bucket(days)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    order = ["future", "<=7d", "8-30d", "31-90d", "91-180d", "181-365d", ">365d"]
    total = sum(buckets.values())
    results = []
    for b in order:
        if b in buckets:
            n = buckets[b]
            results.append({
                "bucket": b,
                "count": n,
                "share": round(n / total, 4) if total > 0 else 0.0,
            })

    return results


def per_kind_provenance(conn) -> list[dict]:
    """Upstream revision patterns per source kind."""
    rows = conn.execute(
        "SELECT kind, upstream_rev, upstream_mtime, liveness "
        "FROM sources"
    ).fetchall()

    if not rows:
        return []

    by_kind: dict[str, dict] = {}
    for kind, rev, mtime, liveness in rows:
        if kind not in by_kind:
            by_kind[kind] = {
                "revs": [],
                "liveness": {},
                "total": 0,
            }
        k = by_kind[kind]
        k["total"] += 1
        if rev and rev.strip():
            k["revs"].append(rev.strip())
        k["liveness"][liveness] = k["liveness"].get(liveness, 0) + 1

    results = []
    for kind, info in by_kind.items():
        distinct_revs = len(set(info["revs"]))
        results.append({
            "kind": kind,
            "source_count": info["total"],
            "distinct_revs": distinct_revs,
            "rev_populated": len(info["revs"]),
            "liveness_breakdown": info["liveness"],
        })

    results.sort(key=lambda r: -r["source_count"])
    return results


def provenance_summary(conn) -> dict:
    """Aggregate upstream provenance statistics."""
    rows = conn.execute(
        "SELECT upstream_rev, upstream_mtime, kind, liveness "
        "FROM sources"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "rev_populated": 0,
            "rev_rate": 0.0,
            "mtime_populated": 0,
            "mtime_rate": 0.0,
            "distinct_revs": 0,
            "distinct_kinds": 0,
            "oldest_mtime": None,
            "newest_mtime": None,
            "liveness_counts": {},
        }

    n = len(rows)
    rev_pop = 0
    mtime_pop = 0
    revs: set[str] = set()
    kinds: set[str] = set()
    liveness_counts: dict[str, int] = {}
    mtimes: list[datetime.datetime] = []

    for rev, mtime, kind, liveness in rows:
        kinds.add(kind)
        liveness_counts[liveness] = liveness_counts.get(liveness, 0) + 1

        if rev and rev.strip():
            rev_pop += 1
            revs.add(rev.strip())
        if mtime and mtime.strip():
            mtime_pop += 1
            dt = _parse_utc(mtime)
            if dt:
                mtimes.append(dt)

    oldest = min(mtimes).strftime("%Y-%m-%dT%H:%M:%SZ") if mtimes else None
    newest = max(mtimes).strftime("%Y-%m-%dT%H:%M:%SZ") if mtimes else None

    return {
        "total_sources": n,
        "rev_populated": rev_pop,
        "rev_rate": round(rev_pop / n, 4) if n > 0 else 0.0,
        "mtime_populated": mtime_pop,
        "mtime_rate": round(mtime_pop / n, 4) if n > 0 else 0.0,
        "distinct_revs": len(revs),
        "distinct_kinds": len(kinds),
        "oldest_mtime": oldest,
        "newest_mtime": newest,
        "liveness_counts": liveness_counts,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        )
        now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        old_s = (now - datetime.timedelta(days=200)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        recent_s = (now - datetime.timedelta(days=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        sources = [
            ("s1", "https://s1.com", "paper", "abc123", now_s, "live"),
            ("s2", "https://s2.com", "paper", "def456", old_s, "stale"),
            ("s3", "https://s3.com", "local_md", "", recent_s, "live"),
            ("s4", "https://s4.com", "local_md", "ghi789", "", "live"),
            ("s5", "https://s5.com", "hf_dataset", "", "", "archived"),
            ("s6", "https://s6.com", "repo", "jkl012", recent_s, "live"),
        ]
        for sid, uri, kind, rev, mtime, liveness in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now_s, now_s, rev, mtime, liveness, f"sha_{sid}", 1000,
                 None),
            )

        conn.commit()

        # 1: completeness returns entries
        comp = completeness(conn)
        assert len(comp) > 0
        checks += 1

        # 2: paper kind has 2 sources, both with rev
        paper = next(c for c in comp if c["kind"] == "paper")
        assert paper["source_count"] == 2
        assert paper["has_rev"] == 2
        checks += 1

        # 3: local_md has 1 with rev, 1 with mtime
        lmd = next(c for c in comp if c["kind"] == "local_md")
        assert lmd["has_rev"] == 1
        assert lmd["has_mtime"] == 1
        checks += 1

        # 4: hf_dataset has neither
        hf = next(c for c in comp if c["kind"] == "hf_dataset")
        assert hf["has_neither"] == 1
        checks += 1

        # 5: age-distribution returns entries
        ages = age_distribution(conn)
        assert len(ages) > 0
        checks += 1

        # 6: shares sum to approximately 1.0
        total_share = sum(a["share"] for a in ages)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 7: recent bucket (<=7d) has entries (s1 now, s3 5d, s6 5d)
        recent = next((a for a in ages if a["bucket"] == "<=7d"), None)
        assert recent is not None
        assert recent["count"] >= 2
        checks += 1

        # 8: 181-365d bucket has s2 (200 days old)
        old_bucket = next(
            (a for a in ages if a["bucket"] == "181-365d"), None
        )
        assert old_bucket is not None
        assert old_bucket["count"] == 1
        checks += 1

        # 9: per-kind returns entries
        pk = per_kind_provenance(conn)
        assert len(pk) > 0
        checks += 1

        # 10: paper kind has 2 distinct revs
        pk_paper = next(p for p in pk if p["kind"] == "paper")
        assert pk_paper["distinct_revs"] == 2
        checks += 1

        # 11: summary has correct totals
        summary = provenance_summary(conn)
        assert summary["total_sources"] == 6
        assert summary["rev_populated"] == 4
        assert summary["mtime_populated"] == 4
        checks += 1

        # 12: distinct revs and kinds
        assert summary["distinct_revs"] == 4
        assert summary["distinct_kinds"] == 4
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(comp)
        _ = json.dumps(ages)
        _ = json.dumps(pk)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = completeness(conn2)
        assert empty == []
        empty_summary = provenance_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS upstream_provenance selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upstream provenance analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_comp = sub.add_parser("completeness",
                            help="Upstream field completeness")
    p_comp.add_argument("--db", default=DEFAULT_DB)
    p_comp.add_argument("--json", action="store_true")

    p_age = sub.add_parser("age-distribution",
                           help="Upstream modification age distribution")
    p_age.add_argument("--db", default=DEFAULT_DB)
    p_age.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("per-kind",
                            help="Upstream revision patterns per kind")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Upstream provenance statistics")
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

    if args.cmd == "completeness":
        results = completeness(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  n={r['source_count']:3d}  "
                      f"rev={r['rev_rate']:.0%}  "
                      f"mtime={r['mtime_rate']:.0%}  "
                      f"neither={r['has_neither']}")

    elif args.cmd == "age-distribution":
        results = age_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bucket']:10s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-kind":
        results = per_kind_provenance(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['kind']:12s}  n={r['source_count']:3d}  "
                      f"revs={r['distinct_revs']}  "
                      f"populated={r['rev_populated']}")

    elif args.cmd == "summary":
        result = provenance_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}")
            print(f"  Rev: {result['rev_populated']} "
                  f"({result['rev_rate']:.1%})  "
                  f"Mtime: {result['mtime_populated']} "
                  f"({result['mtime_rate']:.1%})")
            print(f"  Distinct revs: {result['distinct_revs']}  "
                  f"Kinds: {result['distinct_kinds']}")
            if result["oldest_mtime"]:
                print(f"  Oldest: {result['oldest_mtime']}  "
                      f"Newest: {result['newest_mtime']}")

    conn.close()


if __name__ == "__main__":
    main()
