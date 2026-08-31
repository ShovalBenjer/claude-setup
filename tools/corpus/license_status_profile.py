#!/usr/bin/env python3
"""License status profile: how licenses distribute across chunk statuses.

license_liveness_profile.py profiles licenses by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool joins sources.license_spdx with chunks.status to measure which
licenses correlate with accepted versus quarantined or rejected chunks,
or how chunk quality distributes across license types.

Usage:
    python tools/corpus/license_status_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_status_profile.py by-status [--db PATH] [--json]
    python tools/corpus/license_status_profile.py acceptance [--db PATH] [--json]
    python tools/corpus/license_status_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_status_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def statuses_by_license(conn) -> list[dict]:
    """Chunk status distribution per license."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT c.status) AS distinct_statuses,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        GROUP BY s.license_spdx
        ORDER BY total_chunks DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "distinct_statuses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def licenses_by_status(conn) -> list[dict]:
    """License distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(c.word_count) AS total_words
        FROM chunks c
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY c.status
        ORDER BY total_chunks DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "distinct_licenses": r[1],
            "total_chunks": r[2],
            "total_words": r[3],
        }
        for r in rows
    ]


def license_acceptance_rate(conn) -> list[dict]:
    """Per-license acceptance rate, filtered to licenses with at least 2 chunks."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(c.chunk_id) AS total_chunks,
               SUM(CASE WHEN c.status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
               SUM(CASE WHEN c.status = 'quarantined' THEN 1 ELSE 0 END) AS quarantined,
               SUM(CASE WHEN c.status = 'rejected' THEN 1 ELSE 0 END) AS rejected
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        GROUP BY s.license_spdx
        HAVING COUNT(c.chunk_id) >= 2
        ORDER BY CAST(SUM(CASE WHEN c.status = 'accepted' THEN 1 ELSE 0 END) AS REAL)
                 / COUNT(c.chunk_id) DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license": r[0],
            "total_chunks": r[1],
            "accepted": r[2],
            "quarantined": r[3],
            "rejected": r[4],
            "acceptance_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def license_status_summary(conn) -> dict:
    """Aggregate license-status statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    licenses_with_chunks = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        """
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    total_accepted = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]

    overall_acceptance_rate = round(total_accepted / max(total_chunks, 1), 4)

    licenses_multi_status = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT s.license_spdx
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            GROUP BY s.license_spdx
            HAVING COUNT(DISTINCT c.status) > 1
        )
        """
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT s.license_spdx, c.status
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            GROUP BY s.license_spdx, c.status
        )
        """
    ).fetchone()[0]

    return {
        "total_licenses": total_licenses,
        "licenses_with_chunks": licenses_with_chunks,
        "total_chunks": total_chunks,
        "total_accepted": total_accepted,
        "overall_acceptance_rate": overall_acceptance_rate,
        "licenses_multi_status": licenses_multi_status,
        "multi_status_rate": round(licenses_multi_status / max(licenses_with_chunks, 1), 4),
        "distinct_license_status_pairs": distinct_pairs,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # MIT: s1 (2 accepted, 1 quarantined); Apache-2.0: s2 (1 accepted, 1 rejected); CC-BY-4.0: s3 (1 accepted)
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "results", "claim", None, "t", "t", 25, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s2", 1, "intro", "claim", None, "t", "t", 35, "jkl", 4000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 2, "methods", "claim", None, "t", "t", 15, "mno", 5000, 0, "rejected", "duplicate", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s3", 1, "intro", "claim", None, "t", "t", 40, "pqr", 6000, 0, "accepted", None, t1))
        conn.commit()

        # 1. by-license: MIT has 2 distinct statuses (accepted, quarantined)
        bl = statuses_by_license(conn)
        mit = [r for r in bl if r["license"] == "MIT"][0]
        assert mit["distinct_statuses"] == 2
        ok += 1

        # 2. MIT has 3 total chunks
        assert mit["total_chunks"] == 3
        ok += 1

        # 3. Apache-2.0 has 2 distinct statuses (accepted, rejected)
        apache = [r for r in bl if r["license"] == "Apache-2.0"][0]
        assert apache["distinct_statuses"] == 2
        ok += 1

        # 4. by-status: "accepted" has 3 licenses (MIT, Apache-2.0, CC-BY-4.0)
        bs = licenses_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["distinct_licenses"] == 3
        ok += 1

        # 5. "quarantined" has 1 license (MIT)
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["distinct_licenses"] == 1
        ok += 1

        # 6. "rejected" has 1 license (Apache-2.0)
        rejected = [r for r in bs if r["status"] == "rejected"][0]
        assert rejected["distinct_licenses"] == 1
        ok += 1

        # 7. acceptance: MIT rate = 2/3
        ar = license_acceptance_rate(conn)
        mit_ar = [r for r in ar if r["license"] == "MIT"][0]
        assert mit_ar["acceptance_rate"] == round(2 / 3, 4)
        ok += 1

        # 8. Apache-2.0 rate = 1/2 = 0.5
        apache_ar = [r for r in ar if r["license"] == "Apache-2.0"][0]
        assert apache_ar["acceptance_rate"] == 0.5
        ok += 1

        # 9. CC-BY-4.0 not in acceptance (only 1 chunk, below threshold)
        cc_ar = [r for r in ar if r["license"] == "CC-BY-4.0"]
        assert len(cc_ar) == 0
        ok += 1

        # 10. summary: total_licenses = 3
        s = license_status_summary(conn)
        assert s["total_licenses"] == 3
        ok += 1

        # 11. total_accepted = 4 (c1, c2, c4, c6)
        assert s["total_accepted"] == 4
        ok += 1

        # 12. licenses_multi_status = 2 (MIT, Apache-2.0 both have >1 status)
        assert s["licenses_multi_status"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["overall_acceptance_rate"] == s["overall_acceptance_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = license_status_summary(conn)
        assert s["total_licenses"] == 0
        assert s["total_chunks"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License status profile analysis")
    ap.add_argument("command", choices=["by-license", "by-status", "acceptance", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_status_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = statuses_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license status data found.")
            else:
                print(f"{'license':<20} {'statuses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['distinct_statuses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "by-status":
        rows = licenses_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status license data found.")
            else:
                print(f"{'status':<14} {'licenses':<10} {'chunks':<8} {'words'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['distinct_licenses']:<10} {r['total_chunks']:<8} {r['total_words']}")
    elif args.command == "acceptance":
        rows = license_acceptance_rate(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No licenses with multiple chunks found.")
            else:
                print(f"{'license':<20} {'chunks':<8} {'accepted':<10} {'quarantined':<12} {'rejected':<10} {'rate'}")
                for r in rows:
                    print(f"{r['license']:<20} {r['total_chunks']:<8} {r['accepted']:<10} {r['quarantined']:<12} {r['rejected']:<10} {r['acceptance_rate']:.4f}")
    elif args.command == "summary":
        s = license_status_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
