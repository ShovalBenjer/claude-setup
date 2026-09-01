#!/usr/bin/env python3
"""Simhash domain profile: how simhash collision groups distribute across semantic domains.

simhash_tag_profile.py profiles simhash groups by chunk tags.
simhash_license_profile.py profiles simhash groups by source license.
No tool cross-tabulates chunks.simhash with chunk_domains.domain to measure
whether near-duplicate clusters share the same semantic domains, or how
domain classifications distribute across simhash collision groups.

Usage:
    python tools/corpus/simhash_domain_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/simhash_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_simhash(conn) -> list[dict]:
    """Domain distribution per simhash collision group (groups with 2+ classified chunks)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.simhash
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY classified_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_domains": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def simhash_groups_by_domain(conn) -> list[dict]:
    """Simhash group distribution per semantic domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY cd.domain
        ORDER BY classified_chunks DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_simhashes": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def simhash_domain_concentration(conn) -> list[dict]:
    """Per-simhash domain concentration: groups with 2+ classified chunks, ordered by domain diversity."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               COUNT(cd.domain) AS domain_assignments,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY c.simhash
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY distinct_domains DESC, classified_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_domains": r[1],
            "classified_chunks": r[2],
            "domain_assignments": r[3],
            "avg_score": r[4],
            "domain_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def simhash_domain_summary(conn) -> dict:
    """Aggregate simhash-domain statistics."""
    total_simhashes = conn.execute(
        "SELECT COUNT(DISTINCT c.simhash) FROM chunks c JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_classified_chunks = conn.execute(
        "SELECT COUNT(DISTINCT c.chunk_id) FROM chunks c JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.simhash
            HAVING COUNT(DISTINCT c.chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    cross_domain_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.simhash
            HAVING COUNT(DISTINCT c.chunk_id) >= 2
               AND COUNT(DISTINCT cd.domain) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash, cd.domain
            FROM chunks c
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY c.simhash, cd.domain
        )
        """
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_classified_chunks": total_classified_chunks,
        "collision_groups": collision_groups,
        "cross_domain_groups": cross_domain_groups,
        "cross_domain_rate": round(cross_domain_groups / max(collision_groups, 1), 4),
        "distinct_simhash_domain_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # simhash 1000: c1 (nlp, ml), c2 (nlp) -- cross-domain; simhash 2000: c3 (ml), c4 (ml) -- same; simhash 3000: c5 (web) -- singleton
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "nlp", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "nlp", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "ml", 0.5, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c5", "web", 0.4, t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 has 2 distinct domains (nlp, ml)
        bs = domains_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["distinct_domains"] == 2
        ok += 1

        # 2. simhash 2000 has 1 distinct domain (ml)
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["distinct_domains"] == 1
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-domain: "nlp" has 1 distinct simhash (1000)
        bd = simhash_groups_by_domain(conn)
        nlp = [r for r in bd if r["domain"] == "nlp"][0]
        assert nlp["distinct_simhashes"] == 1
        ok += 1

        # 5. "ml" has 2 distinct simhashes (1000, 2000)
        ml = [r for r in bd if r["domain"] == "ml"][0]
        assert ml["distinct_simhashes"] == 2
        ok += 1

        # 6. "ml" has 3 classified chunks (c1, c3, c4)
        assert ml["classified_chunks"] == 3
        ok += 1

        # 7. concentration: simhash 1000 domain_ratio = 2/2 = 1.0
        conc = simhash_domain_concentration(conn)
        c1000 = [r for r in conc if r["simhash"] == 1000][0]
        assert c1000["domain_ratio"] == 1.0
        ok += 1

        # 8. simhash 2000 domain_ratio = 1/2 = 0.5
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["domain_ratio"] == 0.5
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_domain_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. cross_domain_groups = 1 (1000)
        assert s["cross_domain_groups"] == 1
        ok += 1

        # 12. total_simhashes = 3
        assert s["total_simhashes"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_domain_rate"] == s["cross_domain_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = simhash_domain_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_classified_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash domain profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = domains_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups with domains found.")
            else:
                print(f"{'simhash':<16} {'domains':<10} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_domains']:<10} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = simhash_groups_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain simhash data found.")
            else:
                print(f"{'domain':<16} {'simhashes':<12} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['distinct_simhashes']:<12} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = simhash_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups with domains found.")
            else:
                print(f"{'simhash':<16} {'domains':<10} {'chunks':<8} {'assignments':<14} {'avg_score':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_domains']:<10} {r['classified_chunks']:<8} {r['domain_assignments']:<14} {r['avg_score']:<12.4f} {r['domain_ratio']:.4f}")
    elif args.command == "summary":
        s = simhash_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
