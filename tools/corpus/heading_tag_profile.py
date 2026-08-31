#!/usr/bin/env python3
"""Heading tag profile: how heading paths distribute across chunk tags.

heading_publisher_profile.py profiles headings by source publisher.
heading_license_profile.py profiles headings by source license.
No tool cross-tabulates chunks.heading_path with chunk_tags.tag to measure
which topic tags appear under which document sections, or how tag vocabulary
distributes across heading paths.

Usage:
    python tools/corpus/heading_tag_profile.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/heading_tag_profile.py concentration [--db PATH] [--json]
    python tools/corpus/heading_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/heading_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_heading(conn) -> list[dict]:
    """Tag distribution per heading path."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               COUNT(ct.tag) AS tag_assignments,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY tagged_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_tags": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def headings_by_tag(conn) -> list[dict]:
    """Heading distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT c.heading_path) AS distinct_headings,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               COUNT(ct.tag) AS tag_assignments,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY ct.tag
        ORDER BY tagged_chunks DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_headings": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def heading_tag_concentration(conn) -> list[dict]:
    """Per-heading tag concentration ordered by tag diversity."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               COUNT(ct.tag) AS tag_assignments,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY distinct_tags DESC, tagged_chunks DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_tags": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
            "tag_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_tag_summary(conn) -> dict:
    """Aggregate heading-tag statistics."""
    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT c.heading_path) FROM chunks c JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT c.chunk_id) FROM chunks c JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT ct.tag) FROM chunk_tags ct"
    ).fetchone()[0]

    multi_tag_headings = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.heading_path
            HAVING COUNT(DISTINCT ct.tag) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.heading_path, ct.tag
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.heading_path, ct.tag
        )
        """
    ).fetchone()[0]

    return {
        "total_headings": total_headings,
        "total_tagged_chunks": total_tagged_chunks,
        "total_tags": total_tags,
        "multi_tag_headings": multi_tag_headings,
        "multi_tag_rate": round(multi_tag_headings / max(total_headings, 1), 4),
        "distinct_heading_tag_pairs": distinct_pairs,
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
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))

        # intro: c1 (python, ml), c2 (python); methods: c3 (ml); results: c4 (web); c5 untagged
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "results", "claim", None, "t", "t", 35, "jkl", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3001, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))
        conn.commit()

        # 1. by-heading: intro has 2 distinct tags (python, ml)
        bh = tags_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_tags"] == 2
        ok += 1

        # 2. methods has 1 distinct tag (ml)
        methods = [r for r in bh if r["heading_path"] == "methods"][0]
        assert methods["distinct_tags"] == 1
        ok += 1

        # 3. results has 1 distinct tag (web) -- c5 is untagged
        results = [r for r in bh if r["heading_path"] == "results"][0]
        assert results["distinct_tags"] == 1
        ok += 1

        # 4. by-tag: "python" spans 1 heading (intro)
        bt = headings_by_tag(conn)
        python = [r for r in bt if r["tag"] == "python"][0]
        assert python["distinct_headings"] == 1
        ok += 1

        # 5. "ml" spans 2 headings (intro, methods)
        ml = [r for r in bt if r["tag"] == "ml"][0]
        assert ml["distinct_headings"] == 2
        ok += 1

        # 6. "python" has 2 tagged chunks (c1, c2)
        assert python["tagged_chunks"] == 2
        ok += 1

        # 7. concentration: intro tag_ratio = 2/2 = 1.0
        conc = heading_tag_concentration(conn)
        c_intro = [r for r in conc if r["heading_path"] == "intro"][0]
        assert c_intro["tag_ratio"] == 1.0
        ok += 1

        # 8. methods tag_ratio = 1/1 = 1.0
        c_methods = [r for r in conc if r["heading_path"] == "methods"][0]
        assert c_methods["tag_ratio"] == 1.0
        ok += 1

        # 9. results tagged_chunks = 1 (only c4 is tagged)
        c_results = [r for r in conc if r["heading_path"] == "results"][0]
        assert c_results["tagged_chunks"] == 1
        ok += 1

        # 10. summary: total_headings = 3 (intro, methods, results)
        s = heading_tag_summary(conn)
        assert s["total_headings"] == 3
        ok += 1

        # 11. multi_tag_headings = 1 (intro has python + ml)
        assert s["multi_tag_headings"] == 1
        ok += 1

        # 12. total_tags = 3 (python, ml, web)
        assert s["total_tags"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_tag_rate"] == s["multi_tag_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = heading_tag_summary(conn)
        assert s["total_headings"] == 0
        assert s["total_tagged_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading tag profile analysis")
    ap.add_argument("command", choices=["by-heading", "by-tag", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = tags_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading tag data found.")
            else:
                print(f"{'heading':<20} {'tags':<8} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['distinct_tags']:<8} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = headings_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag heading data found.")
            else:
                print(f"{'tag':<16} {'headings':<10} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['distinct_headings']:<10} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = heading_tag_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No heading tag data found.")
            else:
                print(f"{'heading':<20} {'tags':<8} {'chunks':<8} {'assignments':<14} {'avg_score':<12} {'ratio'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<20} {r['distinct_tags']:<8} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:<12.4f} {r['tag_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
