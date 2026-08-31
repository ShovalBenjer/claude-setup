#!/usr/bin/env python3
"""Liveness citation profile: how source liveness relates to citations.

liveness_cross_analysis.py cross-tabulates liveness against kind,
publisher, and license. No tool joins sources.liveness with citations
to measure whether live sources produce more verified citations than
stale or archived ones, or how citation target diversity varies by
liveness state.

Usage:
    python tools/corpus/liveness_citation_profile.py by-liveness [--db PATH] [--json]
    python tools/corpus/liveness_citation_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/liveness_citation_profile.py verification [--db PATH] [--json]
    python tools/corpus/liveness_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/liveness_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_liveness(conn) -> list[dict]:
    """Citation distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.liveness
        ORDER BY total_citations DESC, s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citation_tags_by_liveness(conn) -> list[dict]:
    """Citation tag distribution per source liveness state."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               ci.tag,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.liveness, ci.tag
        ORDER BY s.liveness, total DESC
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "tag": r[1],
            "total": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def liveness_verification_profile(conn) -> list[dict]:
    """Verification rate per liveness state, filtered to states with at least 2 citations."""
    rows = conn.execute(
        """
        SELECT s.liveness,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        GROUP BY s.liveness
        HAVING COUNT(ci.citation_id) >= 2
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, s.liveness
        """
    ).fetchall()
    return [
        {
            "liveness": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def liveness_citation_summary(conn) -> dict:
    """Aggregate liveness-citation statistics."""
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    states_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT s.liveness)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        JOIN sources s ON s.source_id = c.source_id
        """
    ).fetchone()[0]

    total_states = conn.execute(
        "SELECT COUNT(DISTINCT liveness) FROM sources"
    ).fetchone()[0]

    avg_citations_per_state = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT s.liveness, COUNT(ci.citation_id) AS cite_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            JOIN sources s ON s.source_id = c.source_id
            GROUP BY s.liveness
        )
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "liveness_states_with_citations": states_with_citations,
        "total_liveness_states": total_states,
        "liveness_citation_coverage": round(states_with_citations / max(total_states, 1), 4),
        "avg_citations_per_state": avg_citations_per_state or 0.0,
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "stale", "def", 200, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "MIT", "vendor", "self", None, None, t1, None, None, "archived", "ghi", 150, None),
        )

        # c1: live, c2: live, c3: stale, c4: archived (no citations)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "methods", "claim", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "methods", "claim", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Citations: live c1 has 3 (2 verified), live c2 has 1 (1 verified),
        # stale c3 has 2 (0 verified), archived c4 has none
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

        # 1. by-liveness: "live" has 4 citations
        bl = citations_by_liveness(conn)
        live = [r for r in bl if r["liveness"] == "live"][0]
        assert live["total_citations"] == 4
        ok += 1

        # 2. "live" has 3 verified
        assert live["verified"] == 3
        ok += 1

        # 3. "stale" has 2 citations
        stale = [r for r in bl if r["liveness"] == "stale"][0]
        assert stale["total_citations"] == 2
        ok += 1

        # 4. "archived" not in results (no citations)
        archived = [r for r in bl if r["liveness"] == "archived"]
        assert len(archived) == 0
        ok += 1

        # 5. citation_tags_by_liveness: live has "ref" with 3
        ct = citation_tags_by_liveness(conn)
        live_ref = [r for r in ct if r["liveness"] == "live" and r["tag"] == "ref"]
        assert len(live_ref) == 1 and live_ref[0]["total"] == 3
        ok += 1

        # 6. live has "note" with 1
        live_note = [r for r in ct if r["liveness"] == "live" and r["tag"] == "note"]
        assert len(live_note) == 1 and live_note[0]["total"] == 1
        ok += 1

        # 7. stale has None tag with 1
        stale_none = [r for r in ct if r["liveness"] == "stale" and r["tag"] is None]
        assert len(stale_none) == 1 and stale_none[0]["total"] == 1
        ok += 1

        # 8. verification: "live" rate = 3/4 = 0.75
        vp = liveness_verification_profile(conn)
        live_vp = [r for r in vp if r["liveness"] == "live"][0]
        assert live_vp["verification_rate"] == 0.75
        ok += 1

        # 9. "stale" rate = 0/2 = 0.0
        stale_vp = [r for r in vp if r["liveness"] == "stale"][0]
        assert stale_vp["verification_rate"] == 0.0
        ok += 1

        # 10. "archived" not in verification (no citations)
        archived_vp = [r for r in vp if r["liveness"] == "archived"]
        assert len(archived_vp) == 0
        ok += 1

        # 11. summary: total_citations = 6
        s = liveness_citation_summary(conn)
        assert s["total_citations"] == 6
        ok += 1

        # 12. liveness_states_with_citations = 2 (live, stale)
        assert s["liveness_states_with_citations"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["liveness_citation_coverage"] == s["liveness_citation_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = liveness_citation_summary(conn)
        assert s["total_citations"] == 0
        assert s["liveness_states_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Liveness citation profile analysis")
    ap.add_argument("command", choices=["by-liveness", "by-tag", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS liveness_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-liveness":
        rows = citations_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness citation data found.")
            else:
                print(f"{'liveness':<12} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['liveness']:<12} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-tag":
        rows = citation_tags_by_liveness(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness citation tag data found.")
            else:
                print(f"{'liveness':<12} {'tag':<12} {'total':<8} {'verified'}")
                for r in rows:
                    tag = r["tag"] or "(none)"
                    print(f"{r['liveness']:<12} {tag:<12} {r['total']:<8} {r['verified']}")
    elif args.command == "verification":
        rows = liveness_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No liveness states with multiple citations found.")
            else:
                print(f"{'liveness':<12} {'total':<8} {'verified':<10} {'unverified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['liveness']:<12} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = liveness_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
