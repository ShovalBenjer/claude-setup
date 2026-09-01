#!/usr/bin/env python3
"""License liveness profile: how licenses distribute across liveness states.

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool cross-tabulates sources.license_spdx with sources.liveness to
measure which licenses correlate with live versus stale or archived
sources, or how content volume distributes across license-liveness
combinations.

Usage:
    python tools/corpus/license_liveness_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_liveness_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/license_liveness_profile.py concentration [--db PATH] [--json]
    python tools/corpus/license_liveness_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_liveness_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def liveness_by_license(conn) -> list[dict]:
    """Liveness distribution per license."""
    rows = conn.execute(
        """
        SELECT license_spdx,
               COUNT(DISTINCT liveness) AS distinct_states,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY license_spdx
        ORDER BY total_sources DESC, license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def licenses_by_liveness(conn) -> list[dict]:
    """License distribution per liveness state."""
    rows = conn.execute(
        """
        SELECT liveness,
               COUNT(DISTINCT license_spdx) AS distinct_licenses,
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
            "distinct_licenses": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def license_liveness_concentration(conn) -> list[dict]:
    """Per-license liveness concentration: how many states each license spans."""
    rows = conn.execute(
        """
        SELECT license_spdx,
               COUNT(DISTINCT liveness) AS distinct_states,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY license_spdx
        HAVING COUNT(source_id) >= 2
        ORDER BY distinct_states DESC, license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "distinct_states": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "state_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def license_liveness_summary(conn) -> dict:
    """Aggregate license-liveness statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]

    licenses_multi_state = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT license_spdx
            FROM sources
            GROUP BY license_spdx
            HAVING COUNT(DISTINCT liveness) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT license_spdx, liveness
            FROM sources
            GROUP BY license_spdx, liveness
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
        "total_licenses": total_licenses,
        "total_liveness_states": total_states,
        "total_sources": total_sources,
        "licenses_multi_state": licenses_multi_state,
        "multi_state_rate": round(licenses_multi_state / max(total_licenses, 1), 4),
        "distinct_license_liveness_pairs": distinct_pairs,
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
        # MIT: 2 live, 1 stale; Apache-2.0: 1 live; CC-BY-4.0: 1 archived
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "local_md", "S4", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "jkl", 300, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "local_md", "S5", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "archived", "mno", 50, None))
        conn.commit()

        # 1. by-license: MIT has 2 distinct states (live, stale)
        bl = liveness_by_license(conn)
        mit = [r for r in bl if r["license"] == "MIT"][0]
        assert mit["distinct_states"] == 2
        ok += 1

        # 2. MIT has 3 total sources
        assert mit["total_sources"] == 3
        ok += 1

        # 3. Apache-2.0 has 1 distinct state (live)
        apache = [r for r in bl if r["license"] == "Apache-2.0"][0]
        assert apache["distinct_states"] == 1
        ok += 1

        # 4. by-liveness: "live" has 2 distinct licenses (MIT, Apache-2.0)
        bv = licenses_by_liveness(conn)
        live = [r for r in bv if r["liveness"] == "live"][0]
        assert live["distinct_licenses"] == 2
        ok += 1

        # 5. "stale" has 1 license (MIT)
        stale = [r for r in bv if r["liveness"] == "stale"][0]
        assert stale["distinct_licenses"] == 1
        ok += 1

        # 6. "archived" has 1 license (CC-BY-4.0)
        archived = [r for r in bv if r["liveness"] == "archived"][0]
        assert archived["distinct_licenses"] == 1
        ok += 1

        # 7. concentration: MIT has 2 states, 3 sources
        conc = license_liveness_concentration(conn)
        mit_conc = [r for r in conc if r["license"] == "MIT"][0]
        assert mit_conc["distinct_states"] == 2
        ok += 1

        # 8. Apache-2.0 not in concentration (only 1 source, below threshold)
        apache_conc = [r for r in conc if r["license"] == "Apache-2.0"]
        assert len(apache_conc) == 0
        ok += 1

        # 9. CC-BY-4.0 not in concentration (only 1 source, below threshold)
        cc_conc = [r for r in conc if r["license"] == "CC-BY-4.0"]
        assert len(cc_conc) == 0
        ok += 1

        # 10. summary: total_licenses = 3 (MIT, Apache-2.0, CC-BY-4.0)
        s = license_liveness_summary(conn)
        assert s["total_licenses"] == 3
        ok += 1

        # 11. licenses_multi_state = 1 (MIT)
        assert s["licenses_multi_state"] == 1
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
        s = license_liveness_summary(conn)
        assert s["total_licenses"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License liveness profile analysis")
    ap.add_argument("command", choices=["by-license", "by-liveness", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_liveness_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = liveness_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license liveness data found.")
            else:
                print(f"{'license':<20} {'states':<8} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "by-liveness":
        rows = licenses_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness license data found.")
            else:
                print(f"{'liveness':<14} {'licenses':<10} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['liveness']:<14} {r['distinct_licenses']:<10} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "concentration":
        rows = license_liveness_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple sources found.")
            else:
                print(f"{'license':<20} {'states':<8} {'sources':<8} {'bytes':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_states']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['state_ratio']:.4f}")
    elif args.command == "summary":
        s = license_liveness_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
