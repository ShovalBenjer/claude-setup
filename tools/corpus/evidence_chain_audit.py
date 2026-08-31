#!/usr/bin/env python3
"""Evidence chain audit: end-to-end provenance across sources, chunks, citations, artifacts.

edge_citation_quality.py checks citation quality on claim_edges.
artifact_citation_provenance.py checks citation backing on artifacts.
Neither audits the full chain from source through chunk to both
citations and artifacts in a single pass.  Understanding which chunks
lack any external evidence (no citations AND no artifact evidence_path)
required separate queries against each table.

Usage:
    python tools/corpus/evidence_chain_audit.py unattested [--db PATH] [--json]
    python tools/corpus/evidence_chain_audit.py by-source [--db PATH] [--json]
    python tools/corpus/evidence_chain_audit.py by-kind [--db PATH] [--json]
    python tools/corpus/evidence_chain_audit.py summary [--db PATH] [--json]
    python tools/corpus/evidence_chain_audit.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def unattested_chunks(conn) -> list[dict]:
    """Chunks with zero citations AND zero artifact evidence_paths."""
    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, c.status, "
        "  c.word_count, c.heading_path, "
        "  s.title AS source_title, s.kind AS source_kind "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "LEFT JOIN citations ci ON c.chunk_id = ci.chunk_id "
        "LEFT JOIN artifacts a ON c.chunk_id = a.chunk_id "
        "  AND a.evidence_path IS NOT NULL "
        "WHERE ci.citation_id IS NULL "
        "  AND a.artifact_id IS NULL "
        "ORDER BY c.source_id, c.ordinal"
    ).fetchall()

    results = []
    for (cid, sid, kind, status, wc, hp,
         stitle, skind) in rows:
        results.append({
            "chunk_id": cid,
            "source_id": sid,
            "chunk_kind": kind,
            "status": status,
            "word_count": wc,
            "heading_path": hp,
            "source_title": stitle,
            "source_kind": skind,
        })

    return results


def evidence_by_source(conn) -> list[dict]:
    """Per-source evidence chain statistics."""
    rows = conn.execute(
        "SELECT s.source_id, s.title, s.kind, "
        "  count(DISTINCT c.chunk_id) AS total_chunks, "
        "  count(DISTINCT ci.citation_id) AS total_citations, "
        "  count(DISTINCT CASE WHEN a.evidence_path IS NOT NULL "
        "    THEN a.artifact_id END) AS evidenced_artifacts "
        "FROM sources s "
        "LEFT JOIN chunks c ON s.source_id = c.source_id "
        "LEFT JOIN citations ci ON c.chunk_id = ci.chunk_id "
        "LEFT JOIN artifacts a ON c.chunk_id = a.chunk_id "
        "GROUP BY s.source_id "
        "ORDER BY total_chunks DESC"
    ).fetchall()

    results = []
    for (sid, title, kind, tc, tci, ea) in rows:
        results.append({
            "source_id": sid,
            "title": title,
            "source_kind": kind,
            "total_chunks": tc,
            "total_citations": tci,
            "evidenced_artifacts": ea,
            "citations_per_chunk": (
                round(tci / tc, 2) if tc > 0 else 0.0
            ),
        })

    return results


def evidence_by_kind(conn) -> list[dict]:
    """Evidence chain statistics per chunk kind."""
    rows = conn.execute(
        "SELECT c.kind, "
        "  count(DISTINCT c.chunk_id) AS total_chunks, "
        "  count(DISTINCT ci.citation_id) AS total_citations, "
        "  count(DISTINCT CASE WHEN ci.verified = 1 "
        "    THEN ci.citation_id END) AS verified_citations, "
        "  count(DISTINCT CASE WHEN a.evidence_path IS NOT NULL "
        "    THEN a.artifact_id END) AS evidenced_artifacts "
        "FROM chunks c "
        "LEFT JOIN citations ci ON c.chunk_id = ci.chunk_id "
        "LEFT JOIN artifacts a ON c.chunk_id = a.chunk_id "
        "GROUP BY c.kind "
        "ORDER BY total_chunks DESC"
    ).fetchall()

    results = []
    for (kind, tc, tci, vci, ea) in rows:
        results.append({
            "chunk_kind": kind,
            "total_chunks": tc,
            "total_citations": tci,
            "verified_citations": vci,
            "evidenced_artifacts": ea,
            "citation_rate": (
                round(tci / tc, 2) if tc > 0 else 0.0
            ),
        })

    return results


def evidence_chain_summary(conn) -> dict:
    """Aggregate evidence chain statistics."""
    total_chunks = conn.execute(
        "SELECT count(*) FROM chunks"
    ).fetchone()[0]

    if total_chunks == 0:
        return {
            "total_chunks": 0,
            "total_citations": 0,
            "total_artifacts": 0,
            "unattested_chunks": 0,
            "unattested_rate": 0.0,
            "verified_citations": 0,
            "verification_rate": 0.0,
            "evidenced_artifacts": 0,
            "evidence_rate": 0.0,
            "weakest_kind": None,
            "strongest_kind": None,
        }

    total_citations = conn.execute(
        "SELECT count(*) FROM citations"
    ).fetchone()[0]

    verified_citations = conn.execute(
        "SELECT count(*) FROM citations WHERE verified = 1"
    ).fetchone()[0]

    total_artifacts = conn.execute(
        "SELECT count(*) FROM artifacts"
    ).fetchone()[0]

    evidenced_artifacts = conn.execute(
        "SELECT count(*) FROM artifacts "
        "WHERE evidence_path IS NOT NULL"
    ).fetchone()[0]

    unattested = unattested_chunks(conn)
    unattested_count = len(unattested)

    by_kind = evidence_by_kind(conn)
    weakest = min(by_kind, key=lambda k: k["citation_rate"]) if by_kind else None
    strongest = max(by_kind, key=lambda k: k["citation_rate"]) if by_kind else None

    return {
        "total_chunks": total_chunks,
        "total_citations": total_citations,
        "total_artifacts": total_artifacts,
        "unattested_chunks": unattested_count,
        "unattested_rate": round(
            unattested_count / total_chunks, 4
        ) if total_chunks > 0 else 0.0,
        "verified_citations": verified_citations,
        "verification_rate": round(
            verified_citations / total_citations, 4
        ) if total_citations > 0 else 0.0,
        "evidenced_artifacts": evidenced_artifacts,
        "evidence_rate": round(
            evidenced_artifacts / total_artifacts, 4
        ) if total_artifacts > 0 else 0.0,
        "weakest_kind": (
            weakest["chunk_kind"] if weakest else None
        ),
        "strongest_kind": (
            strongest["chunk_kind"] if strongest else None
        ),
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        for i in range(2):
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"s{i+1}", f"https://s{i+1}.com",
                 "paper", f"Source {i+1}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_s{i+1}", 1000, None),
            )

        # 6 chunks across 2 sources, different kinds
        chunk_data = [
            ("c1", "s1", 0, "claim", 20),
            ("c2", "s1", 1, "code", 15),
            ("c3", "s1", 2, "claim", 30),
            ("c4", "s2", 0, "table", 25),
            ("c5", "s2", 1, "claim", 10),
            ("c6", "s2", 2, "code", 18),
        ]
        for cid, sid, o, kind, wc in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, o, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", wc,
                 f"sha_{cid}", 0, 0, "accepted", now),
            )

        # Citations:
        # c1: 2 citations (1 verified)
        # c2: 1 citation (unverified)
        # c3: 0 citations
        # c4: 1 citation (verified)
        # c5: 0 citations
        # c6: 0 citations
        citations = [
            ("ci1", "c1", "https://ref1.com", None, None, None, 1, now),
            ("ci2", "c1", "https://ref2.com", None, None, None, 0, None),
            ("ci3", "c2", "https://ref3.com", None, None, None, 0, None),
            ("ci4", "c4", "https://ref4.com", None, None, None, 1, now),
        ]
        for ci in citations:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", ci,
            )

        # Artifacts:
        # c1: library torch (with evidence_path)
        # c3: api openai (no evidence_path)
        # c5: command curl (with evidence_path)
        # c6: pattern retry (no evidence_path)
        artifacts = [
            ("a1", "c1", "library", "torch", "2.0", None, 1,
             "tools/test.py"),
            ("a2", "c3", "api", "openai", "1.0", None, 0, None),
            ("a3", "c5", "command", "curl", None, None, 1,
             "scripts/fetch.sh"),
            ("a4", "c6", "pattern", "retry", None, None, 0, None),
        ]
        for a in artifacts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, "
                "implemented, evidence_path) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", a,
            )

        conn.commit()

        # 1: unattested_chunks returns chunks with no citations AND no evidenced artifacts
        # c3 has no citations but has artifact a2 (no evidence_path) -> unattested
        # c5 has no citations but has artifact a3 (with evidence_path) -> NOT unattested
        # c6 has no citations and artifact a4 (no evidence_path) -> unattested
        ua = unattested_chunks(conn)
        ua_ids = {c["chunk_id"] for c in ua}
        assert "c3" in ua_ids
        assert "c6" in ua_ids
        checks += 1

        # 2: c1 has citations, not unattested
        assert "c1" not in ua_ids
        checks += 1

        # 3: c5 has evidenced artifact, not unattested
        assert "c5" not in ua_ids
        checks += 1

        # 4: c2 has citation, not unattested
        assert "c2" not in ua_ids
        checks += 1

        # 5: evidence_by_source returns 2 sources
        bs = evidence_by_source(conn)
        assert len(bs) == 2
        checks += 1

        # 6: s1 has 3 chunks, 3 citations, 1 evidenced artifact
        s1 = next(s for s in bs if s["source_id"] == "s1")
        assert s1["total_chunks"] == 3
        assert s1["total_citations"] == 3
        assert s1["evidenced_artifacts"] == 1
        checks += 1

        # 7: s2 has 3 chunks, 1 citation, 1 evidenced artifact
        s2 = next(s for s in bs if s["source_id"] == "s2")
        assert s2["total_chunks"] == 3
        assert s2["total_citations"] == 1
        assert s2["evidenced_artifacts"] == 1
        checks += 1

        # 8: evidence_by_kind returns entries for claim, code, table
        bk = evidence_by_kind(conn)
        kinds = {k["chunk_kind"] for k in bk}
        assert kinds == {"claim", "code", "table"}
        checks += 1

        # 9: claim kind has 3 chunks, 2 citations
        claim_k = next(k for k in bk if k["chunk_kind"] == "claim")
        assert claim_k["total_chunks"] == 3
        assert claim_k["total_citations"] == 2
        checks += 1

        # 10: code kind has 2 chunks, 1 citation
        code_k = next(k for k in bk if k["chunk_kind"] == "code")
        assert code_k["total_chunks"] == 2
        assert code_k["total_citations"] == 1
        checks += 1

        # 11: summary totals
        summary = evidence_chain_summary(conn)
        assert summary["total_chunks"] == 6
        assert summary["total_citations"] == 4
        assert summary["total_artifacts"] == 4
        checks += 1

        # 12: unattested count and rate
        assert summary["unattested_chunks"] == 2
        assert summary["unattested_rate"] > 0
        checks += 1

        # 13: verification and evidence rates
        assert summary["verified_citations"] == 2
        assert summary["verification_rate"] == 0.5
        assert summary["evidenced_artifacts"] == 2
        assert summary["evidence_rate"] == 0.5
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(ua)
        _ = json.dumps(bs)
        _ = json.dumps(bk)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty_ua = unattested_chunks(conn2)
        assert empty_ua == []
        empty_summary = evidence_chain_summary(conn2)
        assert empty_summary["total_chunks"] == 0
        checks += 1

    print(
        f"PASS evidence_chain_audit selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence chain audit"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_ua = sub.add_parser("unattested",
                          help="Chunks with no evidence")
    p_ua.add_argument("--db", default=DEFAULT_DB)
    p_ua.add_argument("--json", action="store_true")

    p_bs = sub.add_parser("by-source",
                           help="Evidence per source")
    p_bs.add_argument("--db", default=DEFAULT_DB)
    p_bs.add_argument("--json", action="store_true")

    p_bk = sub.add_parser("by-kind",
                           help="Evidence per chunk kind")
    p_bk.add_argument("--db", default=DEFAULT_DB)
    p_bk.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Evidence chain statistics")
    p_sum.add_argument("--db", default=DEFAULT_DB)
    p_sum.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "unattested":
        results = unattested_chunks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No unattested chunks.")
            else:
                for r in results:
                    print(f"  {r['chunk_id']:12s}  "
                          f"{r['chunk_kind']:8s}  "
                          f"{r['status']:12s}  "
                          f"words={r['word_count']:4d}  "
                          f"src={r['source_id']}")

    elif args.cmd == "by-source":
        results = evidence_by_source(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_id']:12s}  "
                      f"chunks={r['total_chunks']:4d}  "
                      f"citations={r['total_citations']:4d}  "
                      f"evidenced={r['evidenced_artifacts']:3d}  "
                      f"cit/chunk="
                      f"{r['citations_per_chunk']:.1f}")

    elif args.cmd == "by-kind":
        results = evidence_by_kind(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['chunk_kind']:8s}  "
                      f"chunks={r['total_chunks']:4d}  "
                      f"citations={r['total_citations']:4d}  "
                      f"verified={r['verified_citations']:3d}  "
                      f"evidenced={r['evidenced_artifacts']:3d}  "
                      f"rate={r['citation_rate']:.2f}")

    elif args.cmd == "summary":
        result = evidence_chain_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chunks: {result['total_chunks']}  "
                  f"Citations: {result['total_citations']}  "
                  f"Artifacts: {result['total_artifacts']}")
            print(f"  Unattested: "
                  f"{result['unattested_chunks']} "
                  f"({result['unattested_rate']:.1%})")
            print(f"  Verified citations: "
                  f"{result['verified_citations']} "
                  f"({result['verification_rate']:.1%})")
            print(f"  Evidenced artifacts: "
                  f"{result['evidenced_artifacts']} "
                  f"({result['evidence_rate']:.1%})")
            if result["weakest_kind"]:
                print(f"  Weakest kind: "
                      f"{result['weakest_kind']}  "
                      f"Strongest: "
                      f"{result['strongest_kind']}")

    conn.close()


if __name__ == "__main__":
    main()
