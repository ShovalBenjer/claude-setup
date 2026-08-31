#!/usr/bin/env python3
"""Version tag stability: tags whose parent chunk changed after tagging.

version_citation_drift.py checks citations against chunk_versions.
tag_citation_yield.py correlates tags with citation counts.
No tool joins chunk_versions with chunk_tags to detect tags that may be
stale because their parent chunk's content was revised after the tag
was assigned.

Usage:
    python tools/corpus/version_tag_stability.py unstable [--db PATH] [--json]
    python tools/corpus/version_tag_stability.py by-tag [--db PATH] [--json]
    python tools/corpus/version_tag_stability.py by-depth [--db PATH] [--json]
    python tools/corpus/version_tag_stability.py summary [--db PATH] [--json]
    python tools/corpus/version_tag_stability.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CV_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_versions ("
    "  version_id TEXT PRIMARY KEY,"
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  version_num INTEGER NOT NULL,"
    "  norm_sha256 TEXT,"
    "  word_count INTEGER,"
    "  snapshot_utc TEXT,"
    "  UNIQUE(chunk_id, version_num))"
)
_CT_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_tags ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  tag TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  tagged_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, tag))"
)


def unstable_tags(conn) -> list[dict]:
    """Tags whose parent chunk was revised after the tag was assigned."""
    conn.execute(_CV_DDL)
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.chunk_id, ct.tag, ct.score, ct.tagged_utc,
               MAX(cv.snapshot_utc) AS latest_revision,
               COUNT(cv.version_id) AS revisions_after
        FROM chunk_tags ct
        JOIN chunk_versions cv
          ON cv.chunk_id = ct.chunk_id
         AND cv.snapshot_utc > ct.tagged_utc
        GROUP BY ct.chunk_id, ct.tag
        ORDER BY revisions_after DESC, ct.tag, ct.chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "tag": r[1],
            "score": r[2],
            "tagged_utc": r[3],
            "latest_revision": r[4],
            "revisions_after": r[5],
        }
        for r in rows
    ]


def stability_by_tag(conn) -> list[dict]:
    """Stability counts per tag value."""
    conn.execute(_CV_DDL)
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(*) AS total_assignments,
               COUNT(CASE WHEN cv.version_id IS NOT NULL THEN 1 END) AS unstable,
               ROUND(
                   COUNT(CASE WHEN cv.version_id IS NOT NULL THEN 1 END) * 1.0
                   / MAX(COUNT(*), 1),
                   4
               ) AS instability_rate
        FROM chunk_tags ct
        LEFT JOIN chunk_versions cv
          ON cv.chunk_id = ct.chunk_id
         AND cv.snapshot_utc > ct.tagged_utc
        GROUP BY ct.tag
        ORDER BY unstable DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "total_assignments": r[1],
            "unstable": r[2],
            "instability_rate": r[3],
        }
        for r in rows
    ]


def stability_by_depth(conn) -> list[dict]:
    """Unstable tags bucketed by revision depth of parent chunk."""
    conn.execute(_CV_DDL)
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT rev_count, COUNT(*) AS unstable_tags
        FROM (
            SELECT ct.chunk_id, ct.tag,
                   COUNT(cv.version_id) AS rev_count
            FROM chunk_tags ct
            JOIN chunk_versions cv
              ON cv.chunk_id = ct.chunk_id
             AND cv.snapshot_utc > ct.tagged_utc
            GROUP BY ct.chunk_id, ct.tag
        )
        GROUP BY rev_count
        ORDER BY rev_count
        """
    ).fetchall()
    return [
        {"revision_depth": r[0], "unstable_tags": r[1]}
        for r in rows
    ]


