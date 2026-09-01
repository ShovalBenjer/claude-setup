#!/usr/bin/env python3
"""Claim consensus analyzer: cross-source agreement on claims.

Measures how many independent sources support, contradict, or refine
each claim through claim_edges, producing per-claim consensus scores
and corpus-wide agreement statistics.

Usage:
    python tools/corpus/claim_consensus.py consensus [--db PATH] [--top N] [--json]
    python tools/corpus/claim_consensus.py contested [--db PATH] [--json]
    python tools/corpus/claim_consensus.py summary [--db PATH] [--json]
    python tools/corpus/claim_consensus.py selftest
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


def claim_consensus(conn) -> list[dict]:
    """Per-claim consensus from cross-source edges.

    For each chunk that is a target of claim_edges, counts how many
    distinct sources support it vs. contradict it.  The consensus score
    is (supports - contradicts) / total_edges, ranging from -1 (all
    contradict) to +1 (all support).
    """
    rows = conn.execute(
        "SELECT e.target_chunk, e.edge_type, e.confidence, "
        "cs.source_id AS src_source, ct.source_id AS tgt_source, "
        "ct.heading_path, ct.kind "
        "FROM claim_edges e "
        "JOIN chunks cs ON e.source_chunk = cs.chunk_id "
        "JOIN chunks ct ON e.target_chunk = ct.chunk_id "
        "WHERE ct.status != 'superseded'"
    ).fetchall()

    if not rows:
        return []

    claims: dict[str, dict] = {}
    for target_id, edge_type, confidence, src_source, tgt_source, heading, kind in rows:
        if target_id not in claims:
            claims[target_id] = {
                "chunk_id": target_id,
                "heading": heading,
                "kind": kind,
                "supports": 0,
                "contradicts": 0,
                "refines": 0,
                "duplicates": 0,
                "supersedes": 0,
                "source_ids": set(),
                "cross_source_edges": 0,
                "total_confidence": 0.0,
            }

        c = claims[target_id]
        if edge_type in c:
            c[edge_type] += 1
        c["source_ids"].add(src_source)
        c["total_confidence"] += confidence
        if src_source != tgt_source:
            c["cross_source_edges"] += 1

    results = []
    for cid, c in claims.items():
        total = c["supports"] + c["contradicts"] + c["refines"] + c["duplicates"] + c["supersedes"]
        if total == 0:
            continue

        consensus = round(
            (c["supports"] - c["contradicts"]) / total, 4
        )
        avg_confidence = round(c["total_confidence"] / total, 4)

        results.append({
            "chunk_id": cid,
            "heading": c["heading"],
            "kind": c["kind"],
            "consensus_score": consensus,
            "supports": c["supports"],
            "contradicts": c["contradicts"],
            "refines": c["refines"],
            "duplicates": c["duplicates"],
            "supersedes": c["supersedes"],
            "total_edges": total,
            "distinct_sources": len(c["source_ids"]),
            "cross_source_edges": c["cross_source_edges"],
            "avg_confidence": avg_confidence,
        })

    results.sort(key=lambda r: r["consensus_score"])
    return results


def contested_claims(conn) -> list[dict]:
    """Claims with at least one contradiction edge."""
    all_claims = claim_consensus(conn)
    return [c for c in all_claims if c["contradicts"] > 0]


def consensus_summary(conn) -> dict:
    """Aggregate consensus statistics across the corpus."""
    claims = claim_consensus(conn)
    if not claims:
        return {
            "total_claims_with_edges": 0,
            "avg_consensus": 0.0,
            "contested_count": 0,
            "unanimous_support": 0,
            "cross_source_claims": 0,
            "edge_type_totals": {
                "supports": 0, "contradicts": 0, "refines": 0,
                "duplicates": 0, "supersedes": 0,
            },
        }

    scores = [c["consensus_score"] for c in claims]
    contested = sum(1 for c in claims if c["contradicts"] > 0)
    unanimous = sum(1 for c in claims
                    if c["consensus_score"] == 1.0 and c["supports"] > 0)
    cross_source = sum(1 for c in claims if c["cross_source_edges"] > 0)

    edge_totals = {
        "supports": sum(c["supports"] for c in claims),
        "contradicts": sum(c["contradicts"] for c in claims),
        "refines": sum(c["refines"] for c in claims),
        "duplicates": sum(c["duplicates"] for c in claims),
        "supersedes": sum(c["supersedes"] for c in claims),
    }

    return {
        "total_claims_with_edges": len(claims),
        "avg_consensus": round(sum(scores) / len(scores), 4),
        "contested_count": contested,
        "unanimous_support": unanimous,
        "cross_source_claims": cross_source,
        "edge_type_totals": edge_totals,
    }


# -- selftest ----------------------------------------------------------------


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

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com"),
                         ("s3", "https://c.com")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_data = [
            ("c1", "s1", 0, "Claim A"),
            ("c2", "s2", 0, "Claim B"),
            ("c3", "s3", 0, "Claim C"),
            ("c4", "s1", 1, "Superseded"),
            ("c5", "s2", 1, "Unlinked"),
        ]
        for cid, sid, ordinal, heading in chunk_data:
            status = "superseded" if cid == "c4" else "accepted"
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, ordinal, heading, "claim", "en",
                 "text", "text", 10, f"n_{cid}", status, now),
            )

        edges = [
            ("e1", "c2", "c1", "supports", 0.9),
            ("e2", "c3", "c1", "supports", 0.8),
            ("e3", "c3", "c2", "contradicts", 0.7),
            ("e4", "c1", "c2", "refines", 0.6),
            ("e5", "c2", "c3", "supports", 0.85),
            ("e6", "c1", "c3", "contradicts", 0.75),
        ]
        for eid, src, tgt, etype, conf in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
                "edge_type, basis, confidence, detected_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (eid, src, tgt, etype, "semantic", conf, now),
            )

        conn.commit()

        # 1: consensus computed for non-superseded target chunks
        results = claim_consensus(conn)
        ids = [r["chunk_id"] for r in results]
        assert "c4" not in ids
        assert "c5" not in ids
        checks += 1

        # 2: c1 has unanimous support (2 supports, 0 contradicts)
        c1 = [r for r in results if r["chunk_id"] == "c1"][0]
        assert c1["supports"] == 2
        assert c1["contradicts"] == 0
        assert c1["consensus_score"] == 1.0
        checks += 1

        # 3: c2 has mixed edges (1 contradicts, 1 refines)
        c2 = [r for r in results if r["chunk_id"] == "c2"][0]
        assert c2["contradicts"] == 1
        assert c2["refines"] == 1
        checks += 1

        # 4: consensus scores range from -1 to 1
        for r in results:
            assert -1.0 <= r["consensus_score"] <= 1.0
        checks += 1

        # 5: results sorted by consensus ascending (most contested first)
        scores = [r["consensus_score"] for r in results]
        assert scores == sorted(scores)
        checks += 1

        # 6: cross-source edges detected
        assert c1["cross_source_edges"] == 2
        checks += 1

        # 7: distinct sources counted
        assert c1["distinct_sources"] == 2
        checks += 1

        # 8: contested_claims filters correctly
        contested = contested_claims(conn)
        contested_ids = [c["chunk_id"] for c in contested]
        assert "c1" not in contested_ids
        assert "c2" in contested_ids
        checks += 1

        # 9: summary has required keys
        summary = consensus_summary(conn)
        assert summary["total_claims_with_edges"] == 3
        assert "avg_consensus" in summary
        assert "edge_type_totals" in summary
        checks += 1

        # 10: unanimous count
        assert summary["unanimous_support"] == 1
        checks += 1

        # 11: contested count
        assert summary["contested_count"] == 2
        checks += 1

        # 12: edge type totals sum correctly
        totals = summary["edge_type_totals"]
        assert totals["supports"] == 3
        assert totals["contradicts"] == 2
        assert totals["refines"] == 1
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(results)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = claim_consensus(conn2)
        assert empty == []
        empty_summary = consensus_summary(conn2)
        assert empty_summary["total_claims_with_edges"] == 0
        checks += 1

    print(f"PASS claim_consensus selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claim consensus: cross-source agreement analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_con = sub.add_parser("consensus",
                           help="Per-claim consensus scores")
    p_con.add_argument("--db", default=DEFAULT_DB)
    p_con.add_argument("--top", type=int, default=0,
                       help="Show only top N claims (0 = all)")
    p_con.add_argument("--json", action="store_true")

    p_cst = sub.add_parser("contested",
                           help="Claims with contradictions")
    p_cst.add_argument("--db", default=DEFAULT_DB)
    p_cst.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Aggregate consensus statistics")
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

    if args.cmd == "consensus":
        results = claim_consensus(conn)
        if args.top > 0:
            results = results[:args.top]
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                sign = "+" if r["consensus_score"] >= 0 else ""
                xs = f"x{r['cross_source_edges']}" if r["cross_source_edges"] else "  "
                print(f"  {sign}{r['consensus_score']:.2f}  "
                      f"S{r['supports']} C{r['contradicts']} R{r['refines']}  "
                      f"{xs}  {r['chunk_id'][:12]:12s}  {r['heading']}")

    elif args.cmd == "contested":
        results = contested_claims(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No contested claims found.")
            else:
                print(f"{len(results)} contested claims:")
                for r in results:
                    print(f"  {r['consensus_score']:+.2f}  "
                          f"S{r['supports']} C{r['contradicts']}  "
                          f"{r['chunk_id'][:12]:12s}  {r['heading']}")

    elif args.cmd == "summary":
        result = consensus_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Claim Consensus: {result['avg_consensus']:+.2f} avg "
                  f"({result['total_claims_with_edges']} claims with edges)")
            print(f"  Unanimous support: {result['unanimous_support']}  "
                  f"Contested: {result['contested_count']}  "
                  f"Cross-source: {result['cross_source_claims']}")
            et = result["edge_type_totals"]
            print(f"  Edges: {et['supports']} supports, "
                  f"{et['contradicts']} contradicts, "
                  f"{et['refines']} refines, "
                  f"{et['duplicates']} duplicates, "
                  f"{et['supersedes']} supersedes")

    conn.close()


if __name__ == "__main__":
    main()
