#!/usr/bin/env python3
"""Version FTS coverage: how chunk revisions affect searchable word count.

version_source_profile.py measures revision activity per source.
fts_edge_reachability.py correlates edges with FTS word count.
No tool measures how word count changes across chunk versions,
which sources gain or lose searchable content through revisions,
or how much total churn revisions produce relative to final word
count.

Usage:
    python tools/corpus/version_fts_coverage.py by-source [--db PATH] [--json]
    python tools/corpus/version_fts_coverage.py word-delta [--db PATH] [--json]
    python tools/corpus/version_fts_coverage.py churn-rate [--db PATH] [--json]
    python tools/corpus/version_fts_coverage.py summary [--db PATH] [--json]
    python tools/corpus/version_fts_coverage.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def version_fts_by_source(conn) -> list[dict]:
    """Per-source version word count statistics."""
    rows = conn.execute(
        """
        SELECT c.source_id, s.title,
               COUNT(DISTINCT v.chunk_id) AS versioned_chunks,
               COUNT(v.version_id) AS total_versions,
               SUM(CASE WHEN v.version_num = first_v.min_ver THEN v.word_count ELSE 0 END) AS initial_words,
               SUM(CASE WHEN v.version_num = last_v.max_ver THEN v.word_count ELSE 0 END) AS latest_words
        FROM chunk_versions v
        JOIN chunks c ON c.chunk_id = v.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        JOIN (
            SELECT chunk_id, MIN(version_num) AS min_ver
            FROM chunk_versions GROUP BY chunk_id
        ) first_v ON first_v.chunk_id = v.chunk_id
        JOIN (
            SELECT chunk_id, MAX(version_num) AS max_ver
            FROM chunk_versions GROUP BY chunk_id
        ) last_v ON last_v.chunk_id = v.chunk_id
        GROUP BY c.source_id
        ORDER BY total_versions DESC, c.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "versioned_chunks": r[2],
            "total_versions": r[3],
            "initial_words": r[4],
            "latest_words": r[5],
            "net_word_change": r[5] - r[4],
        }
        for r in rows
    ]


def version_word_delta(conn) -> list[dict]:
    """Per-chunk word count delta between first and latest version."""
    rows = conn.execute(
        """
        SELECT v_first.chunk_id, c.source_id, c.word_count AS current_words,
               v_first.word_count AS first_words,
               v_last.word_count AS last_words,
               v_last.word_count - v_first.word_count AS delta,
               last_v.max_ver AS version_count
        FROM (
            SELECT chunk_id, MIN(version_num) AS min_ver, MAX(version_num) AS max_ver
            FROM chunk_versions GROUP BY chunk_id
        ) last_v
        JOIN chunk_versions v_first
          ON v_first.chunk_id = last_v.chunk_id AND v_first.version_num = last_v.min_ver
        JOIN chunk_versions v_last
          ON v_last.chunk_id = last_v.chunk_id AND v_last.version_num = last_v.max_ver
        JOIN chunks c ON c.chunk_id = last_v.chunk_id
        ORDER BY ABS(v_last.word_count - v_first.word_count) DESC, last_v.chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "current_words": r[2],
            "first_words": r[3],
            "last_words": r[4],
            "delta": r[5],
            "version_count": r[6],
            "grew": r[5] > 0,
        }
        for r in rows
    ]


def version_churn_rate(conn) -> list[dict]:
    """Total word count churn per source from consecutive version deltas."""
    rows = conn.execute(
        """
        SELECT c.source_id, s.title,
               SUM(ABS(v2.word_count - v1.word_count)) AS total_churn,
               COUNT(*) AS transition_count,
               SUM(CASE WHEN v2.word_count > v1.word_count THEN 1 ELSE 0 END) AS grew,
               SUM(CASE WHEN v2.word_count < v1.word_count THEN 1 ELSE 0 END) AS shrank,
               SUM(CASE WHEN v2.word_count = v1.word_count THEN 1 ELSE 0 END) AS unchanged
        FROM chunk_versions v1
        JOIN chunk_versions v2
          ON v2.chunk_id = v1.chunk_id AND v2.version_num = v1.version_num + 1
        JOIN chunks c ON c.chunk_id = v1.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY c.source_id
        ORDER BY total_churn DESC, c.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "total_churn": r[2],
            "transition_count": r[3],
            "grew": r[4],
            "shrank": r[5],
            "unchanged": r[6],
        }
        for r in rows
    ]