def stability_summary(conn) -> dict:
    """Aggregate tag stability statistics."""
    conn.execute(_CV_DDL)
    conn.execute(_CT_DDL)
    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_tags"
    ).fetchone()[0]
    unstable = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.chunk_id, ct.tag
            FROM chunk_tags ct
            JOIN chunk_versions cv
              ON cv.chunk_id = ct.chunk_id
             AND cv.snapshot_utc > ct.tagged_utc
            GROUP BY ct.chunk_id, ct.tag
        )
        """
    ).fetchone()[0]
    stable = total_assignments - unstable
    instability_rate = round(unstable / max(total_assignments, 1), 4)

    distinct_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]
    tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]
    revised_tagged_chunks = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.chunk_id)
        FROM chunk_tags ct
        JOIN chunk_versions cv
          ON cv.chunk_id = ct.chunk_id
         AND cv.snapshot_utc > ct.tagged_utc
        """
    ).fetchone()[0]

    by_tag = stability_by_tag(conn)
    most_unstable = by_tag[0]["tag"] if by_tag and by_tag[0]["unstable"] > 0 else None

    return {
        "total_assignments": total_assignments,
        "stable": stable,
        "unstable": unstable,
        "instability_rate": instability_rate,
        "distinct_tags": distinct_tags,
        "tagged_chunks": tagged_chunks,
        "revised_tagged_chunks": revised_tagged_chunks,
        "most_unstable_tag": most_unstable,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CV_DDL)
        conn.execute(_CT_DDL)

        t1 = "2026-01-01T00:00:00Z"
        t2 = "2026-02-01T00:00:00Z"
        t3 = "2026-03-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # c1 tagged at t1 with "python", chunk revised at t2 -> unstable
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "python", 0.9, t1),
        )
        # c1 tagged at t1 with "ml", chunk revised at t2 -> unstable
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c1", "ml", 0.8, t1),
        )
        # c2 tagged at t1 with "python", chunk revised at t3 -> unstable
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c2", "python", 0.7, t1),
        )
        # c3 tagged at t3, chunk revised at t2 -> stable (revision before tagging)
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c3", "python", 0.6, t3),
        )
        # c4 tagged at t1, no revision -> stable
        conn.execute(
            "INSERT INTO chunk_tags VALUES (?,?,?,?)",
            ("c4", "ml", 0.5, t1),
        )

        # chunk_versions: c1 revised at t2, c2 revised at t3, c3 revised at t2
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v1", "c1", 2, "def", 12, t2),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v2", "c2", 2, "ghi", 11, t3),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v3", "c3", 2, "jkl", 9, t2),
        )
        conn.commit()

        # 1. unstable_tags returns correct count (c1/python, c1/ml, c2/python)
        u = unstable_tags(conn)
        assert len(u) == 3, f"expected 3 unstable, got {len(u)}"
        ok += 1

        # 2. c1/python is unstable
        pairs = {(r["chunk_id"], r["tag"]) for r in u}
        assert ("c1", "python") in pairs
        ok += 1

        # 3. c1/ml is unstable
        assert ("c1", "ml") in pairs
        ok += 1

        # 4. c2/python is unstable
        assert ("c2", "python") in pairs
        ok += 1

        # 5. c3/python is NOT unstable (revision before tagging)
        assert ("c3", "python") not in pairs
        ok += 1

        # 6. c4/ml is NOT unstable (no revision)
        assert ("c4", "ml") not in pairs
        ok += 1

        # 7. stability_by_tag returns correct tags
        bt = stability_by_tag(conn)
        tags = {r["tag"] for r in bt}
        assert "python" in tags and "ml" in tags
        ok += 1

        # 8. python has 2 unstable out of 3 total
        py_row = [r for r in bt if r["tag"] == "python"][0]
        assert py_row["unstable"] == 2, f"python unstable {py_row['unstable']}"
        assert py_row["total_assignments"] == 3
        ok += 1

        # 9. ml has 1 unstable out of 2 total
        ml_row = [r for r in bt if r["tag"] == "ml"][0]
        assert ml_row["unstable"] == 1, f"ml unstable {ml_row['unstable']}"
        assert ml_row["total_assignments"] == 2
        ok += 1

        # 10. stability_by_depth returns buckets
        bd = stability_by_depth(conn)
        assert len(bd) >= 1
        ok += 1

        # 11. summary totals
        s = stability_summary(conn)
        assert s["total_assignments"] == 5, f"total {s['total_assignments']}"
        assert s["unstable"] == 3, f"unstable {s['unstable']}"
        assert s["stable"] == 2, f"stable {s['stable']}"
        ok += 1

        # 12. summary distinct counts
        assert s["distinct_tags"] == 2
        assert s["tagged_chunks"] == 4
        ok += 1

        # 13. JSON serialisation round-trips
        j = json.loads(json.dumps(s))
        assert j["instability_rate"] == s["instability_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = stability_summary(conn)
        assert s["total_assignments"] == 0
        assert s["unstable"] == 0
        assert s["instability_rate"] == 0.0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Version tag stability analysis")
    ap.add_argument("command", choices=["unstable", "by-tag", "by-depth", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS version_tag_stability selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "unstable":
        rows = unstable_tags(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No unstable tags found.")
            else:
                print(f"{'chunk_id':<10} {'tag':<16} {'score':<8} {'revisions':<10} {'latest_revision'}")
                for r in rows:
                    print(f"{r['chunk_id']:<10} {r['tag']:<16} {r['score']:<8.2f} {r['revisions_after']:<10} {r['latest_revision']}")
    elif args.command == "by-tag":
        rows = stability_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'total':<10} {'unstable':<10} {'instability_rate'}")
            for r in rows:
                print(f"{r['tag']:<16} {r['total_assignments']:<10} {r['unstable']:<10} {r['instability_rate']:.4f}")
    elif args.command == "by-depth":
        rows = stability_by_depth(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'rev_depth':<12} {'unstable_tags'}")
            for r in rows:
                print(f"{r['revision_depth']:<12} {r['unstable_tags']}")
    elif args.command == "summary":
        s = stability_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
