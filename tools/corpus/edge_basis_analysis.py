#!/usr/bin/env python3
"""Edge basis analysis: patterns in claim edge justification text.

Analyses the basis field of claim_edges to reveal how edges are
justified, which basis patterns correlate with edge types and
confidence levels, and whether basis text is missing or sparse.

Usage:
    python tools/corpus/edge_basis_analysis.py frequency [--db PATH] [--json]
    python tools/corpus/edge_basis_analysis.py per-type [--db PATH] [--json]
    python tools/corpus/edge_basis_analysis.py quality [--db PATH] [--json]
    python tools/corpus/edge_basis_analysis.py summary [--db PATH] [--json]
    python tools/corpus/edge_basis_analysis.py selftest
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

WORD_BINS = [
    (0, 0, "empty"),
    (1, 5, "1-5w"),
    (6, 15, "6-15w"),
    (16, 50, "16-50w"),
    (51, None, ">50w"),
]


def _word_count(text: str | None) -> int:
    if not text or not text.strip():
        return 0
    return len(text.split())


def basis_frequency(conn) -> list[dict]:
    """Word-count distribution of basis text across all edges."""
    rows = conn.execute(
        "SELECT basis FROM claim_edges"
    ).fetchall()

    if not rows:
        return []

    wcs = [_word_count(r[0]) for r in rows]
    total = len(wcs)

    results = []
    for lo, hi, label in WORD_BINS:
        if hi is None:
            n = sum(1 for w in wcs if w >= lo)
        else:
            n = sum(1 for w in wcs if lo <= w <= hi)
        results.append({
            "bin": label,
            "count": n,
            "share": round(n / total, 4) if total > 0 else 0.0,
        })

    return results


def basis_per_type(conn) -> list[dict]:
    """Basis text statistics per edge type."""
    rows = conn.execute(
        "SELECT edge_type, basis FROM claim_edges"
    ).fetchall()

    if not rows:
        return []

    by_type: dict[str, list[int]] = {}
    for etype, basis in rows:
        by_type.setdefault(etype, []).append(_word_count(basis))

    results = []
    for etype, wcs in sorted(by_type.items()):
        n = len(wcs)
        mean = sum(wcs) / n
        non_empty = sum(1 for w in wcs if w > 0)
        variance = sum((w - mean) ** 2 for w in wcs) / n if n > 1 else 0.0

        results.append({
            "edge_type": etype,
            "count": n,
            "non_empty": non_empty,
            "coverage": round(non_empty / n, 4) if n > 0 else 0.0,
            "mean_words": round(mean, 1),
            "max_words": max(wcs),
            "stddev": round(math.sqrt(variance), 1),
        })

    results.sort(key=lambda r: r["coverage"])
    return results


def basis_quality(conn) -> list[dict]:
    """Edges with missing or very short basis text."""
    rows = conn.execute(
        "SELECT edge_id, source_chunk, target_chunk, edge_type, "
        "confidence, basis FROM claim_edges"
    ).fetchall()

    if not rows:
        return []

    results = []
    for edge_id, src, tgt, etype, conf, basis in rows:
        wc = _word_count(basis)
        if wc <= 5:
            results.append({
                "edge_id": edge_id,
                "source_chunk": src,
                "target_chunk": tgt,
                "edge_type": etype,
                "confidence": conf,
                "basis_words": wc,
                "issue": "missing" if wc == 0 else "sparse",
            })

    results.sort(key=lambda r: (r["basis_words"], r["edge_id"]))
    return results


def basis_summary(conn) -> dict:
    """Aggregate basis text statistics."""
    rows = conn.execute(
        "SELECT edge_type, basis, confidence FROM claim_edges"
    ).fetchall()

    if not rows:
        return {
            "total_edges": 0,
            "with_basis": 0,
            "without_basis": 0,
            "coverage_rate": 0.0,
            "mean_words": 0.0,
            "median_words": 0,
            "max_words": 0,
            "sparse_count": 0,
            "edge_types": 0,
        }

    wcs = [_word_count(r[1]) for r in rows]
    n = len(wcs)
    with_basis = sum(1 for w in wcs if w > 0)
    sorted_wcs = sorted(wcs)
    mean = sum(wcs) / n

    types = {r[0] for r in rows}

    return {
        "total_edges": n,
        "with_basis": with_basis,
        "without_basis": n - with_basis,
        "coverage_rate": round(with_basis / n, 4) if n > 0 else 0.0,
        "mean_words": round(mean, 1),
        "median_words": sorted_wcs[n // 2],
        "max_words": max(wcs),
        "sparse_count": sum(1 for w in wcs if 0 < w <= 5),
        "edge_types": len(types),
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

        src_id = "s1"
        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (src_id, "https://s1.com", "paper", "Source 1",
             "CC-BY-4.0", "vendor", "declared", "Pub",
             now, now, "", "", "live", "sha_s1", 1000, None),
        )

        chunks = [
            ("c1", 0, "claim"), ("c2", 1, "prose"),
            ("c3", 2, "claim"), ("c4", 3, "code"),
        ]
        for cid, ordinal, kind in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, src_id, ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 2, f"sha_{cid}",
                 0, 0, "accepted", now),
            )

        edges = [
            ("e1", "c1", "c2", "supports",
             "Both discuss the same methodology with matching results",
             0.9),
            ("e2", "c1", "c3", "contradicts",
             "Conflicting claims about threshold values",
             0.7),
            ("e3", "c2", "c3", "supports", "", 0.8),
            ("e4", "c3", "c4", "refines", "", 0.6),
            ("e5", "c1", "c4", "duplicates", "same", 0.95),
            ("e6", "c2", "c4", "supports",
             "Extended analysis confirming the original finding "
             "with additional data points and revised methodology",
             0.85),
        ]
        for eid, src, tgt, etype, basis, conf in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (eid, src, tgt, etype, basis, conf, now),
            )

        conn.commit()

        # 1: frequency returns 5 bins
        freq = basis_frequency(conn)
        assert len(freq) == 5
        checks += 1

        # 2: shares sum to approximately 1.0
        total_share = sum(b["share"] for b in freq)
        assert abs(total_share - 1.0) < 0.01
        checks += 1

        # 3: counts sum to total edges
        total_count = sum(b["count"] for b in freq)
        assert total_count == 6
        checks += 1

        # 4: empty bin has 2 edges (e3 empty string, e4 None)
        empty_bin = next(b for b in freq if b["bin"] == "empty")
        assert empty_bin["count"] == 2
        checks += 1

        # 5: per-type returns all edge types
        per_type = basis_per_type(conn)
        type_set = {t["edge_type"] for t in per_type}
        assert type_set == {"supports", "contradicts", "refines", "duplicates"}
        checks += 1

        # 6: sorted by coverage ascending
        coverages = [t["coverage"] for t in per_type]
        assert coverages == sorted(coverages)
        checks += 1

        # 7: supports has 3 edges
        supports = next(t for t in per_type if t["edge_type"] == "supports")
        assert supports["count"] == 3
        checks += 1

        # 8: quality returns edges with short/missing basis
        quality = basis_quality(conn)
        assert len(quality) > 0
        checks += 1

        # 9: e3 (empty) and e4 (None) are missing
        missing = [q for q in quality if q["issue"] == "missing"]
        missing_ids = {q["edge_id"] for q in missing}
        assert "e3" in missing_ids and "e4" in missing_ids
        checks += 1

        # 10: e5 ("same", 1 word) is sparse
        sparse = [q for q in quality if q["issue"] == "sparse"]
        sparse_ids = {q["edge_id"] for q in sparse}
        assert "e5" in sparse_ids
        checks += 1

        # 11: summary has correct totals
        summary = basis_summary(conn)
        assert summary["total_edges"] == 6
        assert summary["with_basis"] == 4
        assert summary["without_basis"] == 2
        checks += 1

        # 12: coverage rate is 4/6
        assert abs(summary["coverage_rate"] - 4 / 6) < 0.01
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(freq)
        _ = json.dumps(per_type)
        _ = json.dumps(quality)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = basis_frequency(conn2)
        assert empty == []
        empty_summary = basis_summary(conn2)
        assert empty_summary["total_edges"] == 0
        checks += 1

    print(f"PASS edge_basis_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Edge basis analysis: claim justification patterns"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_freq = sub.add_parser("frequency",
                            help="Basis text word-count distribution")
    p_freq.add_argument("--db", default=DEFAULT_DB)
    p_freq.add_argument("--json", action="store_true")

    p_type = sub.add_parser("per-type",
                            help="Basis statistics per edge type")
    p_type.add_argument("--db", default=DEFAULT_DB)
    p_type.add_argument("--json", action="store_true")

    p_qual = sub.add_parser("quality",
                            help="Edges with missing or sparse basis")
    p_qual.add_argument("--db", default=DEFAULT_DB)
    p_qual.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Basis text statistics")
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

    if args.cmd == "frequency":
        results = basis_frequency(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bin']:8s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "per-type":
        results = basis_per_type(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['edge_type']:14s}  n={r['count']:3d}  "
                      f"coverage={r['coverage']:5.1%}  "
                      f"mean={r['mean_words']:.1f}w  "
                      f"max={r['max_words']}w")

    elif args.cmd == "quality":
        results = basis_quality(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("All edges have adequate basis text.")
            else:
                print(f"{len(results)} edges with weak basis:")
                for r in results:
                    print(f"  {r['issue']:7s}  {r['basis_words']}w  "
                          f"{r['edge_type']:14s}  conf={r['confidence']:.2f}  "
                          f"{r['edge_id'][:12]}")

    elif args.cmd == "summary":
        result = basis_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edges: {result['total_edges']}, "
                  f"{result['edge_types']} types")
            print(f"  With basis: {result['with_basis']}  "
                  f"Without: {result['without_basis']}  "
                  f"Coverage: {result['coverage_rate']:.1%}")
            print(f"  Mean: {result['mean_words']:.1f}w  "
                  f"Median: {result['median_words']}w  "
                  f"Max: {result['max_words']}w  "
                  f"Sparse: {result['sparse_count']}")

    conn.close()


if __name__ == "__main__":
    main()
