#!/usr/bin/env python3
"""Kind liveness profile: how source kinds distribute across liveness states.

license_liveness_profile.py profiles licenses by source liveness.
publisher_liveness_profile.py profiles publishers by source liveness.
No tool cross-tabulates sources.kind with sources.liveness to measure
which source kinds remain live versus going stale or archived, or how
content volume distributes across kind-liveness combinations.

Usage:
    python tools/corpus/kind_liveness_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/kind_liveness_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/kind_liveness_profile.py concentration [--db PATH] [--json]
    python tools/corpus/kind_liveness_profile.py summary [--db PATH] [--json]
    python tools/corpus/kind_liveness_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def liveness_by_kind(conn) -> list[dict]:
    """Liveness distribution per source kind."""
    rows = conn.execute(
        """
        SELECT kind,
               COUNT(DISTINCT liveness) AS distinct_states,
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
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def kinds_by_liveness(conn) -> list[dict]:
    """Kind distribution per liveness state."""
    rows = conn.execute(
        """
        SELECT liveness,
               COUNT(DISTINCT kind) AS distinct_kinds,
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
            "distinct_kinds": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def kind_liveness_concentration(conn) -> list[dict]:
    """Per-kind liveness concentration: how many states each kind spans."""
    rows = conn.execute(
        """
        SELECT kind,
               COUNT(DISTINCT liveness) AS distinct_states,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY kind
        HAVING COUNT(source_id) >= 2
        ORDER BY distinct_states DESC, kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "state_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def kind_liveness_summary(conn) -> dict:
    """Aggregate kind-liveness statistics."""
    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM sources"
    ).fetchone()[0]

    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]

    kinds_multi_state = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT kind
            FROM sources
            GROUP BY kind
            HAVING COUNT(DISTINCT liveness) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT kind, liveness
            FROM sources
            GROUP BY kind, liveness
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
        "total_kinds": total_kinds,
        "total_liveness_states": total_states,
        "total_sources": total_sources,
        "kinds_multi_state": kinds_multi_state,
        "multi_state_rate": round(kinds_multi_state / max(total_kinds, 1), 4),
        "distinct_kind_liveness_pairs": distinct_pairs,
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
        # local_md: 2 live, 1 stale; repo: 1 live; paper: 1 archived
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "repo", "S4", "MIT", "vendor", "self", None, None, t1, None, None, "live", "jkl", 300, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "paper", "S5", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "mno", 50, None))
        conn.commit()

        # 1. by-kind: local_md has 2 distinct states (live, stale)
        bk = liveness_by_kind(conn)
        local_md = [r for r in bk if r["kind"] == "local_md"][0]
        assert local_md["distinct_states"] == 2
        ok += 1

        # 2. local_md has 3 total sources
        assert local_md["total_sources"] == 3
        ok += 1

        # 3. repo has 1 distinct state (live)
        repo = [r for r in bk if r["kind"] == "repo"][0]
        assert repo["distinct_states"] == 1
        ok += 1

        # 4. by-liveness: "live" has 2 distinct kinds (local_md, repo)
        bl = kinds_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["distinct_kinds"] == 2
        ok += 1

        # 5. "stale" has 1 kind (local_md)
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["distinct_kinds"] == 1
        ok += 1

        # 6. "archived" has 1 kind (paper)
        archived = [r for r in bl if r["liveness"] == "archived"][0]
        assert archived["distinct_kinds"] == 1
        ok += 1

        # 7. concentration: local_md has 2 states, 3 sources
        conc = kind_liveness_concentration(conn)
        lm_conc = [r for r in conc if r["kind"] == "local_md"][0]
        assert lm_conc["distinct_states"] == 2
        ok += 1

        # 8. repo not in concentration (only 1 source, below threshold)
        repo_conc = [r for r in conc if r["kind"] == "repo"]
        assert len(repo_conc) == 0
        ok += 1

        # 9. paper not in concentration (only 1 source, below threshold)
        paper_conc = [r for r in conc if r["kind"] == "paper"]
        assert len(paper_conc) == 0
        ok += 1

        # 10. summary: total_kinds = 3 (local_md, repo, paper)
        s = kind_liveness_summary(conn)
        assert s["total_kinds"] == 3
        ok += 1

        # 11. kinds_multi_state = 1 (local_md)
        assert s["kinds_multi_state"] == 1
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
        s = kind_liveness_summary(conn)
        assert s["total_kinds"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Kind liveness profile analysis")
    ap.add_argument("command", choices=["by-kind", "by-liveness", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS kind_liveness_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-kind":
        rows = liveness_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind liveness data found.")
            else:
                print(f"{'kind':<20} {'states':<8} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['kind']:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "by-liveness":
        rows = kinds_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness kind data found.")
            else:
                print(f"{'liveness':<14} {'kinds':<8} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_kinds']:<8} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "concentration":
        rows = kind_liveness_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kinds with multiple sources found.")
            else:
                print(f"{'kind':<20} {'states':<8} {'sources':<8} {'bytes':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['kind']:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['state_ratio']:.4f}")
    elif args.command == "summary":
        s = kind_liveness_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
