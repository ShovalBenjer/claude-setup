#!/usr/bin/env python3
"""Publisher domain profile: which publishers produce which semantic domains.

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_license_distribution.py profiles publishers by license.
No tool joins sources.publisher with chunk_domains to measure which
publishers concentrate which knowledge domains, whether publisher
breadth correlates with domain diversity, or how domain scores
vary by publisher.

Usage:
    python tools/corpus/publisher_domain_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_domain_profile.py by-domain [--db PATH] [--json]
    python tools/corpus/publisher_domain_profile.py concentration [--db PATH] [--json]
    python tools/corpus/publisher_domain_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_domain_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def domains_by_publisher(conn) -> list[dict]:
    """Domain distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS domain_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.publisher
        ORDER BY domain_assignments DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_domains": r[1],
            "domain_assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def publishers_by_domain(conn) -> list[dict]:
    """Publisher distribution per domain."""
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
               COUNT(cd.domain) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks,
               ROUND(AVG(cd.score), 4) AS avg_score
        FROM chunk_domains cd
        JOIN chunks c ON c.chunk_id = cd.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY cd.domain
        ORDER BY distinct_publishers DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "distinct_publishers": r[1],
            "assignments": r[2],
            "classified_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def publisher_domain_concentration(conn) -> list[dict]:
    """Per-publisher domain concentration: ratio of distinct domains to assignments."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(cd.domain) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS classified_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        GROUP BY s.publisher
        HAVING COUNT(cd.domain) >= 2
        ORDER BY CAST(COUNT(DISTINCT cd.domain) AS REAL) / COUNT(cd.domain), s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_domains": r[1],
            "total_assignments": r[2],
            "classified_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def publisher_domain_summary(conn) -> dict:
    """Aggregate publisher-domain statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    publishers_with_domains = conn.execute(
        """
        SELECT COUNT(DISTINCT s.publisher)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_domains"
    ).fetchone()[0]

    avg_domains_per_publisher = conn.execute(
        """
        SELECT ROUND(AVG(dom_count), 4)
        FROM (
            SELECT s.publisher, COUNT(DISTINCT cd.domain) AS dom_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_domains cd ON cd.chunk_id = c.chunk_id
            GROUP BY s.publisher
        )
        """
    ).fetchone()[0]

    single_publisher_domains = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT cd.domain
            FROM chunk_domains cd
            JOIN chunks c ON c.chunk_id = cd.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY cd.domain
            HAVING COUNT(DISTINCT s.publisher) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "publishers_with_domains": publishers_with_domains,
        "publisher_domain_coverage": round(publishers_with_domains / max(total_publishers, 1), 4),
        "total_distinct_domains": total_domains,
        "total_domain_assignments": total_assignments,
        "avg_domains_per_publisher": avg_domains_per_publisher or 0.0,
        "single_publisher_domains": single_publisher_domains,
        "single_publisher_domain_rate": round(single_publisher_domains / max(total_domains, 1), 4),
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "intro", "claim", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))

        # Domains: acme gets ML+NLP+stats, globex gets ML+bio, null pub gets NLP
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ML", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "NLP", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "stats", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ML", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "bio", 0.6, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "NLP", 0.75, t1))
        conn.commit()

        # 1. by-publisher: acme has 3 distinct domains
        bp = domains_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_domains"] == 3
        ok += 1

        # 2. acme has 3 domain assignments
        assert acme["domain_assignments"] == 3
        ok += 1

        # 3. globex has 2 distinct domains
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_domains"] == 2
        ok += 1

        # 4. by-domain: "ML" spans 2 named publishers (acme, globex); null excluded
        bd = publishers_by_domain(conn)
        ml = [r for r in bd if r["domain"] == "ML"][0]
        assert ml["distinct_publishers"] == 2
        ok += 1

        # 5. "bio" spans 1 publisher (globex)
        bio = [r for r in bd if r["domain"] == "bio"][0]
        assert bio["distinct_publishers"] == 1
        ok += 1

        # 6. "NLP" spans 1 named publisher (acme); null excluded by COUNT(DISTINCT)
        nlp = [r for r in bd if r["domain"] == "NLP"][0]
        assert nlp["distinct_publishers"] == 1
        ok += 1

        # 7. concentration: acme has 3/3=1.0
        conc = publisher_domain_concentration(conn)
        acme_conc = [r for r in conc if r["publisher"] == "acme"][0]
        assert acme_conc["diversity_ratio"] == 1.0
        ok += 1

        # 8. globex has 2/2=1.0
        globex_conc = [r for r in conc if r["publisher"] == "globex"][0]
        assert globex_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. null publisher not in concentration (only 1 assignment)
        null_conc = [r for r in conc if r["publisher"] is None]
        assert len(null_conc) == 0
        ok += 1

        # 10. summary: publishers_with_domains = 2 (acme, globex; null excluded)
        s = publisher_domain_summary(conn)
        assert s["publishers_with_domains"] == 2
        ok += 1

        # 11. total_distinct_domains = 4
        assert s["total_distinct_domains"] == 4
        ok += 1

        # 12. single_publisher_domains: stats (acme), bio (globex), NLP (1 named) = 3
        assert s["single_publisher_domains"] == 3, f"expected 3, got {s['single_publisher_domains']}"
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["publisher_domain_coverage"] == s["publisher_domain_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = publisher_domain_summary(conn)
        assert s["publishers_with_domains"] == 0
        assert s["total_distinct_domains"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher domain profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-domain", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_domain_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = domains_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher domain data found.")
            else:
                print(f"{'publisher':<20} {'domains':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_domains']:<8} {r['domain_assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-domain":
        rows = publishers_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No domain publisher data found.")
            else:
                print(f"{'domain':<20} {'publishers':<12} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<20} {r['distinct_publishers']:<12} {r['assignments']:<12} {r['classified_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = publisher_domain_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with multiple domains found.")
            else:
                print(f"{'publisher':<20} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_domains']:<10} {r['total_assignments']:<8} {r['classified_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = publisher_domain_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
