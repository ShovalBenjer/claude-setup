#!/usr/bin/env python3
"""License tag profile: which license types correlate with which tags.

license_gate.py enforces license compliance.
publisher_license_distribution.py profiles publishers by license.
No tool joins sources.license_spdx with chunk_tags to measure which
license categories concentrate which tags, whether open licenses
attract broader tag vocabularies, or how tag scores vary by license.

Usage:
    python tools/corpus/license_tag_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/license_tag_profile.py diversity [--db PATH] [--json]
    python tools/corpus/license_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_license(conn) -> list[dict]:
    """Tag distribution per license type."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        ORDER BY tag_assignments DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def licenses_by_tag(conn) -> list[dict]:
    """License distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(ct.tag) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY ct.tag
        ORDER BY distinct_licenses DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_licenses": r[1],
            "assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def license_tag_diversity(conn) -> list[dict]:
    """Per-license tag diversity: ratio of distinct tags to assignments."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "tagged_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def license_tag_summary(conn) -> dict:
    """Aggregate license-tag statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    licenses_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
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

    avg_tags_per_license = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT s.license_spdx, COUNT(DISTINCT ct.tag) AS tag_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY s.license_spdx
        )
        """
    ).fetchone()[0]

    single_license_tags = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT s.license_spdx) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_licenses": total_licenses,
        "licenses_with_tags": licenses_with_tags,
        "license_tag_coverage": round(licenses_with_tags / max(total_licenses, 1), 4),
        "total_distinct_tags": total_tags,
        "total_tag_assignments": total_assignments,
        "avg_tags_per_license": avg_tags_per_license or 0.0,
        "single_license_tags": single_license_tags,
        "single_license_tag_rate": round(single_license_tags / max(total_tags, 1), 4),
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
        # Three licenses: MIT (s1), Apache-2.0 (s2), CC-BY-4.0 (s3)
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None),
        )

        # Chunks: c1,c2 from s1 (MIT); c3 from s2 (Apache); c4 from s3 (CC-BY)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "intro", "claim", None, "t", "t", 15, "jkl", 4000, 0, "accepted", None, t1))

        # Tags: MIT gets law+tech+science, Apache gets tech+bio, CC-BY gets law
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "science", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "bio", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "law", 0.75, t1))
        conn.commit()

        # 1. by-license: MIT has 3 distinct tags (law, tech, science)
        bl = tags_by_license(conn)
        mit = [r for r in bl if r["license_spdx"] == "MIT"][0]
        assert mit["distinct_tags"] == 3
        ok += 1

        # 2. MIT has 3 tag assignments
        assert mit["tag_assignments"] == 3
        ok += 1

        # 3. Apache-2.0 has 2 distinct tags (tech, bio)
        apache = [r for r in bl if r["license_spdx"] == "Apache-2.0"][0]
        assert apache["distinct_tags"] == 2
        ok += 1

        # 4. CC-BY-4.0 has 1 tag
        ccby = [r for r in bl if r["license_spdx"] == "CC-BY-4.0"][0]
        assert ccby["distinct_tags"] == 1
        ok += 1

        # 5. by-tag: "tech" spans 2 licenses (MIT, Apache)
        bt = licenses_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_licenses"] == 2
        ok += 1

        # 6. "law" spans 2 licenses (MIT, CC-BY)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_licenses"] == 2
        ok += 1

        # 7. "bio" spans 1 license (Apache only)
        bio = [r for r in bt if r["tag"] == "bio"][0]
        assert bio["distinct_licenses"] == 1
        ok += 1

        # 8. diversity: MIT has 3/3=1.0
        div = license_tag_diversity(conn)
        mit_div = [r for r in div if r["license_spdx"] == "MIT"][0]
        assert mit_div["diversity_ratio"] == 1.0
        ok += 1

        # 9. Apache has 2/2=1.0
        apache_div = [r for r in div if r["license_spdx"] == "Apache-2.0"][0]
        assert apache_div["diversity_ratio"] == 1.0
        ok += 1

        # 10. CC-BY not in diversity (only 1 assignment)
        ccby_div = [r for r in div if r["license_spdx"] == "CC-BY-4.0"]
        assert len(ccby_div) == 0
        ok += 1

        # 11. summary: licenses_with_tags = 3
        s = license_tag_summary(conn)
        assert s["licenses_with_tags"] == 3
        ok += 1

        # 12. total_distinct_tags = 4 (law, tech, science, bio)
        assert s["total_distinct_tags"] == 4
        ok += 1

        # 13. single_license_tags: science (MIT only), bio (Apache only) = 2
        assert s["single_license_tags"] == 2, f"expected 2, got {s['single_license_tags']}"
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = license_tag_summary(conn)
        assert s["licenses_with_tags"] == 0
        assert s["total_distinct_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License tag profile analysis")
    ap.add_argument("command", choices=["by-license", "by-tag", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = tags_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license tag data found.")
            else:
                print(f"{'license':<20} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['license_spdx']:<20} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = licenses_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag license data found.")
            else:
                print(f"{'tag':<20} {'licenses':<10} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_licenses']:<10} {r['assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = license_tag_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple tags found.")
            else:
                print(f"{'license':<20} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['license_spdx']:<20} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['tagged_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = license_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