def version_fts_summary(conn) -> dict:
    """Aggregate version FTS coverage statistics."""
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    total_words = conn.execute(
        "SELECT COALESCE(SUM(word_count), 0) FROM chunks"
    ).fetchone()[0]

    versioned_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_versions"
    ).fetchone()[0]

    total_versions = conn.execute(
        "SELECT COUNT(*) FROM chunk_versions"
    ).fetchone()[0]

    initial_words = conn.execute(
        """
        SELECT COALESCE(SUM(v.word_count), 0)
        FROM chunk_versions v
        JOIN (SELECT chunk_id, MIN(version_num) AS mn FROM chunk_versions GROUP BY chunk_id) f
          ON f.chunk_id = v.chunk_id AND v.version_num = f.mn
        """
    ).fetchone()[0]

    latest_words = conn.execute(
        """
        SELECT COALESCE(SUM(v.word_count), 0)
        FROM chunk_versions v
        JOIN (SELECT chunk_id, MAX(version_num) AS mx FROM chunk_versions GROUP BY chunk_id) l
          ON l.chunk_id = v.chunk_id AND v.version_num = l.mx
        """
    ).fetchone()[0]

    churn = conn.execute(
        """
        SELECT COALESCE(SUM(ABS(v2.word_count - v1.word_count)), 0)
        FROM chunk_versions v1
        JOIN chunk_versions v2
          ON v2.chunk_id = v1.chunk_id AND v2.version_num = v1.version_num + 1
        """
    ).fetchone()[0]

    net_change = latest_words - initial_words
    version_coverage = round(versioned_chunks / max(total_chunks, 1), 4)
    churn_ratio = round(churn / max(latest_words, 1), 4)

    return {
        "total_chunks": total_chunks,
        "total_words": total_words,
        "versioned_chunks": versioned_chunks,
        "total_versions": total_versions,
        "initial_words": initial_words,
        "latest_words": latest_words,
        "net_word_change": net_change,
        "total_churn": churn,
        "version_coverage_rate": version_coverage,
        "churn_ratio": churn_ratio,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_versions (version_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, version_num INTEGER NOT NULL, norm_sha256 TEXT NOT NULL, word_count INTEGER NOT NULL, snapshot_utc TEXT NOT NULL, UNIQUE(chunk_id, version_num))")

        t1 = "2026-01-01T00:00:00Z"
        t2 = "2026-01-02T00:00:00Z"
        t3 = "2026-01-03T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )

        # s1: c1 (current 25w), c2 (current 30w)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "h", "claim", None, "t", "t", 25, "abc", 1000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "h", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1),
        )
        # s2: c3 (current 50w), c4 (current 40w, no versions)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "h", "claim", None, "t", "t", 50, "abc", 3000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 2, "h", "claim", None, "t", "t", 40, "abc", 4000, 0, "accepted", None, t1),
        )

        # Versions: c1 v1=20w, v2=22w, v3=25w (grew)
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v1", "c1", 1, "h1", 20, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v2", "c1", 2, "h2", 22, t2))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v3", "c1", 3, "h3", 25, t3))
        # c2 v1=35w, v2=30w (shrank)
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v4", "c2", 1, "h4", 35, t1))
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v5", "c2", 2, "h5", 30, t2))
        # c3 v1=50w (single version, no delta)
        conn.execute("INSERT INTO chunk_versions VALUES (?,?,?,?,?,?)", ("v6", "c3", 1, "h6", 50, t1))
        conn.commit()

        # 1. by-source: s1 has 2 versioned chunks
        bs = version_fts_by_source(conn)
        s1_row = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1_row["versioned_chunks"] == 2
        ok += 1

        # 2. s1 initial_words = 20 + 35 = 55
        assert s1_row["initial_words"] == 55
        ok += 1

        # 3. s1 latest_words = 25 + 30 = 55
        assert s1_row["latest_words"] == 55
        ok += 1

        # 4. s1 net_word_change = 0
        assert s1_row["net_word_change"] == 0
        ok += 1

        # 5. word-delta: c1 delta = 25 - 20 = 5 (grew)
        wd = version_word_delta(conn)
        c1_row = [r for r in wd if r["chunk_id"] == "c1"][0]
        assert c1_row["delta"] == 5
        assert c1_row["grew"] is True
        ok += 1

        # 6. c2 delta = 30 - 35 = -5 (shrank)
        c2_row = [r for r in wd if r["chunk_id"] == "c2"][0]
        assert c2_row["delta"] == -5
        assert c2_row["grew"] is False
        ok += 1

        # 7. c3 delta = 0 (single version)
        c3_row = [r for r in wd if r["chunk_id"] == "c3"][0]
        assert c3_row["delta"] == 0
        ok += 1

        # 8. churn-rate: s1 transitions: c1 v1->v2 |22-20|=2, v2->v3 |25-22|=3; c2 v1->v2 |30-35|=5 => total 10
        cr = version_churn_rate(conn)
        s1_churn = [r for r in cr if r["source_id"] == "s1"][0]
        assert s1_churn["total_churn"] == 10
        ok += 1

        # 9. s1 transition_count = 3
        assert s1_churn["transition_count"] == 3
        ok += 1

        # 10. s2 has no transitions (c3 has only 1 version, c4 has none)
        s2_churn = [r for r in cr if r["source_id"] == "s2"]
        assert len(s2_churn) == 0
        ok += 1

        # 11. summary: versioned_chunks = 3
        s = version_fts_summary(conn)
        assert s["versioned_chunks"] == 3
        ok += 1

        # 12. summary: net_word_change = (25+30+50) - (20+35+50) = 105 - 105 = 0
        assert s["net_word_change"] == 0
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["churn_ratio"] == s["churn_ratio"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_versions (version_id TEXT PRIMARY KEY, chunk_id TEXT NOT NULL, version_num INTEGER NOT NULL, norm_sha256 TEXT NOT NULL, word_count INTEGER NOT NULL, snapshot_utc TEXT NOT NULL, UNIQUE(chunk_id, version_num))")
        s = version_fts_summary(conn)
        assert s["total_chunks"] == 0
        assert s["versioned_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Version FTS coverage analysis")
    ap.add_argument("command", choices=["by-source", "word-delta", "churn-rate", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS version_fts_coverage selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-source":
        rows = version_fts_by_source(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No versioned sources found.")
            else:
                print(f"{'source_id':<14} {'title':<20} {'v_chunks':<10} {'versions':<10} {'init_words':<12} {'latest_words':<14} {'net_change'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['title']:<20} {r['versioned_chunks']:<10} {r['total_versions']:<10} {r['initial_words']:<12} {r['latest_words']:<14} {r['net_word_change']}")
    elif args.command == "word-delta":
        rows = version_word_delta(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No versioned chunks found.")
            else:
                print(f"{'chunk_id':<12} {'source_id':<14} {'current':<10} {'first':<8} {'last':<8} {'delta':<8} {'versions':<10} {'grew'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['source_id']:<14} {r['current_words']:<10} {r['first_words']:<8} {r['last_words']:<8} {r['delta']:<8} {r['version_count']:<10} {r['grew']}")
    elif args.command == "churn-rate":
        rows = version_churn_rate(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No version transitions found.")
            else:
                print(f"{'source_id':<14} {'title':<20} {'churn':<8} {'transitions':<12} {'grew':<6} {'shrank':<8} {'unchanged'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['title']:<20} {r['total_churn']:<8} {r['transition_count']:<12} {r['grew']:<6} {r['shrank']:<8} {r['unchanged']}")
    elif args.command == "summary":
        s = version_fts_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
