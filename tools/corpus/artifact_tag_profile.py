#!/usr/bin/env python3
"""Artifact tag profile: which tags co-occur with which artifact types.

artifact_domain_distribution.py maps artifacts to domains.
tag_citation_correlation.py correlates tags with citations.
No tool joins artifacts with chunk_tags to show which topic tags
co-occur with which artifact types, or which tags predict the
presence of actionable artifacts.

Usage:
    python tools/corpus/artifact_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/artifact_tag_profile.py by-type [--db PATH] [--json]
    python tools/corpus/artifact_tag_profile.py cross [--db PATH] [--json]
    python tools/corpus/artifact_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/artifact_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CT_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_tags ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  tag TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  tagged_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, tag))"
)


def artifacts_by_tag(conn) -> list[dict]:
    """Artifact counts per tag."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks,
               COUNT(DISTINCT a.artifact_id) AS artifact_count,
               COUNT(DISTINCT CASE WHEN a.implemented = 1 THEN a.artifact_id END) AS implemented,
               ROUND(
                   COUNT(DISTINCT a.artifact_id) * 1.0
                   / MAX(COUNT(DISTINCT ct.chunk_id), 1),
                   4
               ) AS artifacts_per_chunk
        FROM chunk_tags ct
        LEFT JOIN artifacts a ON a.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY artifact_count DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "tagged_chunks": r[1],
            "artifact_count": r[2],
            "implemented": r[3],
            "artifacts_per_chunk": r[4],
        }
        for r in rows
    ]


def tags_by_artifact_type(conn) -> list[dict]:
    """Tag distribution per artifact type."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT a.artifact_type,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT a.artifact_id) AS artifact_count,
               COUNT(DISTINCT ct.chunk_id) AS tagged_chunks
        FROM artifacts a
        JOIN chunk_tags ct ON ct.chunk_id = a.chunk_id
        GROUP BY a.artifact_type
        ORDER BY artifact_count DESC, a.artifact_type
        """
    ).fetchall()
    return [
        {
            "artifact_type": r[0],
            "distinct_tags": r[1],
            "artifact_count": r[2],
            "tagged_chunks": r[3],
        }
        for r in rows
    ]


def tag_artifact_cross(conn) -> list[dict]:
    """Full tag x artifact_type cross-tabulation."""
    conn.execute(_CT_DDL)
    rows = conn.execute(
        """
        SELECT ct.tag, a.artifact_type,
               COUNT(DISTINCT a.artifact_id) AS count,
               COUNT(DISTINCT CASE WHEN a.implemented = 1 THEN a.artifact_id END) AS implemented
        FROM chunk_tags ct
        JOIN artifacts a ON a.chunk_id = ct.chunk_id
        GROUP BY ct.tag, a.artifact_type
        ORDER BY ct.tag, count DESC
        """
    ).fetchall()
    return [
        {"tag": r[0], "artifact_type": r[1], "count": r[2], "implemented": r[3]}
        for r in rows
    ]


