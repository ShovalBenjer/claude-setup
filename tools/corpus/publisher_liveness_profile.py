#!/usr/bin/env python3
"""Publisher liveness profile: how publishers distribute across liveness states.

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_domain_profile.py profiles publishers by domain coverage.
No tool cross-tabulates sources.publisher with sources.liveness to
measure which publishers maintain live sources, which have gone
stale, or how content volume distributes across publisher-liveness
combinations.

Usage:
    python tools/corpus/publisher_liveness_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_liveness_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/publisher_liveness_profile.py concentration [--db PATH] [--json]
    python tools/corpus/publisher_liveness_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_liveness_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def liveness_by_publisher(conn) -> list[dict]:
    """Liveness distribution per publisher."""
    rows = conn.execute(
        """
        SELECT publisher,
               COUNT(DISTINCT liveness) AS distinct_states,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes,
               COUNT(DISTINCT source_id) AS source_count
        FROM sources
        GROUP BY publisher
        ORDER BY total_sources DESC, publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "source_count": r[4],
        }
        for r in rows
    ]


def publishers_by_liveness(conn) -> list[dict]:
    """Publisher distribution per liveness state."""
    rows = conn.execute(
        """
        SELECT liveness,
               COUNT(DISTINCT publisher) AS distinct_publishers,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY liveness
        ORDER BY total_sources DESC, liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "distinct_publishers": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def publisher_liveness_concentration(conn) -> list[dict]:
    """Per-publisher liveness concentration: how many states each publisher spans."""
    rows = conn.execute(
        """
        SELECT publisher,
               COUNT(DISTINCT liveness) AS distinct_states,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        WHERE publisher IS NOT NULL
        GROUP BY publisher
        HAVING COUNT(source_id) >= 2
        ORDER BY distinct_states DESC, publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "state_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def publisher_liveness_summary(conn) -> dict:
    """Aggregate publisher-liveness statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]

    publishers_multi_state = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT publisher
            FROM sources
            WHERE publisher IS NOT NULL
            GROUP BY publisher
            HAVING COUNT(DISTINCT liveness) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT publisher, liveness
            FROM sources
            GROUP BY publisher, liveness
        )
        """
    ).fetchone()[0]

    live_source_rate = conn.execute(
        """
        SELECT ROUND(
            CAST(SUM(CASE WHEN liveness = 'live' THEN 1 ELSE 0 END) AS REAL)
            / MAX(COUNT(*), 1), 4)
        FROM sources
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "total_liveness_states": total_states,
        "total_sources": total_sources,
        "publishers_multi_state": publishers_multi_state,
        "multi_state_rate": round(publishers_multi_state / max(total_publishers, 1), 4),
        "distinct_publisher_liveness_pairs": distinct_pairs,
        "live_source_rate": live_source_rate or 0.0,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # acme: 2 live, 1 stale; globex: 1 live; null publisher: 1 archived
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", "acme", None, t1, None, None, "stale", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "local_md", "S4", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "jkl", 300, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "local_md", "S5", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "mno", 50, None))
        conn.commit()

        # 1. by-publisher: acme has 2 distinct states (live, stale)
        bp = liveness_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_states"] == 2
        ok += 1

        # 2. acme has 3 total sources
        assert acme["total_sources"] == 3
        ok += 1

        # 3. globex has 1 distinct state (live)
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_states"] == 1
        ok += 1

        # 4. by-liveness: "live" has 2 distinct publishers (acme, globex)
        bl = publishers_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["distinct_publishers"] == 2
        ok += 1

        # 5. "stale" has 1 publisher (acme)
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["distinct_publishers"] == 1
        ok += 1

        # 6. "archived" has 0 named publishers (null excluded by COUNT DISTINCT)
        archived = [r for r in bl if r["liveness"] == "archived"][0]
        assert archived["distinct_publishers"] == 0
        ok += 1

        # 7. concentration: acme has 2 states, 3 sources
        conc = publisher_liveness_concentration(conn)
        acme_conc = [r for r in conc if r["publisher"] == "acme"][0]
        assert acme_conc["distinct_states"] == 2
        ok += 1

        # 8. globex not in concentration (only 1 source, below threshold)
        globex_conc = [r for r in conc if r["publisher"] == "globex"]
        assert len(globex_conc) == 0
        ok += 1

        # 9. null publisher not in concentration
        null_conc = [r for r in conc if r["publisher"] is None]
        assert len(null_conc) == 0
        ok += 1

        # 10. summary: total_publishers = 2 (acme, globex)
        s = publisher_liveness_summary(conn)
        assert s["total_publishers"] == 2
        ok += 1

        # 11. publishers_multi_state = 1 (acme)
        assert s["publishers_multi_state"] == 1
        ok += 1

        # 12. live_source_rate = 3/5 = 0.6
        assert s["live_source_rate"] == 0.6
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_state_rate"] == s["multi_state_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_liveness_summary(conn)
        assert s["total_publishers"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher liveness profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-liveness", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_liveness_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = liveness_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher liveness data found.")
            else:
                print(f"{'publisher':<20} {'states':<8} {'sources':<8} {'bytes':<12} {'count'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['source_count']}")
    elif args.command == "by-liveness":
        rows = publishers_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness publisher data found.")
            else:
                print(f"{'liveness':<14} {'publishers':<12} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_publishers']:<12} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "concentration":
        rows = publisher_liveness_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with multiple sources found.")
            else:
                print(f"{'publisher':<20} {'states':<8} {'sources':<8} {'bytes':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['publisher']:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['state_ratio']:.4f}")
    elif args.command == "summary":
        s = publisher_liveness_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
