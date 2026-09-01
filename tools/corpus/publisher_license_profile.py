#!/usr/bin/env python3
"""Publisher license profile: how publishers distribute across licenses.

heading_publisher_profile.py profiles headings by publisher.
license_kind_profile.py profiles licenses by source kind.
No tool cross-tabulates sources.publisher with sources.license_spdx to
measure which publishers use which licenses, or how license choices
distribute across publishers.

Usage:
    python tools/corpus/publisher_license_profile.py by-publisher [--db PATH] [--json]
    python tools/corpus/publisher_license_profile.py by-license [--db PATH] [--json]
    python tools/corpus/publisher_license_profile.py concentration [--db PATH] [--json]
    python tools/corpus/publisher_license_profile.py summary [--db PATH] [--json]
    python tools/corpus/publisher_license_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def licenses_by_publisher(conn) -> list[dict]:
    """License distribution per publisher."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(s.source_id) AS total_sources,
               COUNT(DISTINCT c.chunk_id) AS total_chunks
        FROM sources s
        LEFT JOIN chunks c ON c.source_id = s.source_id
        WHERE s.publisher IS NOT NULL
        GROUP BY s.publisher
        ORDER BY total_sources DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_licenses": r[1],
            "total_sources": r[2],
            "total_chunks": r[3],
        }
        for r in rows
    ]


