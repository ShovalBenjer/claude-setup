#!/usr/bin/env python3
"""Status citation profile: how chunk status relates to citation patterns.

status_enrichment_profile.py profiles statuses by enrichment depth.
status_reason_trends.py tracks status reason evolution.
No tool joins chunks.status with citations to measure whether accepted
chunks carry more citations than quarantined or rejected ones, or how
verification rates vary across chunk statuses.

Usage:
    python tools/corpus/status_citation_profile.py by-status [--db PATH] [--json]
    python tools/corpus/status_citation_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/status_citation_profile.py verification [--db PATH] [--json]
    python tools/corpus/status_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/status_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_status(conn) -> list[dict]:
    """Citation distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.status
        ORDER BY total_citations DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citation_tags_by_status(conn) -> list[dict]:
    """Citation tag distribution per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               ci.tag,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.status, ci.tag
        ORDER BY c.status, total DESC
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "tag": r[1],
            "total": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def status_verification_profile(conn) -> list[dict]:
    """Verification rate per status, filtered to statuses with at least 2 citations."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.status
        HAVING COUNT(ci.citation_id) >= 2
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def status_citation_summary(conn) -> dict:
    """Aggregate status-citation statistics."""
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    statuses_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT c.status)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        """
    ).fetchone()[0]

    total_statuses = conn.execute(
        "SELECT COUNT(DISTINCT status) FROM chunks"
    ).fetchone()[0]

    avg_citations_per_status = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT c.status, COUNT(ci.citation_id) AS cite_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            GROUP BY c.status
        )
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "statuses_with_citations": statuses_with_citations,
        "total_statuses": total_statuses,
        "status_citation_coverage": round(statuses_with_citations / max(total_statuses, 1), 4),
        "avg_citations_per_status": avg_citations_per_status or 0.0,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1: accepted, c2: accepted, c3: quarantined, c4: rejected (no citations)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "quarantined", "low quality", t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "rejected", "duplicate", t1))

        # Citations: accepted c1 has 3 (2 verified), accepted c2 has 1 (1 verified),
        # quarantined c3 has 2 (0 verified), rejected c4 has none
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci1", "c1", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci2", "c1", "http://example.com/b", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci3", "c1", "http://example.com/c", None, "note", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci4", "c2", "http://example.com/a", None, "ref", None, 1, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci5", "c3", "http://example.com/d", None, "ref", None, 0, None))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("ci6", "c3", "http://example.com/e", None, None, None, 0, None))
        conn.commit()

        # 1. by-status: "accepted" has 4 citations
        bs = citations_by_status(conn)
        accepted = [r for r in bs if r["status"] == "accepted"][0]
        assert accepted["total_citations"] == 4
        ok += 1

        # 2. "accepted" has 3 verified
        assert accepted["verified"] == 3
        ok += 1

        # 3. "quarantined" has 2 citations
        quarantined = [r for r in bs if r["status"] == "quarantined"][0]
        assert quarantined["total_citations"] == 2
        ok += 1

        # 4. "rejected" not in results (no citations)
        rejected = [r for r in bs if r["status"] == "rejected"]
        assert len(rejected) == 0
        ok += 1

        # 5. citation_tags_by_status: accepted has "ref" with 3
        ct = citation_tags_by_status(conn)
        acc_ref = [r for r in ct if r["status"] == "accepted" and r["tag"] == "ref"]
        assert len(acc_ref) == 1 and acc_ref[0]["total"] == 3
        ok += 1

        # 6. accepted has "note" with 1
        acc_note = [r for r in ct if r["status"] == "accepted" and r["tag"] == "note"]
        assert len(acc_note) == 1 and acc_note[0]["total"] == 1
        ok += 1

        # 7. quarantined has None tag with 1
        q_none = [r for r in ct if r["status"] == "quarantined" and r["tag"] is None]
        assert len(q_none) == 1 and q_none[0]["total"] == 1
        ok += 1

        # 8. verification: "accepted" rate = 3/4 = 0.75
        vp = status_verification_profile(conn)
        acc_vp = [r for r in vp if r["status"] == "accepted"][0]
        assert acc_vp["verification_rate"] == 0.75
        ok += 1

        # 9. "quarantined" rate = 0/2 = 0.0
        q_vp = [r for r in vp if r["status"] == "quarantined"][0]
        assert q_vp["verification_rate"] == 0.0
        ok += 1

        # 10. "rejected" not in verification (no citations)
        rej_vp = [r for r in vp if r["status"] == "rejected"]
        assert len(rej_vp) == 0
        ok += 1

        # 11. summary: total_citations = 6
        s = status_citation_summary(conn)
        assert s["total_citations"] == 6
        ok += 1

        # 12. statuses_with_citations = 2 (accepted, quarantined)
        assert s["statuses_with_citations"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["status_citation_coverage"] == s["status_citation_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = status_citation_summary(conn)
        assert s["total_citations"] == 0
        assert s["statuses_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Status citation profile analysis")
    ap.add_argument("command", choices=["by-status", "by-tag", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS status_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-status":
        rows = citations_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status citation data found.")
            else:
                print(f"{'status':<14} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-tag":
        rows = citation_tags_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No status citation tag data found.")
            else:
                print(f"{'status':<14} {'tag':<12} {'total':<8} {'verified'}")
                for r in rows:
                    tag = r["tag"] or "(none)"
                    print(f"{r['status']:<14} {tag:<12} {r['total']:<8} {r['verified']}")
    elif args.command == "verification":
        rows = status_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No statuses with multiple citations found.")
            else:
                print(f"{'status':<14} {'total':<8} {'verified':<10} {'unverified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = status_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
