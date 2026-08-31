#!/usr/bin/env python3
"""Edge confidence calibration: confidence distribution across claim edges.

Analyses how confidence scores are distributed across edge types,
detects calibration issues (clustering at extremes), and identifies
source pairs with systematically biased confidence.

Usage:
    python tools/corpus/edge_confidence.py distribution [--db PATH] [--json]
    python tools/corpus/edge_confidence.py extremes [--db PATH] [--threshold F] [--json]
    python tools/corpus/edge_confidence.py per-type [--db PATH] [--json]
    python tools/corpus/edge_confidence.py summary [--db PATH] [--json]
    python tools/corpus/edge_confidence.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _bucket(conf: float) -> str:
    """Map a confidence value to a histogram bucket."""
    if conf <= 0.2:
        return "0.0-0.2"
    if conf <= 0.4:
        return "0.2-0.4"
    if conf <= 0.6:
        return "0.4-0.6"
    if conf <= 0.8:
        return "0.6-0.8"
    return "0.8-1.0"


BUCKET_ORDER = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]


def confidence_distribution(conn) -> list[dict]:
    """Confidence histogram across all claim edges."""
    rows = conn.execute(
        "SELECT e.confidence "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE a.status = 'accepted' AND b.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, int] = dict.fromkeys(BUCKET_ORDER, 0)
    for (conf,) in rows:
        buckets[_bucket(conf)] += 1

    total = len(rows)
    return [
        {
            "bucket": b,
            "count": buckets[b],
            "share": round(buckets[b] / total, 4) if total > 0 else 0.0,
        }
        for b in BUCKET_ORDER
    ]


def extreme_edges(conn, threshold: float = 0.05) -> list[dict]:
    """Edges with confidence near 0 or 1, possibly miscalibrated.

    Returns edges where confidence < threshold or > (1 - threshold).
    """
    rows = conn.execute(
        "SELECT e.edge_id, e.source_chunk, e.target_chunk, "
        "e.edge_type, e.confidence, e.basis, e.resolution "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE a.status = 'accepted' AND b.status = 'accepted' "
        "AND (e.confidence < ? OR e.confidence > ?)",
        (threshold, 1.0 - threshold),
    ).fetchall()

    results = []
    for edge_id, src, tgt, etype, conf, basis, resolution in rows:
        results.append({
            "edge_id": edge_id,
            "source_chunk": src,
            "target_chunk": tgt,
            "edge_type": etype,
            "confidence": round(conf, 4),
            "basis": basis,
            "resolved": resolution is not None,
            "extreme": "low" if conf < threshold else "high",
        })

    results.sort(key=lambda r: r["confidence"])
    return results


def per_type_confidence(conn) -> list[dict]:
    """Confidence statistics per edge type."""
    rows = conn.execute(
        "SELECT e.edge_type, e.confidence "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE a.status = 'accepted' AND b.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    by_type: dict[str, list[float]] = {}
    for etype, conf in rows:
        by_type.setdefault(etype, []).append(conf)

    results = []
    for etype, confs in sorted(by_type.items()):
        n = len(confs)
        mean_c = sum(confs) / n
        sorted_c = sorted(confs)
        median_c = sorted_c[n // 2]
        variance = sum((c - mean_c) ** 2 for c in confs) / n if n > 1 else 0.0
        stddev = math.sqrt(variance)

        results.append({
            "edge_type": etype,
            "count": n,
            "mean_confidence": round(mean_c, 4),
            "median_confidence": round(median_c, 4),
            "min_confidence": round(min(confs), 4),
            "max_confidence": round(max(confs), 4),
            "stddev": round(stddev, 4),
        })

    results.sort(key=lambda r: r["count"], reverse=True)
    return results


def confidence_summary(conn) -> dict:
    """Aggregate edge confidence statistics."""
    rows = conn.execute(
        "SELECT e.confidence, e.edge_type, e.resolution "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE a.status = 'accepted' AND b.status = 'accepted'"
    ).fetchall()

    if not rows:
        return {
            "total_edges": 0,
            "mean_confidence": 0.0,
            "median_confidence": 0.0,
            "stddev": 0.0,
            "resolved_count": 0,
            "unresolved_count": 0,
            "edge_types": 0,
            "high_confidence_count": 0,
            "low_confidence_count": 0,
        }

    confs = [r[0] for r in rows]
    n = len(confs)
    mean_c = sum(confs) / n
    sorted_c = sorted(confs)
    median_c = sorted_c[n // 2]
    variance = sum((c - mean_c) ** 2 for c in confs) / n if n > 1 else 0.0
    stddev = math.sqrt(variance)

    resolved = sum(1 for r in rows if r[2] is not None)
    edge_types = len({r[1] for r in rows})

    return {
        "total_edges": n,
        "mean_confidence": round(mean_c, 4),
        "median_confidence": round(median_c, 4),
        "stddev": round(stddev, 4),
        "resolved_count": resolved,
        "unresolved_count": n - resolved,
        "edge_types": edge_types,
        "high_confidence_count": sum(1 for c in confs if c > 0.8),
        "low_confidence_count": sum(1 for c in confs if c < 0.2),
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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://a.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        for i in range(4):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (f"c{i}", "s1", i, f"Heading {i}", "claim", "en",
                 f"text {i}", f"text {i}", 10, f"n_c{i}",
                 "accepted", now),
            )

        edges = [
            ("e1", "c0", "c1", "supports", "semantic", 0.95, None),
            ("e2", "c1", "c2", "contradicts", "semantic", 0.72, None),
            ("e3", "c2", "c3", "supports", "keyword", 0.45, "accepted"),
            ("e4", "c0", "c2", "duplicates", "norm_sha256", 1.0, None),
            ("e5", "c1", "c3", "contradicts", "semantic", 0.03, None),
            ("e6", "c0", "c3", "refines", "semantic", 0.60, "rejected"),
        ]
        for eid, src, tgt, etype, basis, conf, resolution in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc, resolution, resolved_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (eid, src, tgt, etype, basis, conf, now, resolution,
                 now if resolution else None),
            )

        conn.commit()

        # 1: distribution returns 5 buckets
        dist = confidence_distribution(conn)
        assert len(dist) == 5
        checks += 1

        # 2: all shares sum to approximately 1.0
        total_share = sum(d["share"] for d in dist)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: bucket counts sum to total edges
        total_count = sum(d["count"] for d in dist)
        assert total_count == 6
        checks += 1

        # 4: high confidence bucket has edges
        high_bucket = next(d for d in dist if d["bucket"] == "0.8-1.0")
        assert high_bucket["count"] >= 2
        checks += 1

        # 5: extreme edges with default threshold
        extremes = extreme_edges(conn, threshold=0.05)
        extreme_ids = [e["edge_id"] for e in extremes]
        assert "e5" in extreme_ids
        assert "e4" in extreme_ids
        checks += 1

        # 6: extreme edges have correct extreme label
        e5 = next(e for e in extremes if e["edge_id"] == "e5")
        assert e5["extreme"] == "low"
        e4 = next(e for e in extremes if e["edge_id"] == "e4")
        assert e4["extreme"] == "high"
        checks += 1

        # 7: sorted by confidence ascending
        ext_confs = [e["confidence"] for e in extremes]
        assert ext_confs == sorted(ext_confs)
        checks += 1

        # 8: per-type returns all present types
        pt = per_type_confidence(conn)
        type_set = {p["edge_type"] for p in pt}
        assert type_set == {"supports", "contradicts", "duplicates", "refines"}
        checks += 1

        # 9: supports has 2 edges
        supports = next(p for p in pt if p["edge_type"] == "supports")
        assert supports["count"] == 2
        checks += 1

        # 10: mean confidence is between min and max
        for p in pt:
            assert p["min_confidence"] <= p["mean_confidence"] <= p["max_confidence"]
        checks += 1

        # 11: summary has required keys
        summary = confidence_summary(conn)
        assert summary["total_edges"] == 6
        assert summary["edge_types"] == 4
        checks += 1

        # 12: resolved + unresolved = total
        assert (summary["resolved_count"]
                + summary["unresolved_count"]) == summary["total_edges"]
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(extremes)
        _ = json.dumps(pt)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = confidence_distribution(conn2)
        assert empty == []
        empty_summary = confidence_summary(conn2)
        assert empty_summary["total_edges"] == 0
        checks += 1

    print(f"PASS edge_confidence selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge confidence calibration: claim edge confidence analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Confidence histogram across all edges")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_ext = sub.add_parser("extremes",
                           help="Edges with extreme confidence values")
    p_ext.add_argument("--db", default=DEFAULT_DB)
    p_ext.add_argument("--threshold", type=float, default=0.05)
    p_ext.add_argument("--json", action="store_true")

    p_pt = sub.add_parser("per-type",
                          help="Confidence statistics per edge type")
    p_pt.add_argument("--db", default=DEFAULT_DB)
    p_pt.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Aggregate confidence statistics")
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

    if args.cmd == "distribution":
        results = confidence_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bucket']:7s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "extremes":
        results = extreme_edges(conn, args.threshold)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No extreme-confidence edges found.")
            else:
                print(f"{len(results)} edges with confidence "
                      f"< {args.threshold} or > {1 - args.threshold}:")
                for e in results:
                    print(f"  {e['confidence']:.4f}  {e['extreme']:4s}  "
                          f"{e['edge_type']:12s}  {e['edge_id'][:12]}")

    elif args.cmd == "per-type":
        results = per_type_confidence(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:12s}  n={r['count']:3d}  "
                      f"mean={r['mean_confidence']:.3f}  "
                      f"sd={r['stddev']:.3f}  "
                      f"range={r['min_confidence']:.2f}-"
                      f"{r['max_confidence']:.2f}")

    elif args.cmd == "summary":
        result = confidence_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edge Confidence: {result['total_edges']} edges, "
                  f"{result['edge_types']} types")
            print(f"  Mean: {result['mean_confidence']:.3f}  "
                  f"Median: {result['median_confidence']:.3f}  "
                  f"SD: {result['stddev']:.3f}")
            print(f"  High (>0.8): {result['high_confidence_count']}  "
                  f"Low (<0.2): {result['low_confidence_count']}  "
                  f"Resolved: {result['resolved_count']}")

    conn.close()


if __name__ == "__main__":
    main()
