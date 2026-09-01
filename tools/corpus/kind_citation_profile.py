#!/usr/bin/env python3
"""Kind citation profile: how chunk kinds relate to citation patterns.

chunk_kind_profile.py profiles kinds per source.
kind_tag_profile.py profiles kinds by tag vocabulary.
kind_domain_profile.py profiles kinds by semantic domain.
No tool joins chunks.kind with citations to measure which chunk kinds
concentrate citations, how verification rates vary across kinds, or
how citation target diversity differs between claim and code chunks.

Usage:
    python tools/corpus/kind_citation_profile.py by-kind [--db PATH] [--json]
    python tools/corpus/kind_citation_profile.py by-tag [--db PATH] [--json]
    python tools/corpus/kind_citation_profile.py verification [--db PATH] [--json]
    python tools/corpus/kind_citation_profile.py summary [--db PATH] [--json]
    python tools/corpus/kind_citation_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def citations_by_kind(conn) -> list[dict]:
    """Citation distribution per chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(ci.citation_id) AS total_citations,
               COUNT(DISTINCT c.chunk_id) AS citing_chunks,
               SUM(ci.verified) AS verified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.kind
        ORDER BY total_citations DESC, c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "total_citations": r[1],
            "citing_chunks": r[2],
            "verified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[3] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def citation_tags_by_kind(conn) -> list[dict]:
    """Citation tag distribution per chunk kind."""
    rows = conn.execute(
        """
        SELECT c.kind,
               ci.tag,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.kind, ci.tag
        ORDER BY c.kind, total DESC
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "tag": r[1],
            "total": r[2],
            "verified": r[3],
        }
        for r in rows
    ]


def kind_verification_profile(conn) -> list[dict]:
    """Verification rate per chunk kind, filtered to kinds with at least 2 citations."""
    rows = conn.execute(
        """
        SELECT c.kind,
               COUNT(ci.citation_id) AS total,
               SUM(ci.verified) AS verified,
               SUM(CASE WHEN ci.verified = 0 THEN 1 ELSE 0 END) AS unverified,
               COUNT(DISTINCT ci.target_uri) AS distinct_targets
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        GROUP BY c.kind
        HAVING COUNT(ci.citation_id) >= 2
        ORDER BY CAST(SUM(ci.verified) AS REAL) / COUNT(ci.citation_id) DESC, c.kind
        """
    ).fetchall()
    return [
        {
            "kind": r[0],
            "total": r[1],
            "verified": r[2],
            "unverified": r[3],
            "distinct_targets": r[4],
            "verification_rate": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def kind_citation_summary(conn) -> dict:
    """Aggregate kind-citation statistics."""
    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    total_verified = conn.execute(
        "SELECT SUM(verified) FROM citations"
    ).fetchone()[0] or 0

    kinds_with_citations = conn.execute(
        """
        SELECT COUNT(DISTINCT c.kind)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        """
    ).fetchone()[0]

    total_kinds = conn.execute(
        "SELECT COUNT(DISTINCT kind) FROM chunks"
    ).fetchone()[0]

    avg_citations_per_kind = conn.execute(
        """
        SELECT ROUND(AVG(cite_count), 4)
        FROM (
            SELECT c.kind, COUNT(ci.citation_id) AS cite_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            GROUP BY c.kind
        )
        """
    ).fetchone()[0]

    distinct_tags = conn.execute(
        """
        SELECT COUNT(DISTINCT ci.tag)
        FROM citations ci
        JOIN chunks c ON c.chunk_id = ci.chunk_id
        WHERE ci.tag IS NOT NULL
        """
    ).fetchone()[0]

    return {
        "total_citations": total_citations,
        "total_verified": total_verified,
        "overall_verification_rate": round(total_verified / max(total_citations, 1), 4),
        "kinds_with_citations": kinds_with_citations,
        "total_kinds": total_kinds,
        "kind_citation_coverage": round(kinds_with_citations / max(total_kinds, 1), 4),
        "avg_citations_per_kind": avg_citations_per_kind or 0.0,
        "distinct_citation_tags": distinct_tags,
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

        # c1: claim, c2: claim, c3: code, c4: prose (no citations)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 30, "def", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "methods", "code", None, "t", "t", 15, "ghi", 3000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "methods", "prose", None, "t", "t", 25, "jkl", 4000, 0, "accepted", None, t1))

        # Citations: claim c1 has 3 (2 verified, tags: ref, ref, note), claim c2 has 1 (1 verified, tag: ref),
        # code c3 has 2 (0 verified, tags: ref, None), prose c4 has none
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

        # 1. by-kind: "claim" has 4 citations (c1=3, c2=1)
        bk = citations_by_kind(conn)
        claim = [r for r in bk if r["kind"] == "claim"][0]
        assert claim["total_citations"] == 4
        ok += 1

        # 2. "claim" has 3 verified
        assert claim["verified"] == 3
        ok += 1

        # 3. "code" has 2 citations
        code = [r for r in bk if r["kind"] == "code"][0]
        assert code["total_citations"] == 2
        ok += 1

        # 4. "prose" not in results (no citations)
        prose = [r for r in bk if r["kind"] == "prose"]
        assert len(prose) == 0
        ok += 1

        # 5. citation_tags_by_kind: claim has "ref" tag entries
        ct = citation_tags_by_kind(conn)
        claim_ref = [r for r in ct if r["kind"] == "claim" and r["tag"] == "ref"]
        assert len(claim_ref) == 1 and claim_ref[0]["total"] == 3
        ok += 1

        # 6. claim has "note" tag entry with 1
        claim_note = [r for r in ct if r["kind"] == "claim" and r["tag"] == "note"]
        assert len(claim_note) == 1 and claim_note[0]["total"] == 1
        ok += 1

        # 7. code has a None tag entry
        code_none = [r for r in ct if r["kind"] == "code" and r["tag"] is None]
        assert len(code_none) == 1 and code_none[0]["total"] == 1
        ok += 1

        # 8. verification: "claim" rate = 3/4 = 0.75
        vp = kind_verification_profile(conn)
        claim_vp = [r for r in vp if r["kind"] == "claim"][0]
        assert claim_vp["verification_rate"] == 0.75
        ok += 1

        # 9. "code" rate = 0/2 = 0.0
        code_vp = [r for r in vp if r["kind"] == "code"][0]
        assert code_vp["verification_rate"] == 0.0
        ok += 1

        # 10. "prose" not in verification (no citations)
        prose_vp = [r for r in vp if r["kind"] == "prose"]
        assert len(prose_vp) == 0
        ok += 1

        # 11. summary: total_citations = 6
        s = kind_citation_summary(conn)
        assert s["total_citations"] == 6
        ok += 1

        # 12. kinds_with_citations = 2 (claim, code)
        assert s["kinds_with_citations"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["kind_citation_coverage"] == s["kind_citation_coverage"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = kind_citation_summary(conn)
        assert s["total_citations"] == 0
        assert s["kinds_with_citations"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Kind citation profile analysis")
    ap.add_argument("command", choices=["by-kind", "by-tag", "verification", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS kind_citation_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-kind":
        rows = citations_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind citation data found.")
            else:
                print(f"{'kind':<12} {'citations':<10} {'chunks':<8} {'verified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['kind']:<12} {r['total_citations']:<10} {r['citing_chunks']:<8} {r['verified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "by-tag":
        rows = citation_tags_by_kind(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kind citation tag data found.")
            else:
                print(f"{'kind':<12} {'tag':<12} {'total':<8} {'verified'}")
                for r in rows:
                    tag = r["tag"] or "(none)"
                    print(f"{r['kind']:<12} {tag:<12} {r['total']:<8} {r['verified']}")
    elif args.command == "verification":
        rows = kind_verification_profile(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No kinds with multiple citations found.")
            else:
                print(f"{'kind':<12} {'total':<8} {'verified':<10} {'unverified':<10} {'targets':<8} {'rate'}")
                for r in rows:
                    print(f"{r['kind']:<12} {r['total']:<8} {r['verified']:<10} {r['unverified']:<10} {r['distinct_targets']:<8} {r['verification_rate']:.4f}")
    elif args.command == "summary":
        s = kind_citation_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
