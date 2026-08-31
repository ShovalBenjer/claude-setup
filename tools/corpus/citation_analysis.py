#!/usr/bin/env python3
"""Citation analysis: patterns in how chunks cite external resources.

Analyses the citations table to find most-cited URIs, chunks with
highest citation counts, verification rates, and per-source citation
coverage.

Usage:
    python tools/corpus/citation_analysis.py top-targets [--db PATH] [--top N] [--json]
    python tools/corpus/citation_analysis.py coverage [--db PATH] [--json]
    python tools/corpus/citation_analysis.py verification [--db PATH] [--json]
    python tools/corpus/citation_analysis.py uncited-claims [--db PATH] [--limit N] [--json]
    python tools/corpus/citation_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def top_cited_targets(conn, top_n: int = 20) -> list[dict]:
    """Most frequently cited target URIs across all chunks."""
    if not _table_exists(conn, "citations"):
        return []

    rows = conn.execute(
        "SELECT target_uri, count(*) AS cite_count, "
        "count(DISTINCT chunk_id) AS chunk_count, "
        "sum(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified_count "
        "FROM citations "
        "GROUP BY target_uri "
        "ORDER BY cite_count DESC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    return [
        {"target_uri": r[0], "citation_count": r[1],
         "chunk_count": r[2], "verified_count": r[3]}
        for r in rows
    ]


def citation_coverage(conn) -> dict:
    """Per-source citation coverage for accepted claim chunks."""
    if not _table_exists(conn, "chunks"):
        return {"sources": [], "total_claims": 0,
                "cited_claims": 0, "coverage_rate": 0.0}

    has_citations = _table_exists(conn, "citations")

    rows = conn.execute(
        "SELECT c.source_id, s.title, "
        "count(*) AS claim_count "
        "FROM chunks c "
        "JOIN sources s ON s.source_id = c.source_id "
        "WHERE c.status = 'accepted' AND c.kind = 'claim' "
        "GROUP BY c.source_id "
        "ORDER BY claim_count DESC"
    ).fetchall()

    sources = []
    total_claims = 0
    cited_claims = 0

    for r in rows:
        sid = r[0]
        claims = r[2]
        total_claims += claims

        cited = 0
        if has_citations:
            cited = conn.execute(
                "SELECT count(DISTINCT c.chunk_id) "
                "FROM chunks c "
                "JOIN citations ci ON ci.chunk_id = c.chunk_id "
                "WHERE c.source_id = ? AND c.status = 'accepted' "
                "AND c.kind = 'claim'",
                (sid,),
            ).fetchone()[0]

        cited_claims += cited
        sources.append({
            "source_id": sid, "title": r[1],
            "claim_count": claims, "cited_count": cited,
            "coverage": round(cited / claims, 4) if claims else 0.0,
        })

    return {
        "sources": sources,
        "total_claims": total_claims,
        "cited_claims": cited_claims,
        "coverage_rate": round(
            cited_claims / total_claims, 4
        ) if total_claims else 0.0,
    }


def verification_summary(conn) -> dict:
    """Verification rates across all citations."""
    if not _table_exists(conn, "citations"):
        return {"total": 0, "verified": 0, "unverified": 0,
                "rate": 0.0, "by_tag": {}}

    total = conn.execute(
        "SELECT count(*) FROM citations"
    ).fetchone()[0]
    verified = conn.execute(
        "SELECT count(*) FROM citations WHERE verified = 1"
    ).fetchone()[0]

    rows = conn.execute(
        "SELECT tag, count(*) AS total, "
        "sum(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified "
        "FROM citations GROUP BY tag ORDER BY total DESC"
    ).fetchall()

    by_tag = {}
    for r in rows:
        t = r[1]
        v = r[2]
        by_tag[r[0]] = {
            "total": t, "verified": v,
            "rate": round(v / t, 4) if t else 0.0,
        }

    return {
        "total": total,
        "verified": verified,
        "unverified": total - verified,
        "rate": round(verified / total, 4) if total else 0.0,
        "by_tag": by_tag,
    }


def uncited_claims(conn, limit: int = 50) -> list[dict]:
    """Accepted claim chunks with zero citations."""
    if not _table_exists(conn, "chunks"):
        return []

    has_citations = _table_exists(conn, "citations")

    if not has_citations:
        rows = conn.execute(
            "SELECT chunk_id, source_id, heading_path, word_count "
            "FROM chunks "
            "WHERE status = 'accepted' AND kind = 'claim' "
            "ORDER BY chunk_id LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT c.chunk_id, c.source_id, c.heading_path, c.word_count "
            "FROM chunks c "
            "WHERE c.status = 'accepted' AND c.kind = 'claim' "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM citations ci WHERE ci.chunk_id = c.chunk_id"
            ") "
            "ORDER BY c.chunk_id LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {"chunk_id": r[0], "source_id": r[1],
         "heading_path": r[2], "word_count": r[3]}
        for r in rows
    ]


# ── selftest ─────────────────────────────────────────────────────────


def _selftest() -> None:
    import datetime

    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        for sid in ["s1", "s2"]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_data = [
            ("c1", "s1", 0, "H1", "claim"),
            ("c2", "s1", 1, "H2", "claim"),
            ("c3", "s1", 2, "H3", "claim"),
            ("c4", "s2", 0, "H4", "claim"),
            ("c5", "s2", 1, "H5", "prose"),
        ]
        for cd in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (cd[0], cd[1], cd[2], cd[3], cd[4], "en",
                 "text", "text", 10, f"n_{cd[0]}", now),
            )

        citations_data = [
            ("ci1", "c1", "https://ref-a.com", "primary", "p.5", 1),
            ("ci2", "c1", "https://ref-b.com", "secondary", "p.10", 0),
            ("ci3", "c2", "https://ref-a.com", "primary", "p.15", 1),
            ("ci4", "c4", "https://ref-c.com", "primary", "ch.3", 0),
        ]
        for cit in citations_data:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, target_uri, "
                "tag, locator, verified) VALUES (?, ?, ?, ?, ?, ?)",
                cit,
            )
        conn.commit()

        # 1: top cited targets
        tt = top_cited_targets(conn, top_n=10)
        assert len(tt) == 3
        assert tt[0]["target_uri"] == "https://ref-a.com"
        assert tt[0]["citation_count"] == 2
        checks += 1

        # 2: chunk count for top target
        assert tt[0]["chunk_count"] == 2
        assert tt[0]["verified_count"] == 2
        checks += 1

        # 3: top_n limit
        tt2 = top_cited_targets(conn, top_n=1)
        assert len(tt2) == 1
        checks += 1

        # 4: citation coverage
        cov = citation_coverage(conn)
        assert cov["total_claims"] == 4
        assert cov["cited_claims"] == 3
        checks += 1

        # 5: per-source coverage
        s1_cov = [s for s in cov["sources"] if s["source_id"] == "s1"][0]
        assert s1_cov["claim_count"] == 3
        assert s1_cov["cited_count"] == 2
        checks += 1

        # 6: s2 coverage
        s2_cov = [s for s in cov["sources"] if s["source_id"] == "s2"][0]
        assert s2_cov["claim_count"] == 1
        assert s2_cov["cited_count"] == 1
        checks += 1

        # 7: verification summary
        vs = verification_summary(conn)
        assert vs["total"] == 4
        assert vs["verified"] == 2
        assert vs["unverified"] == 2
        assert vs["rate"] == 0.5
        checks += 1

        # 8: verification by tag
        assert "primary" in vs["by_tag"]
        assert vs["by_tag"]["primary"]["total"] == 3
        assert vs["by_tag"]["primary"]["verified"] == 2
        checks += 1

        # 9: uncited claims
        uc = uncited_claims(conn, limit=50)
        uncited_ids = {u["chunk_id"] for u in uc}
        assert "c3" in uncited_ids
        checks += 1

        # 10: cited chunks not in uncited
        assert "c1" not in uncited_ids
        assert "c2" not in uncited_ids
        checks += 1

        # 11: prose chunks not in uncited claims
        assert "c5" not in uncited_ids
        checks += 1

        # 12: JSON serialisable
        _ = json.dumps(tt)
        _ = json.dumps(cov)
        _ = json.dumps(vs)
        _ = json.dumps(uc)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert top_cited_targets(conn2) == []
        cov2 = citation_coverage(conn2)
        assert cov2["total_claims"] == 0
        vs2 = verification_summary(conn2)
        assert vs2["total"] == 0
        uc2 = uncited_claims(conn2)
        assert uc2 == []
        checks += 1

        # 14: coverage rate calculation
        assert cov["coverage_rate"] == 0.75
        checks += 1

    print(f"PASS citation_analysis selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation analysis: patterns in chunk citations"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_tt = sub.add_parser("top-targets",
                          help="Most cited target URIs")
    p_tt.add_argument("--db", default=DEFAULT_DB)
    p_tt.add_argument("--top", type=int, default=20)
    p_tt.add_argument("--json", action="store_true")

    p_cov = sub.add_parser("coverage",
                           help="Per-source citation coverage")
    p_cov.add_argument("--db", default=DEFAULT_DB)
    p_cov.add_argument("--json", action="store_true")

    p_ver = sub.add_parser("verification",
                           help="Citation verification rates")
    p_ver.add_argument("--db", default=DEFAULT_DB)
    p_ver.add_argument("--json", action="store_true")

    p_uc = sub.add_parser("uncited-claims",
                          help="Accepted claims with no citations")
    p_uc.add_argument("--db", default=DEFAULT_DB)
    p_uc.add_argument("--limit", type=int, default=50)
    p_uc.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "top-targets":
        result = top_cited_targets(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Top cited targets: {len(result)}")
            for r in result:
                v = f", {r['verified_count']} verified" if r["verified_count"] else ""
                print(f"  {r['target_uri']}: {r['citation_count']} citations "
                      f"from {r['chunk_count']} chunks{v}")

    elif args.cmd == "coverage":
        result = citation_coverage(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citation coverage: {result['cited_claims']}/"
                  f"{result['total_claims']} claims cited "
                  f"({result['coverage_rate']:.1%})")
            for s in result["sources"]:
                print(f"  {s['source_id']}: {s['cited_count']}/"
                      f"{s['claim_count']} ({s['coverage']:.1%})")

    elif args.cmd == "verification":
        result = verification_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Citations: {result['total']} total, "
                  f"{result['verified']} verified ({result['rate']:.1%})")
            for tag, stats in sorted(result["by_tag"].items()):
                print(f"  {tag}: {stats['verified']}/{stats['total']} "
                      f"({stats['rate']:.1%})")

    elif args.cmd == "uncited-claims":
        result = uncited_claims(conn, limit=args.limit)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Uncited accepted claims: {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['heading_path']} "
                      f"({r['word_count']} words)")

    conn.close()


if __name__ == "__main__":
    main()
