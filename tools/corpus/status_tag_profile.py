#!/usr/bin/env python3
"""Status tag profile: how chunk status relates to chunk tag patterns.

status_citation_profile.py profiles statuses by citation patterns.
status_edge_profile.py profiles statuses by claim edge patterns.
No tool joins chunks.status with chunk_tags to measure whether
accepted chunks carry different tag vocabularies than quarantined
or rejected ones, or how tag scores vary across chunk statuses.

Usage:
    python tools/corpus/status_tag_profile.py by-status [--db PATH] [--json]
    python tools/corpus/status_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/status_tag_profile.py concentration [--db PATH] [--json]
    python tools/corpus/status_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/status_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_status(conn) -> list[dict]:
    """Tag distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.status
        ORDER BY tag_assignments DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def status_by_tag(conn) -> list[dict]:
    """Status distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT c.status) AS distinct_statuses,
               COUNT(ct.tag) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        GROUP BY ct.tag
        ORDER BY distinct_statuses DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_statuses": r[1],
            "assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def status_tag_concentration(conn) -> list[dict]:
    """Per-status tag concentration: ratio of distinct tags to assignments."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.status
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "tagged_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def status_tag_summary(conn) -> dict:
    """Aggregate status-tag statistics."""
    total_statuses = conn.execute(
        "SELECT COUNT(DISTINCT status) FROM chunks"
    ).fetchone()[0]

    statuses_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT c.status)
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    total_tags = conn.execute(
        "SELECT COUNT(DISTINCT tag) FROM chunk_tags"
    ).fetchone()[0]

    total_assignments = conn.execute(
        "SELECT COUNT(*) FROM chunk_tags"
    ).fetchone()[0]

    avg_tags_per_status = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT c.status, COUNT(DISTINCT ct.tag) AS tag_count
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.status
        )
        """
    ).fetchone()[0]

    single_status_tags = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT c.status) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_statuses": total_statuses,
        "statuses_with_tags": statuses_with_tags,
        "status_tag_coverage": round(statuses_with_tags / max(total_statuses, 1), 4),
        "total_distinct_tags": total_tags,
        "total_tag_assignments": total_assignments,
        "avg_tags_per_status": avg_tags_per_status or 0.0,
        "single_status_tags": single_status_tags,
        "single_status_tag_rate": round(single_status_tags / max(total_tags, 1), 4),
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

        # c1: accepted, c2: accepted, c3: quarantined, c4: rejected (no tags)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 25, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "discussion", "claim", None, "t", "t", 35, "jkl", 4000, 0, "rejected", "duplicate", t1))

        # Tags: accepted gets law+tech+science (3), quarantined gets tech+bio (2), rejected gets none
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "science", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "bio", 0.6, t1))
        conn.commit()

        # 1. by-status: accepted has 3 distinct tags
        bs = tags_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["distinct_tags"] == 3
        ok += 1

        # 2. accepted has 3 tag assignments
        assert accepted["tag_assignments"] == 3
        ok += 1

        # 3. quarantined has 2 distinct tags
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["distinct_tags"] == 2
        ok += 1

        # 4. rejected not in results (no tags)
        rejected = [r for r in bs if r["status"] == "rejected"]
        assert len(rejected) == 0
        ok += 1

        # 5. by-tag: "tech" spans 2 statuses (accepted, quarantined)
        bt = status_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_statuses"] == 2
        ok += 1

        # 6. "bio" spans 1 status (quarantined)
        bio = [r for r in bt if r["tag"] == "bio"][0]
        assert bio["distinct_statuses"] == 1
        ok += 1

        # 7. "law" spans 1 status (accepted)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_statuses"] == 1
        ok += 1

        # 8. concentration: accepted has diversity 3/3=1.0
        conc = status_tag_concentration(conn)
        acc_conc = [r for r in conc if r["status"] == "accepted"][0]
        assert acc_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. quarantined has diversity 2/2=1.0
        q_conc = [r for r in conc if r["status"] == "quarantined"][0]
        assert q_conc["diversity_ratio"] == 1.0
        ok += 1

        # 10. rejected not in concentration (no tags)
        rej_conc = [r for r in conc if r["status"] == "rejected"]
        assert len(rej_conc) == 0
        ok += 1

        # 11. summary: statuses_with_tags = 2 (accepted, quarantined)
        s = status_tag_summary(conn)
        assert s["statuses_with_tags"] == 2
        ok += 1

        # 12. total_distinct_tags = 4 (law, tech, science, bio)
        assert s["total_distinct_tags"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["status_tag_coverage"] == s["status_tag_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = status_tag_summary(conn)
        assert s["statuses_with_tags"] == 0
        assert s["total_distinct_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Status tag profile analysis")
    ap.add_argument("command", choices=["by-status", "by-tag", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS status_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-status":
        rows = tags_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status tag data found.")
            else:
                print(f"{'status':<14} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = status_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag status data found.")
            else:
                print(f"{'tag':<20} {'statuses':<10} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_statuses']:<10} {r['assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = status_tag_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No statuses with multiple tags found.")
            else:
                print(f"{'status':<14} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['tagged_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = status_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
