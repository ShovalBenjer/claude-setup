#!/usr/bin/env python3
"""License kind profile: how licenses distribute across source kinds.

license_liveness_profile.py profiles licenses by source liveness.
license_status_profile.py profiles licenses by chunk status.
No tool cross-tabulates sources.license_spdx with sources.kind to
measure which licenses appear in which source formats, or how content
volume distributes across license-kind combinations.

Usage:
    python tools/corpus/license_kind_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_kind_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/license_kind_profile.py concentration [--db PATH] [--json]
    python tools/corpus/license_kind_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_kind_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def kinds_by_license(conn) -> list[dict]:
    """Kind distribution per license."""
    rows = conn.execute(
        """
        SELECT license_spdx,
               COUNT(DISTINCT kind) AS distinct_kinds,
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
            "distinct_kinds": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def licenses_by_kind(conn) -> list[dict]:
    """License distribution per source kind."""
    rows = conn.execute(
        """
        SELECT kind,
               COUNT(DISTINCT license_spdx) AS distinct_licenses,
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
            "distinct_licenses": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
        }
        for r in rows
    ]


def license_kind_concentration(conn) -> list[dict]:
    """Per-license kind concentration: how many kinds each license spans."""
    rows = conn.execute(
        """
        SELECT license_spdx,
               COUNT(DISTINCT kind) AS distinct_kinds,
               COUNT(source_id) AS total_sources,
               SUM(bytes) AS total_bytes
        FROM sources
        GROUP BY license_spdx
        HAVING COUNT(source_id) >= 2
        ORDER BY distinct_kinds DESC, license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "distinct_kinds": r[1],
            "total_sources": r[2],
            "total_bytes": r[3],
            "kind_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def license_kind_summary(conn) -> dict:
    """Aggregate license-kind statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM sources"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources"
    ).fetchone()[0]

    licenses_multi_kind = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT license_spdx
            FROM sources
            GROUP BY license_spdx
            HAVING COUNT(DISTINCT kind) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT license_spdx, kind
            FROM sources
            GROUP BY license_spdx, kind
        )
        """
    ).fetchone()[0]

    return {
        "total_licenses": total_licenses,
        "total_kinds": total_kinds,
        "total_sources": total_sources,
        "licenses_multi_kind": licenses_multi_kind,
        "multi_kind_rate": round(licenses_multi_kind / max(total_licenses, 1), 4),
        "distinct_license_kind_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # MIT: 2 local_md, 1 repo; Apache-2.0: 1 paper; CC-BY-4.0: 1 local_md
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "repo", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "paper", "S4", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "jkl", 300, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "local_md", "S5", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "mno", 50, None))
        conn.commit()

        # 1. by-license: MIT has 2 distinct kinds (local_md, repo)
        bl = kinds_by_license(conn)
        mit = [r for r in bl if r["license"] == "MIT"][0]
        assert mit["distinct_kinds"] == 2
        ok += 1

        # 2. MIT has 3 total sources
        assert mit["total_sources"] == 3
        ok += 1

        # 3. Apache-2.0 has 1 distinct kind (paper)
        apache = [r for r in bl if r["license"] == "Apache-2.0"][0]
        assert apache["distinct_kinds"] == 1
        ok += 1

        # 4. by-kind: "local_md" has 2 distinct licenses (MIT, CC-BY-4.0)
        bk = licenses_by_kind(conn)
        local_md = [r for r in bk if r["kind"] == "local_md"][0]
        assert local_md["distinct_licenses"] == 2
        ok += 1

        # 5. "repo" has 1 license (MIT)
        repo = [r for r in bk if r["kind"] == "repo"][0]
        assert repo["distinct_licenses"] == 1
        ok += 1

        # 6. "paper" has 1 license (Apache-2.0)
        paper = [r for r in bk if r["kind"] == "paper"][0]
        assert paper["distinct_licenses"] == 1
        ok += 1

        # 7. concentration: MIT has 2 kinds, 3 sources
        conc = license_kind_concentration(conn)
        mit_conc = [r for r in conc if r["license"] == "MIT"][0]
        assert mit_conc["distinct_kinds"] == 2
        ok += 1

        # 8. Apache-2.0 not in concentration (only 1 source, below threshold)
        apache_conc = [r for r in conc if r["license"] == "Apache-2.0"]
        assert len(apache_conc) == 0
        ok += 1

        # 9. CC-BY-4.0 not in concentration (only 1 source, below threshold)
        cc_conc = [r for r in conc if r["license"] == "CC-BY-4.0"]
        assert len(cc_conc) == 0
        ok += 1

        # 10. summary: total_licenses = 3
        s = license_kind_summary(conn)
        assert s["total_licenses"] == 3
        ok += 1

        # 11. licenses_multi_kind = 1 (MIT)
        assert s["licenses_multi_kind"] == 1
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
        s = license_kind_summary(conn)
        assert s["total_licenses"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License kind profile analysis")
    ap.add_argument("command", choices=["by-license", "by-kind", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_kind_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = kinds_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license kind data found.")
            else:
                print(f"{'license':<20} {'kinds':<8} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_kinds']:<8} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "by-kind":
        rows = licenses_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind license data found.")
            else:
                print(f"{'kind':<20} {'licenses':<10} {'sources':<8} {'bytes'}")
                for r in rows:
                    print(f"{r['kind']:<20} {r['distinct_licenses']:<10} {r['total_sources']:<8} {r['total_bytes']}")
    elif args.command == "concentration":
        rows = license_kind_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple sources found.")
            else:
                print(f"{'license':<20} {'kinds':<8} {'sources':<8} {'bytes':<12} {'ratio'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_kinds']:<8} {r['total_sources']:<8} {r['total_bytes']:<12} {r['kind_ratio']:.4f}")
    elif args.command == "summary":
        s = license_kind_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
