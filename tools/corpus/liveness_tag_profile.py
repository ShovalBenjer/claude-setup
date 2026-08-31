#!/usr/bin/env python3
"""Liveness tag profile: how source liveness relates to chunk tag patterns.

publisher_tag_profile.py profiles tags by publisher.
liveness_citation_profile.py correlates liveness with citations.
liveness_edge_profile.py correlates liveness with claim edges.
No tool joins sources.liveness with chunk_tags to measure whether
live sources carry different tag vocabularies than stale or archived
ones, or how tag scores vary across liveness states.

Usage:
    python tools/corpus/liveness_tag_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/liveness_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/liveness_tag_profile.py concentration [--db PATH] [--json]
    python tools/corpus/liveness_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/liveness_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_liveness(conn) -> list[dict]:
    """Tag distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS tag_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.liveness
        ORDER BY tag_assignments DESC, s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "distinct_tags": r[1],
            "tag_assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def liveness_by_tag(conn) -> list[dict]:
    """Liveness distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT s.liveness) AS distinct_states,
               COUNT(ct.tag) AS assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunk_tags ct
        JOIN chunks c ON c.chunk_id = ct.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY ct.tag
        ORDER BY distinct_states DESC, ct.tag
        """
    ).fetchall()
    return [
        {
            "tag": r[0],
            "distinct_states": r[1],
            "assignments": r[2],
            "tagged_chunks": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def liveness_tag_concentration(conn) -> list[dict]:
    """Per-liveness tag concentration: ratio of distinct tags to assignments."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(ct.tag) AS total_assignments,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY s.liveness
        HAVING COUNT(ct.tag) >= 2
        ORDER BY CAST(COUNT(DISTINCT ct.tag) AS REAL) / COUNT(ct.tag), s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "distinct_tags": r[1],
            "total_assignments": r[2],
            "tagged_chunks": r[3],
            "diversity_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def liveness_tag_summary(conn) -> dict:
    """Aggregate liveness-tag statistics."""
    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    states_with_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT s.liveness)
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

    avg_tags_per_state = conn.execute(
        """
        SELECT ROUND(AVG(tag_count), 4)
        FROM (
            SELECT s.liveness, COUNT(DISTINCT ct.tag) AS tag_count
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY s.liveness
        )
        """
    ).fetchone()[0]

    single_state_tags = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT ct.tag
            FROM chunk_tags ct
            JOIN chunks c ON c.chunk_id = ct.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY ct.tag
            HAVING COUNT(DISTINCT s.liveness) = 1
        )
        """
    ).fetchone()[0]

    return {
        "total_liveness_states": total_states,
        "states_with_tags": states_with_tags,
        "liveness_tag_coverage": round(states_with_tags / max(total_states, 1), 4),
        "total_distinct_tags": total_tags,
        "total_tag_assignments": total_assignments,
        "avg_tags_per_state": avg_tags_per_state or 0.0,
        "single_state_tags": single_state_tags,
        "single_state_tag_rate": round(single_state_tags / max(total_tags, 1), 4),
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "ghi", 150, None),
        )

        # c1,c2 from s1 (live); c3,c4 from s2 (stale); c5 from s3 (archived, no tags)
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

        # Tags: live gets law+tech+science (3), stale gets tech+bio (2), archived gets none
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "science", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "tech", 0.85, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "bio", 0.6, t1))
        conn.commit()

        # 1. by-liveness: live has 3 distinct tags
        bl = tags_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["distinct_tags"] == 3
        ok += 1

        # 2. live has 3 tag assignments
        assert live["tag_assignments"] == 3
        ok += 1

        # 3. stale has 2 distinct tags
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["distinct_tags"] == 2
        ok += 1

        # 4. archived not in results (no tags)
        archived = [r for r in bl if r["liveness"] == "archived"]
        assert len(archived) == 0
        ok += 1

        # 5. by-tag: "tech" spans 2 liveness states (live, stale)
        bt = liveness_by_tag(conn)
        tech = [r for r in bt if r["tag"] == "tech"][0]
        assert tech["distinct_states"] == 2
        ok += 1

        # 6. "bio" spans 1 liveness state (stale)
        bio = [r for r in bt if r["tag"] == "bio"][0]
        assert bio["distinct_states"] == 1
        ok += 1

        # 7. "law" spans 1 liveness state (live)
        law = [r for r in bt if r["tag"] == "law"][0]
        assert law["distinct_states"] == 1
        ok += 1

        # 8. concentration: live has diversity 3/3=1.0
        conc = liveness_tag_concentration(conn)
        live_conc = [r for r in conc if r["liveness"] == "live"][0]
        assert live_conc["diversity_ratio"] == 1.0
        ok += 1

        # 9. stale has diversity 2/2=1.0
        stale_conc = [r for r in conc if r["liveness"] == "stale"][0]
        assert stale_conc["diversity_ratio"] == 1.0
        ok += 1

        # 10. archived not in concentration (no tags)
        archived_conc = [r for r in conc if r["liveness"] == "archived"]
        assert len(archived_conc) == 0
        ok += 1

        # 11. summary: states_with_tags = 2 (live, stale)
        s = liveness_tag_summary(conn)
        assert s["states_with_tags"] == 2
        ok += 1

        # 12. total_distinct_tags = 4 (law, tech, science, bio)
        assert s["total_distinct_tags"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["liveness_tag_coverage"] == s["liveness_tag_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = liveness_tag_summary(conn)
        assert s["states_with_tags"] == 0
        assert s["total_distinct_tags"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Liveness tag profile analysis")
    ap.add_argument("command", choices=["by-liveness", "by-tag", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS liveness_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-liveness":
        rows = tags_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness tag data found.")
            else:
                print(f"{'liveness':<14} {'tags':<6} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_tags']:<6} {r['tag_assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = liveness_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag liveness data found.")
            else:
                print(f"{'tag':<20} {'states':<8} {'assignments':<12} {'chunks':<8} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<20} {r['distinct_states']:<8} {r['assignments']:<12} {r['tagged_chunks']:<8} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = liveness_tag_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness states with multiple tags found.")
            else:
                print(f"{'liveness':<14} {'distinct':<10} {'total':<8} {'chunks':<8} {'diversity'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_tags']:<10} {r['total_assignments']:<8} {r['tagged_chunks']:<8} {r['diversity_ratio']:.4f}")
    elif args.command == "summary":
        s = liveness_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
