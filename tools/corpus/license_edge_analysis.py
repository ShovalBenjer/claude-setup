#!/usr/bin/env python3
"""License edge analysis: claim edges stratified by source license verdict.

publisher_license_distribution.py analyses source licensing alone.
liveness_cross_analysis.py and source_provenance.py touch license_verdict
but never cross-reference with claim_edges.  No tool joins
sources.license_verdict with chunks and claim_edges to show how many
cross-license-boundary edges exist or whether blocked sources' chunks
participate in the claim network.

Usage:
    python tools/corpus/license_edge_analysis.py by-verdict [--db PATH] [--json]
    python tools/corpus/license_edge_analysis.py cross-boundary [--db PATH] [--json]
    python tools/corpus/license_edge_analysis.py blocked-edges [--db PATH] [--json]
    python tools/corpus/license_edge_analysis.py summary [--db PATH] [--json]
    python tools/corpus/license_edge_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_license_verdict(conn) -> list[dict]:
    """Edge counts per source/target license verdict pair."""
    rows = conn.execute(
        "SELECT ss.license_verdict AS src_verdict, "
        "  st.license_verdict AS tgt_verdict, "
        "  e.edge_type, "
        "  count(*) AS edge_count, "
        "  avg(e.confidence) AS mean_confidence "
        "FROM claim_edges e "
        "JOIN chunks cs ON e.source_chunk = cs.chunk_id "
        "JOIN chunks ct ON e.target_chunk = ct.chunk_id "
        "JOIN sources ss ON cs.source_id = ss.source_id "
        "JOIN sources st ON ct.source_id = st.source_id "
        "GROUP BY src_verdict, tgt_verdict, e.edge_type "
        "ORDER BY src_verdict, tgt_verdict, e.edge_type"
    ).fetchall()

    if not rows:
        return []

    results = []
    for src_v, tgt_v, etype, count, mean_conf in rows:
        results.append({
            "source_verdict": src_v,
            "target_verdict": tgt_v,
            "edge_type": etype,
            "edge_count": count,
            "mean_confidence": round(mean_conf, 4),
            "cross_boundary": src_v != tgt_v,
        })

    return results


def cross_boundary_edges(conn) -> list[dict]:
    """Edges where source and target have different license verdicts."""
    all_edges = edges_by_license_verdict(conn)
    return [e for e in all_edges if e["cross_boundary"]]


def blocked_source_edges(conn) -> list[dict]:
    """Edges involving at least one blocked source."""
    rows = conn.execute(
        "SELECT e.edge_id, e.edge_type, e.confidence, "
        "  e.source_chunk, e.target_chunk, "
        "  ss.license_verdict AS src_verdict, "
        "  st.license_verdict AS tgt_verdict "
        "FROM claim_edges e "
        "JOIN chunks cs ON e.source_chunk = cs.chunk_id "
        "JOIN chunks ct ON e.target_chunk = ct.chunk_id "
        "JOIN sources ss ON cs.source_id = ss.source_id "
        "JOIN sources st ON ct.source_id = st.source_id "
        "WHERE ss.license_verdict = 'blocked' "
        "   OR st.license_verdict = 'blocked' "
        "ORDER BY e.edge_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for (eid, etype, conf, src, tgt,
         src_v, tgt_v) in rows:
        results.append({
            "edge_id": eid,
            "edge_type": etype,
            "confidence": conf,
            "source_chunk": src,
            "target_chunk": tgt,
            "source_verdict": src_v,
            "target_verdict": tgt_v,
            "source_blocked": src_v == "blocked",
            "target_blocked": tgt_v == "blocked",
        })

    return results


def license_edge_summary(conn) -> dict:
    """Aggregate license-edge statistics."""
    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    by_v = edges_by_license_verdict(conn)

    if not by_v:
        return {
            "total_edges": total_edges,
            "cross_boundary_edges": 0,
            "cross_boundary_rate": 0.0,
            "blocked_edges": 0,
            "blocked_rate": 0.0,
            "verdict_pairs": 0,
            "dominant_pair": None,
        }

    cross = sum(e["edge_count"] for e in by_v if e["cross_boundary"])
    classified = sum(e["edge_count"] for e in by_v)

    blocked = blocked_source_edges(conn)
    blocked_count = len(blocked)

    pair_totals: dict[tuple[str, str], int] = {}
    for e in by_v:
        key = (e["source_verdict"], e["target_verdict"])
        pair_totals[key] = pair_totals.get(key, 0) + e["edge_count"]

    dominant = max(pair_totals, key=pair_totals.get)

    return {
        "total_edges": total_edges,
        "cross_boundary_edges": cross,
        "cross_boundary_rate": (
            round(cross / classified, 4)
            if classified > 0 else 0.0
        ),
        "blocked_edges": blocked_count,
        "blocked_rate": (
            round(blocked_count / total_edges, 4)
            if total_edges > 0 else 0.0
        ),
        "verdict_pairs": len(pair_totals),
        "dominant_pair": f"{dominant[0]}->{dominant[1]}",
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        # s1: vendor, s2: blocked, s3: index_only
        sources = [
            ("s1", "https://s1.com", "vendor"),
            ("s2", "https://s2.com", "blocked"),
            ("s3", "https://s3.com", "index_only"),
        ]
        for sid, uri, verdict in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, "
                "license_evidence, publisher, published_utc, "
                "fetched_utc, upstream_rev, upstream_mtime, liveness, "
                "content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", verdict, "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        # c1,c2 from s1; c3,c4 from s2; c5 from s3
        chunks = [
            ("c1", "s1", 0), ("c2", "s1", 1),
            ("c3", "s2", 0), ("c4", "s2", 1),
            ("c5", "s3", 0),
        ]
        for cid, sid, ordinal in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", "claim", "en",
                 f"text {cid}", f"text {cid}", 10,
                 f"sha_{cid}", 0, 0, "accepted", now),
            )

        # Edges:
        # e1: c1(vendor) -> c2(vendor) = same boundary
        # e2: c1(vendor) -> c3(blocked) = cross boundary + blocked
        # e3: c3(blocked) -> c4(blocked) = same boundary + blocked
        # e4: c5(index_only) -> c1(vendor) = cross boundary
        # e5: c3(blocked) -> c5(index_only) = cross + blocked
        edges = [
            ("e1", "c1", "c2", "supports", "text", 0.9, now),
            ("e2", "c1", "c3", "contradicts", "semantic", 0.7, now),
            ("e3", "c3", "c4", "duplicates", "simhash", 0.95, now),
            ("e4", "c5", "c1", "supports", "text", 0.8, now),
            ("e5", "c3", "c5", "refines", "version", 0.6, now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        conn.commit()

        # 1: edges_by_license_verdict returns entries
        by_v = edges_by_license_verdict(conn)
        assert len(by_v) > 0
        checks += 1

        # 2: vendor->vendor pair exists with 1 edge
        vv = [e for e in by_v
              if e["source_verdict"] == "vendor"
              and e["target_verdict"] == "vendor"]
        assert sum(e["edge_count"] for e in vv) == 1
        checks += 1

        # 3: blocked->blocked pair exists with 1 edge
        bb = [e for e in by_v
              if e["source_verdict"] == "blocked"
              and e["target_verdict"] == "blocked"]
        assert sum(e["edge_count"] for e in bb) == 1
        checks += 1

        # 4: cross_boundary entries have cross_boundary=True
        cross = cross_boundary_edges(conn)
        assert all(e["cross_boundary"] for e in cross)
        assert len(cross) > 0
        checks += 1

        # 5: 3 cross-boundary edges (e2, e4, e5)
        cross_total = sum(e["edge_count"] for e in cross)
        assert cross_total == 3
        checks += 1

        # 6: blocked_source_edges returns 3 (e2, e3, e5)
        blocked = blocked_source_edges(conn)
        assert len(blocked) == 3
        blocked_ids = {e["edge_id"] for e in blocked}
        assert blocked_ids == {"e2", "e3", "e5"}
        checks += 1

        # 7: e2 has source_blocked=False, target_blocked=True
        e2 = next(e for e in blocked if e["edge_id"] == "e2")
        assert e2["source_blocked"] is False
        assert e2["target_blocked"] is True
        checks += 1

        # 8: e3 has both blocked
        e3 = next(e for e in blocked if e["edge_id"] == "e3")
        assert e3["source_blocked"] is True
        assert e3["target_blocked"] is True
        checks += 1

        # 9: e5 has source_blocked=True, target_blocked=False
        e5 = next(e for e in blocked if e["edge_id"] == "e5")
        assert e5["source_blocked"] is True
        assert e5["target_blocked"] is False
        checks += 1

        # 10: summary totals
        summary = license_edge_summary(conn)
        assert summary["total_edges"] == 5
        assert summary["cross_boundary_edges"] == 3
        checks += 1

        # 11: cross_boundary_rate = 3/5 = 0.6
        assert abs(summary["cross_boundary_rate"] - 0.6) < 0.001
        checks += 1

        # 12: blocked_edges = 3
        assert summary["blocked_edges"] == 3
        assert abs(summary["blocked_rate"] - 0.6) < 0.001
        checks += 1

        # 13: dominant_pair exists
        assert summary["dominant_pair"] is not None
        assert summary["verdict_pairs"] > 0
        checks += 1

        # 14: JSON serialisable + empty corpus
        _ = json.dumps(by_v)
        _ = json.dumps(cross)
        _ = json.dumps(blocked)
        _ = json.dumps(summary)
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = edges_by_license_verdict(conn2)
        assert empty == []
        empty_summary = license_edge_summary(conn2)
        assert empty_summary["total_edges"] == 0
        checks += 1

    print(
        f"PASS license_edge_analysis selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="License-stratified edge analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_bv = sub.add_parser("by-verdict",
                          help="Edge counts per verdict pair")
    p_bv.add_argument("--db", default=DEFAULT_DB)
    p_bv.add_argument("--json", action="store_true")

    p_cb = sub.add_parser("cross-boundary",
                           help="Cross-license-boundary edges")
    p_cb.add_argument("--db", default=DEFAULT_DB)
    p_cb.add_argument("--json", action="store_true")

    p_bl = sub.add_parser("blocked-edges",
                           help="Edges involving blocked sources")
    p_bl.add_argument("--db", default=DEFAULT_DB)
    p_bl.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="License edge statistics")
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

    if args.cmd == "by-verdict":
        results = edges_by_license_verdict(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                cross = "X" if r["cross_boundary"] else " "
                print(f"  {r['source_verdict']:12s} -> "
                      f"{r['target_verdict']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"n={r['edge_count']:3d}  "
                      f"conf={r['mean_confidence']:.3f}  "
                      f"[{cross}]")

    elif args.cmd == "cross-boundary":
        results = cross_boundary_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_verdict']:12s} -> "
                      f"{r['target_verdict']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"n={r['edge_count']:3d}")

    elif args.cmd == "blocked-edges":
        results = blocked_source_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                sb = "Y" if r["source_blocked"] else "N"
                tb = "Y" if r["target_blocked"] else "N"
                print(f"  {r['edge_id']:12s}  "
                      f"{r['edge_type']:12s}  "
                      f"src_blk={sb}  tgt_blk={tb}  "
                      f"conf={r['confidence']:.2f}")

    elif args.cmd == "summary":
        result = license_edge_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total_edges']}  "
                  f"Cross-boundary: "
                  f"{result['cross_boundary_edges']}  "
                  f"Rate: {result['cross_boundary_rate']:.3f}")
            print(f"  Blocked: {result['blocked_edges']}  "
                  f"Rate: {result['blocked_rate']:.3f}  "
                  f"Pairs: {result['verdict_pairs']}")
            if result["dominant_pair"]:
                print(f"  Dominant: {result['dominant_pair']}")

    conn.close()


if __name__ == "__main__":
    main()