def tag_artifact_summary(conn) -> dict:
    """Aggregate tag-artifact profile statistics."""
    conn.execute(_CT_DDL)
    distinct_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]
    tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]
    tagged_with_artifacts = conn.execute(
        """
        SELECT COUNT(DISTINCT ct.chunk_id)
        FROM chunk_tags ct
        JOIN artifacts a ON a.chunk_id = ct.chunk_id
        """
    ).fetchone()[0]
    tagged_without = tagged_chunks - tagged_with_artifacts
    artifact_coverage = round(tagged_with_artifacts / max(tagged_chunks, 1), 4)

    artifacts_on_tagged = conn.execute(
        """
        SELECT COUNT(DISTINCT a.artifact_id)
        FROM chunk_tags ct
        JOIN artifacts a ON a.chunk_id = ct.chunk_id
        """
    ).fetchone()[0]
    total_artifacts = conn.execute(
        "SELECT COUNT(*) FROM artifacts"
    ).fetchone()[0]
    tagged_artifact_share = round(artifacts_on_tagged / max(total_artifacts, 1), 4)

    by_tag = artifacts_by_tag(conn)
    richest = by_tag[0]["tag"] if by_tag and by_tag[0]["artifact_count"] > 0 else None

    return {
        "distinct_tags": distinct_tags,
        "tagged_chunks": tagged_chunks,
        "tagged_with_artifacts": tagged_with_artifacts,
        "tagged_without_artifacts": tagged_without,
        "artifact_coverage_rate": artifact_coverage,
        "artifacts_on_tagged": artifacts_on_tagged,
        "tagged_artifact_share": tagged_artifact_share,
        "richest_tag": richest,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CT_DDL)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # tags: c1 python+ml, c2 python, c3 ml, c4 web (no artifacts)
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "web", 0.5, t1))

        # artifacts: c1 library+api, c2 command, c5 library (untagged)
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a1", "c1", "library", "requests", "2.31", None, 1, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a2", "c1", "api", "GET /users", None, None, 0, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a3", "c2", "command", "pip install", None, None, 1, None),
        )
        conn.execute(
            "INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
            ("a4", "c5", "library", "numpy", "1.26", None, 1, None),
        )
        conn.commit()

        # 1. python has 3 artifacts (a1+a2 from c1, a3 from c2)
        bt = artifacts_by_tag(conn)
        py_row = [r for r in bt if r["tag"] == "python"][0]
        assert py_row["artifact_count"] == 3, f"python artifacts {py_row['artifact_count']}"
        ok += 1

        # 2. ml has 2 artifacts (a1+a2 from c1; c3 has no artifacts)
        ml_row = [r for r in bt if r["tag"] == "ml"][0]
        assert ml_row["artifact_count"] == 2, f"ml artifacts {ml_row['artifact_count']}"
        ok += 1

        # 3. web has 0 artifacts
        web_row = [r for r in bt if r["tag"] == "web"][0]
        assert web_row["artifact_count"] == 0
        ok += 1

        # 4. python implemented is 2 (a1+a3)
        assert py_row["implemented"] == 2
        ok += 1

        # 5. tags_by_artifact_type: library has tags
        ba = tags_by_artifact_type(conn)
        lib_row = [r for r in ba if r["artifact_type"] == "library"][0]
        assert lib_row["artifact_count"] == 1
        ok += 1

        # 6. command has tags
        cmd_row = [r for r in ba if r["artifact_type"] == "command"][0]
        assert cmd_row["artifact_count"] == 1
        ok += 1

        # 7. cross-tabulation has entries
        cr = tag_artifact_cross(conn)
        assert len(cr) >= 1
        ok += 1

        # 8. python/library in cross
        py_lib = [r for r in cr if r["tag"] == "python" and r["artifact_type"] == "library"]
        assert len(py_lib) == 1 and py_lib[0]["count"] == 1
        ok += 1

        # 9. summary: tagged_with_artifacts is 2 (c1, c2)
        s = tag_artifact_summary(conn)
        assert s["tagged_with_artifacts"] == 2
        ok += 1

        # 10. tagged_without is 2 (c3, c4)
        assert s["tagged_without_artifacts"] == 2
        ok += 1

        # 11. artifacts_on_tagged is 3 (a1,a2,a3; a4 is on untagged c5)
        assert s["artifacts_on_tagged"] == 3
        ok += 1

        # 12. tagged_artifact_share = 3/4
        assert s["tagged_artifact_share"] == round(3 / 4, 4)
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["artifact_coverage_rate"] == s["artifact_coverage_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = tag_artifact_summary(conn)
        assert s["distinct_tags"] == 0
        assert s["tagged_with_artifacts"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Artifact tag profile analysis")
    ap.add_argument("command", choices=["by-tag", "by-type", "cross", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS artifact_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-tag":
        rows = artifacts_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tagged chunks found.")
            else:
                print(f"{'tag':<16} {'chunks':<8} {'artifacts':<10} {'implemented':<12} {'art/chunk'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['tagged_chunks']:<8} {r['artifact_count']:<10} {r['implemented']:<12} {r['artifacts_per_chunk']:.4f}")
    elif args.command == "by-type":
        rows = tags_by_artifact_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'artifact_type':<16} {'tags':<8} {'artifacts':<10} {'tagged_chunks'}")
            for r in rows:
                print(f"{r['artifact_type']:<16} {r['distinct_tags']:<8} {r['artifact_count']:<10} {r['tagged_chunks']}")
    elif args.command == "cross":
        rows = tag_artifact_cross(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'tag':<16} {'artifact_type':<16} {'count':<8} {'implemented'}")
            for r in rows:
                print(f"{r['tag']:<16} {r['artifact_type']:<16} {r['count']:<8} {r['implemented']}")
    elif args.command == "summary":
        s = tag_artifact_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
