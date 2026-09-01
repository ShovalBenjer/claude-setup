#!/usr/bin/env python3
"""Publisher tag profile: which publishers produce which tag vocabularies.

publisher_license_distribution.py profiles publishers by license.
tag_landscape.py profiles tags corpus-wide.
No tool joins sources.publisher with chunk_tags to measure which
publishers concentrate which tags, whether publisher diversity
correlates with tag diversity, or how tag scores vary by publisher.

Usage:
    python tools/corpus/publisher_tag_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/publisher_tag_profile.py concentration [--db PATH] [--json]
    python tools/corpus/publisher_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_publisher(conn) -> list[dict]:
    """Tag distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.publisher
        ORDER BY tag_assignments DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def publishers_by_tag(conn) -> list[dict]:
    """Publisher distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
               COUNT(ct.tag) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY ct.tag
        ORDER BY distinct_publishers DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_publishers": r[1],
            "assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def publisher_tag_concentration(conn) -> list[dict]:
    """Per-publisher tag concentration: ratio of distinct tags to assignments."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.publisher
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "tagged_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def publisher_tag_summary(conn) -> dict:
    """Aggregate publisher-tag statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    publishers_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT s.publisher)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_tags"
    ).fetchone()[0]

    avg_tags_per_publisher = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT s.publisher, COUNT(DISTINCT ct.tag) AS tag_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY s.publisher
        )
        """
    ).fetchone()[0]

    single_publisher_tags = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT s.publisher) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "publishers_with_tags": publishers_with_tags,
        "publisher_tag_coverage": round(publishers_with_tags / max(total_publishers, 1), 4),
        "total_distinct_tags": total_tags,
        "total_tag_assignments": total_assignments,
        "avg_tags_per_publisher": avg_tags_per_publisher or 0.0,
        "single_publisher_tags": single_publisher_tags,
        "single_publisher_tag_rate": round(single_publisher_tags / max(total_tags, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")

        t1 = "2026-01-01T00:00:00Z"
        # Two publishers: "acme" (s1) and "globex" (s2), plus null publisher (s3)
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

        # Chunks: c1,c2 from s1 (acme); c3,c4 from s2 (globex); c5 from s3 (null pub)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "def", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 2, "results", "claim", None, "t", "t", 35, "def", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s3", 1, "intro", "claim", None, "t", "t", 15, "ghi", 5000, 0, "accepted", None, t1))

        # Tags: acme gets law+tech+science, globex gets tech+bio, null pub gets law
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "science", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "bio", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c5", "law", 0.75, t1))
        conn.commit()

        # 1. by-publisher: acme has 3 distinct tags
        bp = tags_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_tags"] == 3, f"expected 3, got {acme['distinct_tags']}"
        ok += 1

        # 2. acme has 3 tag assignments
        assert acme["tag_assignments"] == 3
        ok += 1

        # 3. globex has 2 distinct tags
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_tags"] == 2
        ok += 1

        # 4. null publisher has 1 tag
        null_pub = [r for r in bp if r["publisher"] is None][0]
        assert null_pub["distinct_tags"] == 1
        ok += 1

        # 5. by-tag: "tech" spans 2 publishers (acme, globex)
        bt = publishers_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_publishers"] == 2
        ok += 1

        # 6. "bio" spans 1 publisher (globex only)
        bio = [r for r in bt if r["tag"] == "bio"][0]
        assert bio["distinct_publishers"] == 1
        ok += 1

        # 7. "law" spans 1 named publisher (acme); null excluded by COUNT(DISTINCT)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_publishers"] == 1
        ok += 1

        # 8. concentration: acme has diversity 3/3=1.0
        conc = publisher_tag_concentration(conn)
        acme_conc = [r for r in conc if r["publisher"] == "acme"][0]
        assert acme_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. globex has diversity 2/2=1.0
        globex_conc = [r for r in conc if r["publisher"] == "globex"][0]
        assert globex_conc["diversity_ratio"] == 1.0
        ok += 1

        # 10. null publisher not in concentration (only 1 assignment, below threshold)
        null_conc = [r for r in conc if r["publisher"] is None]
        assert len(null_conc) == 0
        ok += 1

        # 11. summary: publishers_with_tags = 2 (acme, globex; null excluded)
        s = publisher_tag_summary(conn)
        assert s["publishers_with_tags"] == 2
        ok += 1

        # 12. total_distinct_tags = 4 (law, tech, science, bio)
        assert s["total_distinct_tags"] == 4
        ok += 1

        # 13. single_publisher_tags: law (1 named), science (acme), bio (globex) = 3
        assert s["single_publisher_tags"] == 3, f"expected 3, got {s['single_publisher_tags']}"
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = publisher_tag_summary(conn)
        assert s["publishers_with_tags"] == 0
        assert s["total_distinct_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher tag profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-tag", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = tags_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher tag data found.")
            else:
                print(f"{'publisher':<20} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = publishers_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag publisher data found.")
            else:
                print(f"{'tag':<20} {'publishers':<12} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_publishers']:<12} {r['assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = publisher_tag_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with multiple tags found.")
            else:
                print(f"{'publisher':<20} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['tagged_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = publisher_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
