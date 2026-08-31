#!/usr/bin/env python3
"""Heading tag correlation: how heading paths relate to chunk tags.

tag_landscape.py profiles tags corpus-wide.
heading_depth_analysis.py profiles heading path depths.
No tool measures which heading paths concentrate which tags,
whether deeper headings attract different tag vocabularies, or
how tag diversity varies across heading structures.

Usage:
    python tools/corpus/heading_tag_correlation.py by-heading [--db PATH] [--json]
    python tools/corpus/heading_tag_correlation.py by-depth [--db PATH] [--json]
    python tools/corpus/heading_tag_correlation.py diversity [--db PATH] [--json]
    python tools/corpus/heading_tag_correlation.py summary [--db PATH] [--json]
    python tools/corpus/heading_tag_correlation.py selftest
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
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS chunks_at_heading,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        ORDER BY tag_assignments DESC, c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "chunks_at_heading": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def tags_by_heading_depth(conn) -> list[dict]:
    """Tag statistics grouped by heading depth (separator count + 1)."""
    rows = conn.execute(
        """
        SELECT depth, COUNT(DISTINCT tag) AS distinct_tags,
               COUNT(*) AS tag_assignments,
               COUNT(DISTINCT chunk_id) AS tagged_chunks,
               ROUND(AVG(score), 4) AS avg_score
        FROM (
            SELECT ct.tag, ct.score, ct.chunk_id,
                   LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1 AS depth
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            WHERE c.heading_path IS NOT NULL
        )
        GROUP BY depth
        ORDER BY depth
        """
    ).fetchall()
    return [
        {
            "depth": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def heading_tag_diversity(conn) -> list[dict]:
    """Per-heading tag diversity: ratio of distinct tags to total assignments."""
    rows = conn.execute(
        """
        SELECT c.heading_path,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS chunk_count
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.heading_path
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), c.heading_path
        """
    ).fetchall()
    return [
        {
            "heading_path": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "chunk_count": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def heading_tag_summary(conn) -> dict:
    """Aggregate heading-tag correlation statistics."""
    total_tagged = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]

    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    headings_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT c.heading_path)
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_headings = conn.execute(
        "SELECT COUNT(DISTINCT heading_path) FROM chunks WHERE heading_path IS NOT NULL"
    ).fetchone()[0]

    max_depth_row = conn.execute(
        """
        SELECT MAX(LENGTH(c.heading_path) - LENGTH(REPLACE(c.heading_path, '/', '')) + 1)
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        """
    ).fetchone()
    max_tagged_depth = max_depth_row[0] if max_depth_row[0] is not None else 0

    avg_tags_per_heading = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT c.heading_path, COUNT(ct.tag) AS tag_count
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.heading_path
        )
        """
    ).fetchone()[0]

    return {
        "total_tagged_chunks": total_tagged,
        "total_distinct_tags": total_tags,
        "headings_with_tags": headings_with_tags,
        "total_headings": total_headings,
        "heading_tag_coverage": round(headings_with_tags / max(total_headings, 1), 4),
        "max_tagged_depth": max_tagged_depth,
        "avg_tags_per_heading": avg_tags_per_heading or 0.0,
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1: heading "intro", c2: heading "intro/details", c3: heading "methods", c4: heading "methods" (no tags)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro/details", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "abc", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "abc", 4000, 0, "accepted", None, t1))

        # Tags: c1 has law+tech, c2 has law, c3 has tech+science
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "law", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "science", 0.6, t1))
        conn.commit()

        # 1. by-heading: "intro" has 2 distinct tags (law, tech)
        bh = tags_by_heading(conn)
        intro = [r for r in bh if r["heading_path"] == "intro"][0]
        assert intro["distinct_tags"] == 2
        ok += 1

        # 2. "intro" has 2 tag assignments
        assert intro["tag_assignments"] == 2
        ok += 1

        # 3. "intro/details" has 1 tag (law)
        details = [r for r in bh if r["heading_path"] == "intro/details"][0]
        assert details["distinct_tags"] == 1
        ok += 1

        # 4. by-depth: depth 1 has 3 headings worth of tags (intro=2, methods=2)
        bd = tags_by_heading_depth(conn)
        d1 = [r for r in bd if r["depth"] == 1][0]
        assert d1["tag_assignments"] == 4
        ok += 1

        # 5. depth 2 has 1 tag assignment (intro/details -> law)
        d2 = [r for r in bd if r["depth"] == 2][0]
        assert d2["tag_assignments"] == 1
        ok += 1

        # 6. diversity: "intro" has ratio 2/2 = 1.0
        div = heading_tag_diversity(conn)
        intro_div = [r for r in div if r["heading_path"] == "intro"][0]
        assert intro_div["diversity_ratio"] == 1.0
        ok += 1

        # 7. "methods" has 2 distinct tags, 2 assignments, ratio 1.0
        meth_div = [r for r in div if r["heading_path"] == "methods"][0]
        assert meth_div["diversity_ratio"] == 1.0
        ok += 1

        # 8. "intro/details" not in diversity (only 1 assignment, below threshold)
        details_div = [r for r in div if r["heading_path"] == "intro/details"]
        assert len(details_div) == 0
        ok += 1

        # 9. summary: total_tagged_chunks = 3 (c1, c2, c3)
        s = heading_tag_summary(conn)
        assert s["total_tagged_chunks"] == 3
        ok += 1

        # 10. headings_with_tags = 3 (intro, intro/details, methods)
        assert s["headings_with_tags"] == 3
        ok += 1

        # 11. total_headings = 3 (intro, intro/details, methods -- c3 and c4 share "methods")
        assert s["total_headings"] == 3
        ok += 1

        # 12. max_tagged_depth = 2 (intro/details)
        assert s["max_tagged_depth"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["heading_tag_coverage"] == s["heading_tag_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = heading_tag_summary(conn)
        assert s["total_tagged_chunks"] == 0
        assert s["headings_with_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Heading tag correlation analysis")
    ap.add_argument("command", choices=["by-heading", "by-depth", "diversity", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS heading_tag_correlation selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-heading":
        rows = tags_by_heading(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tagged headings found.")
            else:
                print(f"{'heading_path':<30} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['chunks_at_heading']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-depth":
        rows = tags_by_heading_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tagged headings found.")
            else:
                print(f"{'depth':<8} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['depth']:<8} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "diversity":
        rows = heading_tag_diversity(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No headings with multiple tags found.")
            else:
                print(f"{'heading_path':<30} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    h = r["heading_path"] or "(none)"
                    print(f"{h:<30} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['chunk_count']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = heading_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
