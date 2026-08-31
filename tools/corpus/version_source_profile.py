#!/usr/bin/env python3
"""Version source profile: revision activity per source.

version_edge_impact.py joins chunk_versions with claim_edges.
version_citation_drift.py joins chunk_versions with citations.
version_tag_stability.py joins chunk_versions with chunk_tags.
No tool joins chunk_versions with sources to show which sources
have the most revision activity, or which source kinds accumulate
the most churn.

Usage:
    python tools/corpus/version_source_profile.py by-source [--db PATH] [--json]
    python tools/corpus/version_source_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/version_source_profile.py top-churners [--db PATH] [--json]
    python tools/corpus/version_source_profile.py summary [--db PATH] [--json]
    python tools/corpus/version_source_profile.py selftest
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
    "  norm_sha256 TEXT NOT NULL,"
    "  word_count INTEGER NOT NULL,"
    "  snapshot_utc TEXT NOT NULL,"
    "  UNIQUE(chunk_id, version_num))"
)


def revision_by_source(conn) -> list[dict]:
    """Revision density per source."""
    conn.execute(_CV_DDL)
    rows = conn.execute(
        """
        SELECT s.source_id, s.title, s.kind,
               COUNT(DISTINCT c.chunk_id) AS total_chunks,
               COUNT(DISTINCT cv.chunk_id) AS revised_chunks,
               COUNT(cv.version_id) AS total_revisions,
               ROUND(
                   COUNT(cv.version_id) * 1.0
                   / MAX(COUNT(DISTINCT c.chunk_id), 1),
                   4
               ) AS revisions_per_chunk,
               MAX(cv.version_num) AS max_depth
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        LEFT JOIN chunk_versions cv ON cv.chunk_id = c.chunk_id
        GROUP BY s.source_id
        ORDER BY total_revisions DESC, s.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "kind": r[2],
            "total_chunks": r[3],
            "revised_chunks": r[4],
            "total_revisions": r[5],
            "revisions_per_chunk": r[6],
            "max_depth": r[7],
        }
        for r in rows
    ]


def revision_by_kind(conn) -> list[dict]:
    """Revision activity aggregated by source kind."""
    conn.execute(_CV_DDL)
    rows = conn.execute(
        """
        SELECT s.kind,
               COUNT(DISTINCT s.source_id) AS source_count,
               COUNT(DISTINCT c.chunk_id) AS total_chunks,
               COUNT(DISTINCT cv.chunk_id) AS revised_chunks,
               COUNT(cv.version_id) AS total_revisions,
               ROUND(
                   COUNT(cv.version_id) * 1.0
                   / MAX(COUNT(DISTINCT c.chunk_id), 1),
                   4
               ) AS revisions_per_chunk
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        LEFT JOIN chunk_versions cv ON cv.chunk_id = c.chunk_id
        GROUP BY s.kind
        ORDER BY total_revisions DESC, s.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "source_count": r[1],
            "total_chunks": r[2],
            "revised_chunks": r[3],
            "total_revisions": r[4],
            "revisions_per_chunk": r[5],
        }
        for r in rows
    ]


def top_churners(conn, limit: int = 20) -> list[dict]:
    """Sources with highest revision churn (revisions per chunk, minimum 2 chunks)."""
    conn.execute(_CV_DDL)
    rows = conn.execute(
        """
        SELECT s.source_id, s.title, s.kind,
               COUNT(DISTINCT c.chunk_id) AS total_chunks,
               COUNT(cv.version_id) AS total_revisions,
               ROUND(
                   COUNT(cv.version_id) * 1.0
                   / MAX(COUNT(DISTINCT c.chunk_id), 1),
                   4
               ) AS revisions_per_chunk
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_versions cv ON cv.chunk_id = c.chunk_id
        GROUP BY s.source_id
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY revisions_per_chunk DESC, s.source_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "kind": r[2],
            "total_chunks": r[3],
            "total_revisions": r[4],
            "revisions_per_chunk": r[5],
        }
        for r in rows
    ]


