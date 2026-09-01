#!/usr/bin/env python3
"""Publisher kind profile: how publishers distribute across source kinds.

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool cross-tabulates sources.publisher with sources.kind to measure
which publishers contribute which source formats, or how content volume
distributes across publisher-kind combinations.

Usage:
    python tools/corpus/publisher_kind_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_kind_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/publisher_kind_profile.py concentration [--db PATH] [--json]
    python tools/corpus/publisher_kind_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_kind_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def kinds_by_publisher(conn) -> list[dict]:
    """Kind distribution per publisher."""
    rows = conn.execute(
        """
        SELECT publisher,
               COUNT(DISTINCT kind) AS distinct_kinds,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY publisher
        ORDER BY total_sources DESC, publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_kinds": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def publishers_by_kind(conn) -> list[dict]:
    """Publisher distribution per source kind."""
    rows = conn.execute(
        """
        SELECT kind,
               COUNT(DISTINCT publisher) AS distinct_publishers,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY kind
        ORDER BY total_sources DESC, kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_publishers": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def publisher_kind_concentration(conn) -> list[dict]:
    """Per-publisher kind concentration: how many kinds each publisher spans."""
    rows = conn.execute(
        """
        SELECT publisher,
               COUNT(DISTINCT kind) AS distinct_kinds,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        WHERE publisher IS NOT NULL
        GROUP BY publisher
        HAVING COUNT(source_id) >= 2
        ORDER BY distinct_kinds DESC, publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_kinds": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "kind_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def publisher_kind_summary(conn) -> dict:
    """Aggregate publisher-kind statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM sources"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]

    publishers_multi_kind = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT publisher
            FROM sources
            WHERE publisher IS NOT NULL
            GROUP BY publisher
            HAVING COUNT(DISTINCT kind) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT publisher, kind
            FROM sources
            GROUP BY publisher, kind
        )
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "total_kinds": total_kinds,
        "total_sources": total_sources,
        "publishers_multi_kind": publishers_multi_kind,
        "multi_kind_rate": round(publishers_multi_kind / max(total_publishers, 1), 4),
        "distinct_publisher_kind_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # acme: 2 local_md, 1 repo; globex: 1 paper; null publisher: 1 local_md
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "S3", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "paper", "S4", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "jkl", 300, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "local_md", "S5", "MIT", "vendor", "self", None, None, t1, None, None, "live", "mno", 50, None))
        conn.commit()

        # 1. by-publisher: acme has 2 distinct kinds (local_md, repo)
        bp = kinds_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_kinds"] == 2
        ok += 1

        # 2. acme has 3 total sources
        assert acme["total_sources"] == 3
        ok += 1

        # 3. globex has 1 distinct kind (paper)
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_kinds"] == 1
        ok += 1

        # 4. by-kind: "local_md" has 1 named publisher (acme; null excluded)
        bk = publishers_by_kind(conn)
        local_md = [r for r in bk if r["kind"] == "local_md"][0]
        assert local_md["distinct_publishers"] == 1
        ok += 1

        # 5. "repo" has 1 publisher (acme)
        repo = [r for r in bk if r["kind"] == "repo"][0]
        assert repo["distinct_publishers"] == 1
        ok += 1

        # 6. "paper" has 1 publisher (globex)
        paper = [r for r in bk if r["kind"] == "paper"][0]
        assert paper["distinct_publishers"] == 1
        ok += 1

        # 7. concentration: acme has 2 kinds, 3 sources
        conc = publisher_kind_concentration(conn)
        acme_conc = [r for r in conc if r["publisher"] == "acme"][0]
        assert acme_conc["distinct_kinds"] == 2
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
        s = publisher_kind_summary(conn)
        assert s["total_publishers"] == 2
        ok += 1

        # 11. publishers_multi_kind = 1 (acme)
        assert s["publishers_multi_kind"] == 1
        ok += 1

        # 12. total_kinds = 3 (local_md, repo, paper)
        assert s["total_kinds"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_kind_rate"] == s["multi_kind_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_kind_summary(conn)
        assert s["total_publishers"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher kind profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-kind", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_kind_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = kinds_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher kind data found.")
            else:
                print(f"{'publisher':<20} {'kinds':<8} {'sources':<8} {'bytes'}")
                for r in rows:
                    p = r["publisher"] or "(none)"
                    print(f"{p:<20} {r['distinct_kinds']:<8} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "by-kind":
        rows = publishers_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind publisher data found.")
            else:
                print(f"{'kind':<20} {'publishers':<12} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['kind']:<20} {r['distinct_publishers']:<12} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "concentration":
        rows = publisher_kind_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publishers with multiple sources found.")
            else:
                print(f"{'publisher':<20} {'kinds':<8} {'sources':<8} {'bytes':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['publisher']:<20} {r['distinct_kinds']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['kind_ratio']:.4f}")
    elif args.command == "summary":
        s = publisher_kind_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
