#!/usr/bin/env python3
"""Simhash tag profile: how simhash collision groups distribute across chunk tags.

simhash_license_profile.py profiles simhash groups by source license.
simhash_publisher_profile.py profiles simhash groups by source publisher.
No tool cross-tabulates chunks.simhash with chunk_tags.tag to measure
whether near-duplicate clusters share the same topic tags, or how tag
vocabulary distributes across simhash collision groups.

Usage:
    python tools/corpus/simhash_tag_profile.py by-simhash [--db PATH] [--json]
    python tools/corpus/simhash_tag_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/simhash_tag_profile.py concentration [--db PATH] [--json]
    python tools/corpus/simhash_tag_profile.py summary [--db PATH] [--json]
    python tools/corpus/simhash_tag_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def tags_by_simhash(conn) -> list[dict]:
    """Tag distribution per simhash collision group (groups with 2+ tagged chunks)."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               COUNT(ct.tag) AS tag_assignments,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.simhash
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY tagged_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_tags": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def simhash_groups_by_tag(conn) -> list[dict]:
    """Simhash group distribution per tag."""
    rows = conn.execute(
        """
        SELECT ct.tag,
               COUNT(DISTINCT c.simhash) AS distinct_simhashes,
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
            "distinct_simhashes": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
        }
        for r in rows
    ]


def simhash_tag_concentration(conn) -> list[dict]:
    """Per-simhash tag concentration: groups with 2+ tagged chunks, ordered by tag diversity."""
    rows = conn.execute(
        """
        SELECT c.simhash,
               COUNT(DISTINCT ct.tag) AS distinct_tags,
               COUNT(DISTINCT c.chunk_id) AS tagged_chunks,
               COUNT(ct.tag) AS tag_assignments,
               ROUND(AVG(ct.score), 4) AS avg_score
        FROM chunks c
        JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
        GROUP BY c.simhash
        HAVING COUNT(DISTINCT c.chunk_id) >= 2
        ORDER BY distinct_tags DESC, tagged_chunks DESC, c.simhash
        """
    ).fetchall()
    return [
        {
            "simhash": r[0],
            "distinct_tags": r[1],
            "tagged_chunks": r[2],
            "tag_assignments": r[3],
            "avg_score": r[4],
            "tag_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def simhash_tag_summary(conn) -> dict:
    """Aggregate simhash-tag statistics."""
    total_simhashes = conn.execute(
        "SELECT COUNT(DISTINCT c.simhash) FROM chunks c JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id"
    ).fetchone()[0]

    total_tagged_chunks = conn.execute(
        "SELECT COUNT(DISTINCT c.chunk_id) FROM chunks c JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id"
    ).fetchone()[0]

    collision_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.simhash
            HAVING COUNT(DISTINCT c.chunk_id) >= 2
        )
        """
    ).fetchone()[0]

    cross_tag_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.simhash
            HAVING COUNT(DISTINCT c.chunk_id) >= 2
               AND COUNT(DISTINCT ct.tag) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT c.simhash, ct.tag
            FROM chunks c
            JOIN chunk_tags ct ON ct.chunk_id = c.chunk_id
            GROUP BY c.simhash, ct.tag
        )
        """
    ).fetchone()[0]

    return {
        "total_simhashes": total_simhashes,
        "total_tagged_chunks": total_tagged_chunks,
        "collision_groups": collision_groups,
        "cross_tag_groups": cross_tag_groups,
        "cross_tag_rate": round(cross_tag_groups / max(collision_groups, 1), 4),
        "distinct_simhash_tag_pairs": distinct_pairs,
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

        # simhash 1000: c1 tagged (python, ml), c2 tagged (python) -- cross-tag; simhash 2000: c3 tagged (ml), c4 tagged (ml) -- same tag; simhash 3000: c5 tagged (web) -- singleton
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 35, "jkl", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s1", 5, "results", "claim", None, "t", "t", 40, "mno", 3000, 0, "accepted", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "python", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "python", 0.7, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c3", "ml", 0.6, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c4", "ml", 0.5, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c5", "web", 0.4, t1))
        conn.commit()

        # 1. by-simhash: simhash 1000 has 2 distinct tags (python, ml)
        bs = tags_by_simhash(conn)
        g1000 = [r for r in bs if r["simhash"] == 1000][0]
        assert g1000["distinct_tags"] == 2
        ok += 1

        # 2. simhash 2000 has 1 distinct tag (ml)
        g2000 = [r for r in bs if r["simhash"] == 2000][0]
        assert g2000["distinct_tags"] == 1
        ok += 1

        # 3. simhash 3000 not in results (singleton)
        g3000 = [r for r in bs if r["simhash"] == 3000]
        assert len(g3000) == 0
        ok += 1

        # 4. by-tag: "python" has 1 distinct simhash (1000)
        bt = simhash_groups_by_tag(conn)
        python = [r for r in bt if r["tag"] == "python"][0]
        assert python["distinct_simhashes"] == 1
        ok += 1

        # 5. "ml" has 2 distinct simhashes (1000, 2000)
        ml = [r for r in bt if r["tag"] == "ml"][0]
        assert ml["distinct_simhashes"] == 2
        ok += 1

        # 6. "ml" has 3 tagged chunks (c1, c3, c4)
        assert ml["tagged_chunks"] == 3
        ok += 1

        # 7. concentration: simhash 1000 tag_ratio = 2/2 = 1.0
        conc = simhash_tag_concentration(conn)
        c1000 = [r for r in conc if r["simhash"] == 1000][0]
        assert c1000["tag_ratio"] == 1.0
        ok += 1

        # 8. simhash 2000 tag_ratio = 1/2 = 0.5
        c2000 = [r for r in conc if r["simhash"] == 2000][0]
        assert c2000["tag_ratio"] == 0.5
        ok += 1

        # 9. simhash 3000 not in concentration (singleton)
        c3000 = [r for r in conc if r["simhash"] == 3000]
        assert len(c3000) == 0
        ok += 1

        # 10. summary: collision_groups = 2 (1000, 2000)
        s = simhash_tag_summary(conn)
        assert s["collision_groups"] == 2
        ok += 1

        # 11. cross_tag_groups = 1 (1000)
        assert s["cross_tag_groups"] == 1
        ok += 1

        # 12. total_simhashes = 3
        assert s["total_simhashes"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cross_tag_rate"] == s["cross_tag_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        s = simhash_tag_summary(conn)
        assert s["total_simhashes"] == 0
        assert s["total_tagged_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Simhash tag profile analysis")
    ap.add_argument("command", choices=["by-simhash", "by-tag", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS simhash_tag_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-simhash":
        rows = tags_by_simhash(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups with tags found.")
            else:
                print(f"{'simhash':<16} {'tags':<8} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_tags']:<8} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "by-tag":
        rows = simhash_groups_by_tag(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No tag simhash data found.")
            else:
                print(f"{'tag':<16} {'simhashes':<12} {'chunks':<8} {'assignments':<14} {'avg_score'}")
                for r in rows:
                    print(f"{r['tag']:<16} {r['distinct_simhashes']:<12} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:.4f}")
    elif args.command == "concentration":
        rows = simhash_tag_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No simhash collision groups with tags found.")
            else:
                print(f"{'simhash':<16} {'tags':<8} {'chunks':<8} {'assignments':<14} {'avg_score':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['simhash']:<16} {r['distinct_tags']:<8} {r['tagged_chunks']:<8} {r['tag_assignments']:<14} {r['avg_score']:<12.4f} {r['tag_ratio']:.4f}")
    elif args.command == "summary":
        s = simhash_tag_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
