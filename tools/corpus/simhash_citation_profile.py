#!/usr/bin/env python3
"""Simhash citation profile: how simhash collision groups distribute across citation counts.

simhash_domain_profile.py profiles simhash groups by semantic domains.
simhash_tag_profile.py profiles simhash groups by chunk tags.
No tool cross-tabulates chunks.simhash with chunks.citation_count to measure
whether near-duplicate clusters differ in citation activity, or how citation
density distributes across simhash collision groups.

Usage:
    python tools/corpus/simhash_citation_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_citation_profile.py by-bucket [--db PATH] [--json]
    python tools/corpus/simhash_citation_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _cite_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n <= 5:
        return "1-5"
    if n <= 20:
        return "6-20"
    return "21+"


def citations_by_simhash(conn) -> list[dict]:
    """Citation statistics per simhash collision group (groups with 2+ chunks)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.citation_count) AS total_citations,
               ROUND(AVG(c.citation_count), 4) AS avg_citations,
               MIN(c.citation_count) AS min_citations,
               MAX(c.citation_count) AS max_citations
        FROM chunks c
        GROUP BY c.simhash
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY total_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "total_chunks": r[1],
            "total_citations": r[2],
            "avg_citations": r[3],
            "min_citations": r[4],
            "max_citations": r[5],
            "citation_spread": r[5] - r[4],
        }
        for r in rows
    ]


def simhash_groups_by_bucket(conn) -> list[dict]:
    """Simhash group distribution per citation bucket."""
    rows = conn.execute(
        """
        SELECT c.simhash, c.citation_count
        FROM chunks c
        """
    ).fetchall()
    buckets: dict[str, dict] = {}
    simhashes_per_bucket: dict[str, set] = {}
    for simhash, cite_count in rows:
        b = _cite_bucket(cite_count)
        if b not in buckets:
            buckets[b] = {"total_chunks": 0, "total_citations": 0}
            simhashes_per_bucket[b] = set()
        buckets[b]["total_chunks"] += 1
        buckets[b]["total_citations"] += cite_count
        simhashes_per_bucket[b].add(simhash)
    return sorted(
        [
            {
                "bucket": b,
                "distinct_simhashes": len(simhashes_per_bucket[b]),
                "total_chunks": buckets[b]["total_chunks"],
                "total_citations": buckets[b]["total_citations"],
            }
            for b in buckets
        ],
        key=lambda r: r["total_chunks"],
        reverse=True,
    )


def simhash_citation_concentration(conn) -> list[dict]:
    """Per-simhash citation concentration: groups with 2+ chunks, ordered by citation spread."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.citation_count) AS total_citations,
               ROUND(AVG(c.citation_count), 4) AS avg_citations,
               MIN(c.citation_count) AS min_citations,
               MAX(c.citation_count) AS max_citations
        FROM chunks c
        GROUP BY c.simhash
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY (MAX(c.citation_count) - MIN(c.citation_count)) DESC, total_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "total_chunks": r[1],
            "total_citations": r[2],
            "avg_citations": r[3],
            "min_citations": r[4],
            "max_citations": r[5],
            "citation_spread": r[5] - r[4],
        }
        for r in rows
    ]


def simhash_citation_summary(conn) -> dict:
    """Aggregate simhash-citation statistics."""
    total_simhashes = conn.execute(
        "SELECT COUNT(DISTINCT simhash) FROM chunks"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT simhash
            FROM chunks
            GROUP BY simhash
            HAVING COUNT(chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    uneven_citation_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT simhash
            FROM chunks
            GROUP BY simhash
            HAVING COUNT(chunk_id) >= 2
               AND MAX(citation_count) > MIN(citation_count)
        )
        """
    ).fetchone()[0]

    total_citations = conn.execute(
        "SELECT COALESCE(SUM(citation_count), 0) FROM chunks"
    ).fetchone()[0]

    avg_citations = conn.execute(
        "SELECT ROUND(COALESCE(AVG(citation_count), 0), 4) FROM chunks"
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_chunks": total_chunks,
        "collision_groups": collision_groups,
        "uneven_citation_groups": uneven_citation_groups,
        "uneven_citation_rate": round(uneven_citation_groups / max(collision_groups, 1), 4),
        "total_citations": total_citations,
        "avg_citations": avg_citations,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # simhash 1000: c1 (cite=0), c2 (cite=10) -- uneven; simhash 2000: c3 (cite=5), c4 (cite=5) -- even; simhash 3000: c5 (cite=25) -- singleton
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1000, 10, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 5, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 5, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 25, "accepted", None, t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 citation_spread = 10
        bs = citations_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["citation_spread"] == 10
        ok += 1

        # 2. simhash 2000 citation_spread = 0 (even)
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["citation_spread"] == 0
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-bucket: bucket "0" has chunks with 0 citations (c1)
        bb = simhash_groups_by_bucket(conn)
        b0 = [r for r in bb if r["bucket"] == "0"][0]
        assert b0["total_chunks"] == 1
        ok += 1

        # 5. bucket "6-20" has c2 (10 citations)
        b620 = [r for r in bb if r["bucket"] == "6-20"][0]
        assert b620["total_chunks"] == 1
        ok += 1

        # 6. bucket "1-5" has c3, c4 (5 citations each)
        b15 = [r for r in bb if r["bucket"] == "1-5"][0]
        assert b15["total_chunks"] == 2
        ok += 1

        # 7. concentration: simhash 1000 ordered first (spread=10 > spread=0)
        conc = simhash_citation_concentration(conn)
        assert conc[0]["simhash"] == 1000
        ok += 1

        # 8. simhash 2000 has spread=0
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["citation_spread"] == 0
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_citation_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. uneven_citation_groups = 1 (1000)
        assert s["uneven_citation_groups"] == 1
        ok += 1

        # 12. total_citations = 0+10+5+5+25 = 45
        assert s["total_citations"] == 45
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["uneven_citation_rate"] == s["uneven_citation_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = simhash_citation_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash citation profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-bucket", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = citations_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'chunks':<8} {'total':<8} {'avg':<10} {'min':<6} {'max':<6} {'spread'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['total_chunks']:<8} {r['total_citations']:<8} {r['avg_citations']:<10.4f} {r['min_citations']:<6} {r['max_citations']:<6} {r['citation_spread']}")
    elif args.command == "by-bucket":
        rows = simhash_groups_by_bucket(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No citation data found.")
            else:
                print(f"{'bucket':<10} {'simhashes':<12} {'chunks':<8} {'citations'}")
                for r in rows:
                    print(f"{r['bucket']:<10} {r['distinct_simhashes']:<12} {r['total_chunks']:<8} {r['total_citations']}")
    elif args.command == "concentration":
        rows = simhash_citation_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups found.")
            else:
                print(f"{'simhash':<16} {'chunks':<8} {'total':<8} {'avg':<10} {'min':<6} {'max':<6} {'spread'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['total_chunks']:<8} {r['total_citations']:<8} {r['avg_citations']:<10.4f} {r['min_citations']:<6} {r['max_citations']:<6} {r['citation_spread']}")
    elif args.command == "summary":
        s = simhash_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
