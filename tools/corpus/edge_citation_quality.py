#!/usr/bin/env python3
"""Edge citation quality: per-edge citation backing at both endpoints.

No tool joins claim_edges with citations via their shared chunk_id on
chunks to show whether each edge endpoint is citation-backed.  A
"supports" edge between two well-cited chunks is more trustworthy than
one between chunks with zero citations.  health_scorecard.py counts
citations and edges separately; corpus_audit.py finds unverified
citations but never correlates them with edge endpoints.

Usage:
    python tools/corpus/edge_citation_quality.py by-edge [--db PATH] [--json]
    python tools/corpus/edge_citation_quality.py unbacked [--db PATH] [--json]
    python tools/corpus/edge_citation_quality.py quality-distribution [--db PATH] [--json]
    python tools/corpus/edge_citation_quality.py summary [--db PATH] [--json]
    python tools/corpus/edge_citation_quality.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_with_citation_quality(conn) -> list[dict]:
    """Per-edge citation quality at both endpoints."""
    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  e.source_chunk, e.target_chunk, "
        "  count(DISTINCT cs.citation_id) AS src_total, "
        "  count(DISTINCT CASE WHEN cs.verified = 1 "
        "    THEN cs.citation_id END) AS src_verified, "
        "  count(DISTINCT ct.citation_id) AS tgt_total, "
        "  count(DISTINCT CASE WHEN ct.verified = 1 "
        "    THEN ct.citation_id END) AS tgt_verified "
        "FROM claim_edges e "
        "LEFT JOIN citations cs ON e.source_chunk = cs.chunk_id "
        "LEFT JOIN citations ct ON e.target_chunk = ct.chunk_id "
        "GROUP BY e.edge_id "
        "ORDER BY e.edge_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for (eid, etype, conf, src, tgt,
         src_total, src_ver, tgt_total, tgt_ver) in rows:
        both_backed = src_total > 0 and tgt_total > 0
        both_verified = src_ver > 0 and tgt_ver > 0
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "source_chunk": src,
            "target_chunk": tgt,
            "source_citations": src_total,
            "source_verified": src_ver,
            "target_citations": tgt_total,
            "target_verified": tgt_ver,
            "both_backed": both_backed,
            "both_verified": both_verified,
        })

    return results


def unbacked_edges(conn) -> list[dict]:
    """Edges where at least one endpoint has zero citations."""
    ecq = edges_with_citation_quality(conn)
    return [e for e in ecq if not e["both_backed"]]


def quality_distribution(conn) -> list[dict]:
    """Distribution of edges by citation-quality tier."""
    ecq = edges_with_citation_quality(conn)
    if not ecq:
        return []

    tiers = {
        "both_verified": 0,
        "both_backed_partial_verified": 0,
        "both_backed_none_verified": 0,
        "one_backed": 0,
        "neither_backed": 0,
    }

    for e in ecq:
        sb = e["source_citations"] > 0
        tb = e["target_citations"] > 0
        sv = e["source_verified"] > 0
        tv = e["target_verified"] > 0

        if sb and tb and sv and tv:
            tiers["both_verified"] += 1
        elif sb and tb and (sv or tv):
            tiers["both_backed_partial_verified"] += 1
        elif sb and tb:
            tiers["both_backed_none_verified"] += 1
        elif sb or tb:
            tiers["one_backed"] += 1
        else:
            tiers["neither_backed"] += 1

    total = len(ecq)
    results = []
    for tier, count in tiers.items():
        rate = round(count / total, 4) if total > 0 else 0.0
        results.append({
            "tier": tier,
            "count": count,
            "rate": rate,
        })

    return results


def edge_citation_summary(conn) -> dict:
    """Aggregate edge-citation quality statistics."""
    ecq = edges_with_citation_quality(conn)

    if not ecq:
        return {
            "total_edges": 0,
            "both_backed": 0,
            "both_verified": 0,
            "unbacked_edges": 0,
            "backing_rate": 0.0,
            "verification_rate": 0.0,
            "mean_source_citations": 0.0,
            "mean_target_citations": 0.0,
        }

    total = len(ecq)
    bb = sum(1 for e in ecq if e["both_backed"])
    bv = sum(1 for e in ecq if e["both_verified"])
    ub = sum(1 for e in ecq if not e["both_backed"])
    mean_src = round(
        sum(e["source_citations"] for e in ecq) / total, 2
    )
    mean_tgt = round(
        sum(e["target_citations"] for e in ecq) / total, 2
    )

    return {
        "total_edges": total,
        "both_backed": bb,
        "both_verified": bv,
        "unbacked_edges": ub,
        "backing_rate": round(bb / total, 4) if total > 0 else 0.0,
        "verification_rate": (
            round(bv / total, 4) if total > 0 else 0.0
        ),
        "mean_source_citations": mean_src,
        "mean_target_citations": mean_tgt,
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"
        later = "2026-06-15T00:00:00Z"

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, "
            "title, license_spdx, license_verdict, license_evidence, "
            "publisher, published_utc, fetched_utc, upstream_rev, "
            "upstream_mtime, liveness, content_sha256, bytes, "
            "supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"c{i+1}", "s1", i, f"/h/c{i+1}", "claim", "en",
                 f"text c{i+1}", f"text c{i+1}", 10,
                 f"sha_c{i+1}", 0, 0, "accepted", now),
            )

        # Citations:
        # c1: 2 citations (both verified)
        # c2: 1 citation (unverified)
        # c3: 0 citations
        # c4: 1 citation (verified)
        cits = [
            ("ci1", "c1", "https://r1.com", None, "url",
             None, 1, later),
            ("ci2", "c1", "https://r2.com", None, "doi",
             None, 1, later),
            ("ci3", "c2", "https://r3.com", None, "url",
             None, 0, None),
            ("ci4", "c4", "https://r4.com", None, "doi",
             None, 1, later),
        ]
        for c in cits:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", c,
            )

        # Edges:
        # e1: c1 supports c2 (both backed, src verified, tgt not)
        # e2: c1 contradicts c3 (src backed+verified, tgt unbacked)
        # e3: c2 refines c4 (both backed, src unverified, tgt verified)
        # e4: c3 duplicates c4 (src unbacked, tgt backed+verified)
        edges = [
            ("e1", "c1", "c2", "supports", "text match", 0.9, now),
            ("e2", "c1", "c3", "contradicts", "semantic", 0.7, now),
            ("e3", "c2", "c4", "refines", "version", 0.85, now),
            ("e4", "c3", "c4", "duplicates", "simhash", 0.95, now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        conn.commit()

        # 1: edges_with_citation_quality returns 4 edges
        ecq = edges_with_citation_quality(conn)
        assert len(ecq) == 4
        checks += 1

        # 2: e1 source (c1) has 2 citations, 2 verified
        e1 = next(e for e in ecq if e["edge_id"] == "e1")
        assert e1["source_citations"] == 2
        assert e1["source_verified"] == 2
        checks += 1

        # 3: e1 target (c2) has 1 citation, 0 verified
        assert e1["target_citations"] == 1
        assert e1["target_verified"] == 0
        checks += 1

        # 4: e1 is both_backed but not both_verified
        assert e1["both_backed"] is True
        assert e1["both_verified"] is False
        checks += 1

        # 5: e2 target (c3) has 0 citations -- unbacked
        e2 = next(e for e in ecq if e["edge_id"] == "e2")
        assert e2["target_citations"] == 0
        assert e2["both_backed"] is False
        checks += 1

        # 6: e4 source (c3) unbacked, target (c4) backed
        e4 = next(e for e in ecq if e["edge_id"] == "e4")
        assert e4["source_citations"] == 0
        assert e4["target_citations"] == 1
        assert e4["both_backed"] is False
        checks += 1

        # 7: unbacked_edges returns e2 and e4
        ub = unbacked_edges(conn)
        ub_ids = {e["edge_id"] for e in ub}
        assert ub_ids == {"e2", "e4"}
        checks += 1

        # 8: quality_distribution tiers
        qd = quality_distribution(conn)
        tier_map = {t["tier"]: t["count"] for t in qd}
        assert tier_map["both_verified"] == 0
        assert tier_map["both_backed_partial_verified"] == 2
        assert tier_map["one_backed"] == 2
        assert tier_map["neither_backed"] == 0
        checks += 1

        # 9: quality_distribution rates sum to 1
        rate_sum = sum(t["rate"] for t in qd)
        assert abs(rate_sum - 1.0) < 0.01
        checks += 1

        # 10: summary totals
        summary = edge_citation_summary(conn)
        assert summary["total_edges"] == 4
        assert summary["both_backed"] == 2
        assert summary["unbacked_edges"] == 2
        checks += 1

        # 11: summary backing rate = 2/4 = 0.5
        assert abs(summary["backing_rate"] - 0.5) < 0.001
        checks += 1

        # 12: summary mean_source_citations = (2+2+1+0)/4 = 1.25
        assert abs(summary["mean_source_citations"] - 1.25) < 0.01
        checks += 1

        # 13: summary mean_target_citations = (1+0+1+1)/4 = 0.75
        assert abs(summary["mean_target_citations"] - 0.75) < 0.01
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(ecq)
        _ = json.dumps(ub)
        _ = json.dumps(qd)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = edges_with_citation_quality(conn2)
        assert empty == []
        empty_summary = edge_citation_summary(conn2)
        assert empty_summary["total_edges"] == 0
        checks += 1

    print(
        f"PASS edge_citation_quality selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge citation quality analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_be = sub.add_parser("by-edge",
                          help="Citation quality per edge")
    p_be.add_argument("--db", default=DEFAULT_DB)
    p_be.add_argument("--json", action="store_true")

    p_ub = sub.add_parser("unbacked",
                           help="Edges with unbacked endpoints")
    p_ub.add_argument("--db", default=DEFAULT_DB)
    p_ub.add_argument("--json", action="store_true")

    p_qd = sub.add_parser("quality-distribution",
                           help="Edge quality tier distribution")
    p_qd.add_argument("--db", default=DEFAULT_DB)
    p_qd.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Edge citation quality statistics")
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

    if args.cmd == "by-edge":
        results = edges_with_citation_quality(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                backed = "Y" if r["both_backed"] else "N"
                verif = "Y" if r["both_verified"] else "N"
                print(f"  {r['edge_id']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"conf={r['confidence']:.2f}  "
                      f"src_cites={r['source_citations']}/"
                      f"{r['source_verified']}  "
                      f"tgt_cites={r['target_citations']}/"
                      f"{r['target_verified']}  "
                      f"backed={backed}  verif={verif}")

    elif args.cmd == "unbacked":
        results = unbacked_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_id']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"src={r['source_citations']}  "
                      f"tgt={r['target_citations']}")

    elif args.cmd == "quality-distribution":
        results = quality_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['tier']:36s}  "
                      f"n={r['count']:3d}  "
                      f"rate={r['rate']:.3f}")

    elif args.cmd == "summary":
        result = edge_citation_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total_edges']}  "
                  f"Both backed: {result['both_backed']}  "
                  f"Both verified: {result['both_verified']}  "
                  f"Unbacked: {result['unbacked_edges']}")
            print(f"  Backing rate: "
                  f"{result['backing_rate']:.3f}  "
                  f"Verification rate: "
                  f"{result['verification_rate']:.3f}")
            print(f"  Mean src cites: "
                  f"{result['mean_source_citations']:.1f}  "
                  f"Mean tgt cites: "
                  f"{result['mean_target_citations']:.1f}")

    conn.close()


if __name__ == "__main__":
    main()
