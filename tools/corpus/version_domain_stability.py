#!/usr/bin/env python3
"""Version-domain stability: do frequently-revised chunks cluster by domain.

Zero joins between chunk_versions and chunk_domains exist anywhere in
the codebase.  This tool answers whether frequently-revised chunks
cluster in certain domains, and whether domain assignments correlate
with version depth.

Usage:
    python tools/corpus/version_domain_stability.py churn-by-domain [--db PATH] [--json]
    python tools/corpus/version_domain_stability.py stability [--db PATH] [--json]
    python tools/corpus/version_domain_stability.py volatile [--db PATH] [--json]
    python tools/corpus/version_domain_stability.py summary [--db PATH] [--json]
    python tools/corpus/version_domain_stability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def churn_by_domain(conn) -> list[dict]:
    """Mean version count per domain."""
    rows = conn.execute(
        "SELECT cd.domain, cv.chunk_id, max(cv.version_num) AS max_ver "
        "FROM chunk_versions cv "
        "JOIN chunk_domains cd ON cv.chunk_id = cd.chunk_id "
        "GROUP BY cd.domain, cv.chunk_id"
    ).fetchall()

    if not rows:
        return []

    by_dom: dict[str, list[int]] = {}
    for dom, _, max_ver in rows:
        if dom not in by_dom:
            by_dom[dom] = []
        by_dom[dom].append(max_ver)

    results = []
    for dom in sorted(by_dom):
        versions = by_dom[dom]
        n = len(versions)
        total = sum(versions)
        results.append({
            "domain": dom,
            "chunk_count": n,
            "total_versions": total,
            "mean_versions": round(total / n, 2) if n > 0 else 0.0,
            "max_version": max(versions),
        })

    return results


def domain_stability(conn) -> list[dict]:
    """Stability classification per domain based on version churn."""
    cbd = churn_by_domain(conn)

    if not cbd:
        return []

    results = []
    for d in cbd:
        mv = d["mean_versions"]
        if mv <= 1.0:
            label = "stable"
        elif mv <= 2.0:
            label = "moderate"
        elif mv <= 4.0:
            label = "active"
        else:
            label = "volatile"
        results.append({
            "domain": d["domain"],
            "mean_versions": d["mean_versions"],
            "max_version": d["max_version"],
            "stability": label,
        })

    return results


def volatile_chunks(conn, threshold: int = 3) -> list[dict]:
    """Chunks with high version count and their domain assignments."""
    rows = conn.execute(
        "SELECT cv.chunk_id, max(cv.version_num) AS max_ver "
        "FROM chunk_versions cv "
        "GROUP BY cv.chunk_id "
        "HAVING max(cv.version_num) >= ?"
        , (threshold,)
    ).fetchall()

    if not rows:
        return []

    results = []
    for cid, max_ver in rows:
        dom_rows = conn.execute(
            "SELECT domain, score FROM chunk_domains "
            "WHERE chunk_id = ? ORDER BY score DESC",
            (cid,)
        ).fetchall()
        domains = [
            {"domain": d, "score": round(s, 4)}
            for d, s in dom_rows
        ]
        results.append({
            "chunk_id": cid,
            "max_version": max_ver,
            "domains": domains,
            "domain_count": len(domains),
        })

    results.sort(key=lambda r: r["max_version"], reverse=True)
    return results


def stability_summary(conn) -> dict:
    """Aggregate version-domain stability statistics."""
    cbd = churn_by_domain(conn)
    ds = domain_stability(conn)

    if not cbd:
        return {
            "domains_with_versions": 0,
            "total_versioned_chunks": 0,
            "stability_counts": {},
            "most_volatile_domain": None,
            "most_stable_domain": None,
        }

    stability_counts: dict[str, int] = {}
    for d in ds:
        label = d["stability"]
        stability_counts[label] = stability_counts.get(label, 0) + 1

    most_volatile = max(cbd, key=lambda d: d["mean_versions"])
    most_stable = min(cbd, key=lambda d: d["mean_versions"])
    total_chunks = sum(d["chunk_count"] for d in cbd)

    return {
        "domains_with_versions": len(cbd),
        "total_versioned_chunks": total_chunks,
        "stability_counts": stability_counts,
        "most_volatile_domain": most_volatile["domain"],
        "most_stable_domain": most_stable["domain"],
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted", now),
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "version_id TEXT PRIMARY KEY, "
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "version_num INTEGER NOT NULL, "
            "norm_sha256 TEXT NOT NULL, "
            "word_count INTEGER NOT NULL, "
            "snapshot_utc TEXT NOT NULL, "
            "UNIQUE(chunk_id, version_num))"
        )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "domain TEXT NOT NULL, "
            "score REAL NOT NULL, "
            "classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )

        # c1: 5 versions (volatile), domains: ml, nlp
        # c2: 2 versions (moderate), domains: ml, systems
        # c3: 1 version (stable), domains: systems
        # c4: 3 versions (active), domains: nlp
        versions = [
            ("v1", "c1", 1), ("v2", "c1", 2), ("v3", "c1", 3),
            ("v4", "c1", 4), ("v5", "c1", 5),
            ("v6", "c2", 1), ("v7", "c2", 2),
            ("v8", "c3", 1),
            ("v9", "c4", 1), ("v10", "c4", 2), ("v11", "c4", 3),
        ]
        for vid, cid, vnum in versions:
            conn.execute(
                "INSERT INTO chunk_versions (version_id, chunk_id, "
                "version_num, norm_sha256, word_count, snapshot_utc) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (vid, cid, vnum, f"sha_{vid}", 10, now),
            )

        domains = [
            ("c1", "ml", 0.9), ("c1", "nlp", 0.7),
            ("c2", "ml", 0.8), ("c2", "systems", 0.6),
            ("c3", "systems", 0.9),
            ("c4", "nlp", 0.85),
        ]
        for cid, dom, score in domains:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)",
                (cid, dom, score, now),
            )

        conn.commit()

        # 1: churn-by-domain returns 3 domains
        cbd = churn_by_domain(conn)
        assert len(cbd) == 3
        checks += 1

        # 2: ml domain: c1(5 vers), c2(2 vers) = mean 3.5
        ml = next(d for d in cbd if d["domain"] == "ml")
        assert ml["chunk_count"] == 2
        assert abs(ml["mean_versions"] - 3.5) < 0.01
        checks += 1

        # 3: systems domain: c2(2 vers), c3(1 ver) = mean 1.5
        sys_d = next(d for d in cbd if d["domain"] == "systems")
        assert sys_d["chunk_count"] == 2
        assert abs(sys_d["mean_versions"] - 1.5) < 0.01
        checks += 1

        # 4: nlp domain: c1(5 vers), c4(3 vers) = mean 4.0
        nlp = next(d for d in cbd if d["domain"] == "nlp")
        assert abs(nlp["mean_versions"] - 4.0) < 0.01
        checks += 1

        # 5: stability labels assigned correctly
        ds = domain_stability(conn)
        assert len(ds) == 3
        checks += 1

        # 6: ml is active (mean 3.5, 2.0 < 3.5 <= 4.0)
        ml_s = next(d for d in ds if d["domain"] == "ml")
        assert ml_s["stability"] == "active"
        checks += 1

        # 7: systems is moderate (mean 1.5, 1.0 < 1.5 <= 2.0)
        sys_s = next(d for d in ds if d["domain"] == "systems")
        assert sys_s["stability"] == "moderate"
        checks += 1

        # 8: nlp is active (mean 4.0, 2.0 < 4.0 <= 4.0)
        nlp_s = next(d for d in ds if d["domain"] == "nlp")
        assert nlp_s["stability"] == "active"
        checks += 1

        # 9: volatile chunks with threshold 3
        vc = volatile_chunks(conn, threshold=3)
        assert len(vc) == 2  # c1 (5), c4 (3)
        checks += 1

        # 10: c1 is most volatile with 5 versions
        assert vc[0]["chunk_id"] == "c1"
        assert vc[0]["max_version"] == 5
        checks += 1

        # 11: c1 has 2 domains
        assert vc[0]["domain_count"] == 2
        checks += 1

        # 12: summary has correct totals
        summary = stability_summary(conn)
        assert summary["domains_with_versions"] == 3
        assert summary["most_volatile_domain"] == "nlp"
        assert summary["most_stable_domain"] == "systems"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(cbd)
        _ = json.dumps(ds)
        _ = json.dumps(vc)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_versions ("
            "version_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, "
            "version_num INTEGER NOT NULL, norm_sha256 TEXT NOT NULL, "
            "word_count INTEGER NOT NULL, snapshot_utc TEXT NOT NULL, "
            "UNIQUE(chunk_id, version_num))"
        )
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL NOT NULL, classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        empty = churn_by_domain(conn2)
        assert empty == []
        empty_summary = stability_summary(conn2)
        assert empty_summary["domains_with_versions"] == 0
        checks += 1

    print(
        f"PASS version_domain_stability selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Version-domain stability analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_cbd = sub.add_parser("churn-by-domain",
                           help="Version churn per domain")
    p_cbd.add_argument("--db", default=DEFAULT_DB)
    p_cbd.add_argument("--json", action="store_true")

    p_ds = sub.add_parser("stability",
                          help="Domain stability labels")
    p_ds.add_argument("--db", default=DEFAULT_DB)
    p_ds.add_argument("--json", action="store_true")

    p_vc = sub.add_parser("volatile",
                          help="High-churn chunks with domains")
    p_vc.add_argument("--db", default=DEFAULT_DB)
    p_vc.add_argument("--json", action="store_true")
    p_vc.add_argument("--threshold", type=int, default=3)

    p_sum = sub.add_parser("summary",
                           help="Stability statistics")
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

    if args.cmd == "churn-by-domain":
        results = churn_by_domain(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['domain']:16s}  "
                      f"chunks={r['chunk_count']:3d}  "
                      f"mean={r['mean_versions']:.1f}  "
                      f"max={r['max_version']}")

    elif args.cmd == "stability":
        results = domain_stability(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['domain']:16s}  "
                      f"mean={r['mean_versions']:.1f}  "
                      f"{r['stability']}")

    elif args.cmd == "volatile":
        results = volatile_chunks(
            conn, threshold=args.threshold
        )
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                doms = ", ".join(
                    d["domain"] for d in r["domains"]
                )
                print(f"  {r['chunk_id']}  "
                      f"v={r['max_version']}  "
                      f"domains=[{doms}]")

    elif args.cmd == "summary":
        result = stability_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Domains: "
                  f"{result['domains_with_versions']}  "
                  f"Chunks: "
                  f"{result['total_versioned_chunks']}")
            print(f"  Stability: "
                  f"{result['stability_counts']}")
            if result["most_volatile_domain"]:
                print(f"  Most volatile: "
                      f"{result['most_volatile_domain']}  "
                      f"Most stable: "
                      f"{result['most_stable_domain']}")

    conn.close()


if __name__ == "__main__":
    main()