def version_source_summary(conn) -> dict:
    """Aggregate version-source statistics."""
    conn.execute(_CV_DDL)
    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]
    sources_with_revisions = conn.execute(
        """
        SELECT COUNT(DISTINCT s.source_id)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_versions cv ON cv.chunk_id = c.chunk_id
        """
    ).fetchone()[0]
    sources_without = total_sources - sources_with_revisions
    revision_coverage = round(sources_with_revisions / max(total_sources, 1), 4)

    total_revisions = conn.execute(
        "SELECT COUNT(*) FROM chunk_versions"
    ).fetchone()[0]
    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]
    revised_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]

    by_source = revision_by_source(conn)
    most_revised = None
    if by_source and by_source[0]["total_revisions"] > 0:
        most_revised = by_source[0]["source_id"]

    return {
        "total_sources": total_sources,
        "sources_with_revisions": sources_with_revisions,
        "sources_without_revisions": sources_without,
        "revision_coverage_rate": revision_coverage,
        "total_revisions": total_revisions,
        "total_chunks": total_chunks,
        "revised_chunks": revised_chunks,
        "most_revised_source": most_revised,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CV_DDL)

        t1 = "2026-01-01T00:00:00Z"
        t2 = "2026-02-01T00:00:00Z"
        t3 = "2026-03-01T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "Source One", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "Source Two", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "Source Three", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 50, None),
        )

        # s1: chunks c1,c2,c3; s2: chunks c4,c5; s3: chunk c6
        for i, (cid, sid) in enumerate([
            ("c1", "s1"), ("c2", "s1"), ("c3", "s1"),
            ("c4", "s2"), ("c5", "s2"),
            ("c6", "s3"),
        ], 1):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, sid, i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # versions: c1 has 3 versions, c2 has 1 version, c4 has 2 versions
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v1", "c1", 1, "sha1", 10, t1),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v2", "c1", 2, "sha2", 12, t2),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v3", "c1", 3, "sha3", 14, t3),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v4", "c2", 1, "sha4", 10, t1),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v5", "c4", 1, "sha5", 20, t1),
        )
        conn.execute(
            "INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)",
            ("v6", "c4", 2, "sha6", 22, t2),
        )
        conn.commit()

        # 1. s1 has 4 revisions (3 on c1, 1 on c2)
        bs = revision_by_source(conn)
        s1_row = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1_row["total_revisions"] == 4, f"s1 revisions {s1_row['total_revisions']}"
        ok += 1

        # 2. s1 has 2 revised chunks (c1, c2)
        assert s1_row["revised_chunks"] == 2
        ok += 1

        # 3. s1 has 3 total chunks
        assert s1_row["total_chunks"] == 3
        ok += 1

        # 4. s2 has 2 revisions (on c4)
        s2_row = [r for r in bs if r["source_id"] == "s2"][0]
        assert s2_row["total_revisions"] == 2
        ok += 1

        # 5. s3 has 0 revisions
        s3_row = [r for r in bs if r["source_id"] == "s3"][0]
        assert s3_row["total_revisions"] == 0
        ok += 1

        # 6. s1 max_depth is 3
        assert s1_row["max_depth"] == 3
        ok += 1

        # 7. by-kind: local_md has 6 revisions
        bk = revision_by_kind(conn)
        lm_row = [r for r in bk if r["kind"] == "local_md"][0]
        assert lm_row["total_revisions"] == 6
        ok += 1

        # 8. by-kind: repo has 0 revisions
        repo_row = [r for r in bk if r["kind"] == "repo"][0]
        assert repo_row["total_revisions"] == 0
        ok += 1

        # 9. top_churners: only s1 qualifies (2 revised chunks >= 2; s2 has only 1 revised chunk)
        tc = top_churners(conn)
        assert len(tc) == 1
        ok += 1

        # 10. top_churners: s1 has 4/2 revisions_per_chunk (2 revised chunks via INNER JOIN)
        tc_s1 = tc[0]
        assert tc_s1["source_id"] == "s1"
        assert tc_s1["revisions_per_chunk"] == round(4 / 2, 4)
        ok += 1

        # 11. summary: sources_with_revisions is 2 (s1, s2)
        s = version_source_summary(conn)
        assert s["sources_with_revisions"] == 2
        ok += 1

        # 12. summary: sources_without is 1 (s3)
        assert s["sources_without_revisions"] == 1
        ok += 1

        # 13. summary: most_revised_source is s1
        assert s["most_revised_source"] == "s1"
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = version_source_summary(conn)
        assert s["total_sources"] == 0
        assert s["sources_with_revisions"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Version source profile analysis")
    ap.add_argument("command", choices=["by-source", "by-kind", "top-churners", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS version_source_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-source":
        rows = revision_by_source(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No sources found.")
            else:
                print(f"{'source_id':<16} {'title':<20} {'kind':<12} {'chunks':<8} {'revised':<8} {'revisions':<10} {'rev/chunk':<10} {'max_depth'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['title']:<20} {r['kind']:<12} {r['total_chunks']:<8} {r['revised_chunks']:<8} {r['total_revisions']:<10} {r['revisions_per_chunk']:<10.4f} {r['max_depth']}")
    elif args.command == "by-kind":
        rows = revision_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'kind':<16} {'sources':<10} {'chunks':<8} {'revised':<8} {'revisions':<10} {'rev/chunk'}")
            for r in rows:
                print(f"{r['kind']:<16} {r['source_count']:<10} {r['total_chunks']:<8} {r['revised_chunks']:<8} {r['total_revisions']:<10} {r['revisions_per_chunk']:.4f}")
    elif args.command == "top-churners":
        rows = top_churners(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No sources with 2+ chunks and revisions.")
            else:
                print(f"{'source_id':<16} {'title':<20} {'kind':<12} {'chunks':<8} {'revisions':<10} {'rev/chunk'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['title']:<20} {r['kind']:<12} {r['total_chunks']:<8} {r['total_revisions']:<10} {r['revisions_per_chunk']:.4f}")
    elif args.command == "summary":
        s = version_source_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