def publishers_by_license(conn) -> list[dict]:
    """Publisher distribution per license."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT s.publisher) AS distinct_publishers,
               COUNT(s.source_id) AS total_sources,
               COUNT(DISTINCT c.chunk_id) AS total_chunks
        FROM sources s
        LEFT JOIN chunks c ON c.source_id = s.source_id
        WHERE s.publisher IS NOT NULL
        GROUP BY s.license_spdx
        ORDER BY total_sources DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "distinct_publishers": r[1],
            "total_sources": r[2],
            "total_chunks": r[3],
        }
        for r in rows
    ]


def publisher_license_concentration(conn) -> list[dict]:
    """Per-publisher license diversity ordered by distinct licenses."""
    rows = conn.execute(
        """
        SELECT s.publisher,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(s.source_id) AS total_sources,
               COUNT(DISTINCT c.chunk_id) AS total_chunks
        FROM sources s
        LEFT JOIN chunks c ON c.source_id = s.source_id
        WHERE s.publisher IS NOT NULL
        GROUP BY s.publisher
        ORDER BY distinct_licenses DESC, total_sources DESC, s.publisher
        """
    ).fetchall()
    return [
        {
            "publisher": r[0],
            "distinct_licenses": r[1],
            "total_sources": r[2],
            "total_chunks": r[3],
            "license_ratio": round(r[1] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def publisher_license_summary(conn) -> dict:
    """Aggregate publisher-license statistics."""
    total_publishers = conn.execute(
        "SELECT COUNT(DISTINCT publisher) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    total_sources = conn.execute(
        "SELECT COUNT(*) FROM sources WHERE publisher IS NOT NULL"
    ).fetchone()[0]

    multi_license_publishers = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT publisher
            FROM sources
            WHERE publisher IS NOT NULL
            GROUP BY publisher
            HAVING COUNT(DISTINCT license_spdx) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT publisher, license_spdx
            FROM sources
            WHERE publisher IS NOT NULL
            GROUP BY publisher, license_spdx
        )
        """
    ).fetchone()[0]

    return {
        "total_publishers": total_publishers,
        "total_licenses": total_licenses,
        "total_sources": total_sources,
        "multi_license_publishers": multi_license_publishers,
        "multi_license_rate": round(multi_license_publishers / max(total_publishers, 1), 4),
        "distinct_publisher_license_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # acme: MIT (s1), Apache-2.0 (s2) -- multi-license
        # globex: MIT (s3), MIT (s4) -- single license
        # initech: Apache-2.0 (s5) -- single license
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", "acme", None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", "acme", None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "ghi", 150, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s4", "u://s4", "local_md", "S4", "MIT", "vendor", "self", "globex", None, t1, None, None, "live", "jkl", 120, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s5", "u://s5", "local_md", "S5", "Apache-2.0", "vendor", "self", "initech", None, t1, None, None, "live", "mno", 80, None))

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s2", 1, "intro", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s3", 1, "intro", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-publisher: acme has 2 distinct licenses
        bp = licenses_by_publisher(conn)
        acme = [r for r in bp if r["publisher"] == "acme"][0]
        assert acme["distinct_licenses"] == 2
        ok += 1

        # 2. globex has 1 distinct license
        globex = [r for r in bp if r["publisher"] == "globex"][0]
        assert globex["distinct_licenses"] == 1
        ok += 1

        # 3. acme has 2 sources
        assert acme["total_sources"] == 2
        ok += 1

        # 4. by-license: MIT has 2 distinct publishers (acme, globex)
        bl = publishers_by_license(conn)
        mit = [r for r in bl if r["license_spdx"] == "MIT"][0]
        assert mit["distinct_publishers"] == 2
        ok += 1

        # 5. Apache-2.0 has 2 distinct publishers (acme, initech)
        apache = [r for r in bl if r["license_spdx"] == "Apache-2.0"][0]
        assert apache["distinct_publishers"] == 2
        ok += 1

        # 6. MIT has 3 sources (s1, s3, s4)
        assert mit["total_sources"] == 3
        ok += 1

        # 7. concentration: acme license_ratio = 2/2 = 1.0
        conc = publisher_license_concentration(conn)
        c_acme = [r for r in conc if r["publisher"] == "acme"][0]
        assert c_acme["license_ratio"] == 1.0
        ok += 1

        # 8. globex license_ratio = 1/2 = 0.5
        c_globex = [r for r in conc if r["publisher"] == "globex"][0]
        assert c_globex["license_ratio"] == 0.5
        ok += 1

        # 9. initech license_ratio = 1/1 = 1.0
        c_initech = [r for r in conc if r["publisher"] == "initech"][0]
        assert c_initech["license_ratio"] == 1.0
        ok += 1

        # 10. summary: total_publishers = 3
        s = publisher_license_summary(conn)
        assert s["total_publishers"] == 3
        ok += 1

        # 11. multi_license_publishers = 1 (acme)
        assert s["multi_license_publishers"] == 1
        ok += 1

        # 12. distinct_publisher_license_pairs = 4 (acme-MIT, acme-Apache, globex-MIT, initech-Apache)
        assert s["distinct_publisher_license_pairs"] == 4
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_license_rate"] == s["multi_license_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = publisher_license_summary(conn)
        assert s["total_publishers"] == 0
        assert s["total_sources"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Publisher license profile analysis")
    ap.add_argument("command", choices=["by-publisher", "by-license", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS publisher_license_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-publisher":
        rows = licenses_by_publisher(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher license data found.")
            else:
                print(f"{'publisher':<16} {'licenses':<10} {'sources':<10} {'chunks'}")
                for r in rows:
                    print(f"{r['publisher']:<16} {r['distinct_licenses']:<10} {r['total_sources']:<10} {r['total_chunks']}")
    elif args.command == "by-license":
        rows = publishers_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license publisher data found.")
            else:
                print(f"{'license':<16} {'publishers':<12} {'sources':<10} {'chunks'}")
                for r in rows:
                    print(f"{r['license_spdx']:<16} {r['distinct_publishers']:<12} {r['total_sources']:<10} {r['total_chunks']}")
    elif args.command == "concentration":
        rows = publisher_license_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No publisher license data found.")
            else:
                print(f"{'publisher':<16} {'licenses':<10} {'sources':<10} {'chunks':<8} {'ratio'}")
                for r in rows:
                    print(f"{r['publisher']:<16} {r['distinct_licenses']:<10} {r['total_sources']:<10} {r['total_chunks']:<8} {r['license_ratio']:.4f}")
    elif args.command == "summary":
        s = publisher_license_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
