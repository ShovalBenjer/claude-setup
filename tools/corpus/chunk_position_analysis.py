#!/usr/bin/env python3
"""Chunk position analysis: ordinal distribution and positional patterns.

Analyses the chunks.ordinal column which had zero GROUP BY queries
anywhere in the codebase, revealing document length distribution,
how chunk kinds vary by position, and whether citation density
correlates with document position.

Usage:
    python tools/corpus/chunk_position_analysis.py depth [--db PATH] [--json]
    python tools/corpus/chunk_position_analysis.py kind-by-position [--db PATH] [--json]
    python tools/corpus/chunk_position_analysis.py citation-by-position [--db PATH] [--json]
    python tools/corpus/chunk_position_analysis.py summary [--db PATH] [--json]
    python tools/corpus/chunk_position_analysis.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _position_bucket(ordinal: int, max_ordinal: int) -> str:
    if max_ordinal == 0:
        return "only"
    ratio = ordinal / max_ordinal
    if ratio == 0:
        return "first"
    if ratio <= 0.25:
        return "early"
    if ratio <= 0.75:
        return "middle"
    if ratio < 1.0:
        return "late"
    return "last"


def depth_distribution(conn) -> list[dict]:
    """Distribution of document depths (max ordinal + 1 per source)."""
    rows = conn.execute(
        "SELECT source_id, MAX(ordinal) + 1 AS depth "
        "FROM chunks WHERE status = 'accepted' "
        "GROUP BY source_id"
    ).fetchall()

    if not rows:
        return []

    buckets: dict[str, int] = {}
    for _, depth in rows:
        if depth == 1:
            key = "1"
        elif depth <= 3:
            key = "2-3"
        elif depth <= 5:
            key = "4-5"
        elif depth <= 10:
            key = "6-10"
        elif depth <= 20:
            key = "11-20"
        else:
            key = ">20"
        buckets[key] = buckets.get(key, 0) + 1

    order = ["1", "2-3", "4-5", "6-10", "11-20", ">20"]
    total = sum(buckets.values())
    results = []
    for b in order:
        if b in buckets:
            n = buckets[b]
            results.append({
                "bucket": b,
                "count": n,
                "share": round(n / total, 4) if total > 0 else 0.0,
            })

    return results


def kind_by_position(conn) -> list[dict]:
    """Chunk kind distribution by document position."""
    rows = conn.execute(
        "SELECT c.source_id, c.ordinal, c.kind, m.max_ord "
        "FROM chunks c "
        "JOIN (SELECT source_id, MAX(ordinal) AS max_ord "
        "      FROM chunks WHERE status = 'accepted' "
        "      GROUP BY source_id) m "
        "ON c.source_id = m.source_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    pos_kind: dict[str, dict[str, int]] = {}
    for _, ordinal, kind, max_ord in rows:
        pos = _position_bucket(ordinal, max_ord)
        if pos not in pos_kind:
            pos_kind[pos] = {}
        pos_kind[pos][kind] = pos_kind[pos].get(kind, 0) + 1

    order = ["only", "first", "early", "middle", "late", "last"]
    results = []
    for pos in order:
        if pos in pos_kind:
            breakdown = pos_kind[pos]
            total = sum(breakdown.values())
            results.append({
                "position": pos,
                "total": total,
                "breakdown": breakdown,
            })

    return results


def citation_by_position(conn) -> list[dict]:
    """Citation density by document position."""
    rows = conn.execute(
        "SELECT c.ordinal, c.citation_count, m.max_ord "
        "FROM chunks c "
        "JOIN (SELECT source_id, MAX(ordinal) AS max_ord "
        "      FROM chunks WHERE status = 'accepted' "
        "      GROUP BY source_id) m "
        "ON c.source_id = m.source_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    if not rows:
        return []

    pos_data: dict[str, list[int]] = {}
    for ordinal, cite_count, max_ord in rows:
        pos = _position_bucket(ordinal, max_ord)
        if pos not in pos_data:
            pos_data[pos] = []
        pos_data[pos].append(cite_count)

    order = ["only", "first", "early", "middle", "late", "last"]
    results = []
    for pos in order:
        if pos in pos_data:
            counts = pos_data[pos]
            n = len(counts)
            total_cites = sum(counts)
            cited = sum(1 for c in counts if c > 0)
            results.append({
                "position": pos,
                "chunks": n,
                "total_citations": total_cites,
                "mean_citations": round(total_cites / n, 2) if n > 0 else 0.0,
                "cited_rate": round(cited / n, 4) if n > 0 else 0.0,
            })

    return results


def position_summary(conn) -> dict:
    """Aggregate positional statistics."""
    rows = conn.execute(
        "SELECT source_id, MAX(ordinal) + 1 AS depth "
        "FROM chunks WHERE status = 'accepted' "
        "GROUP BY source_id"
    ).fetchall()

    if not rows:
        return {
            "total_sources": 0,
            "total_chunks": 0,
            "depth_mean": 0.0,
            "depth_max": 0,
            "depth_min": 0,
            "single_chunk_sources": 0,
            "single_chunk_rate": 0.0,
        }

    depths = [d for _, d in rows]
    n = len(depths)
    total_chunks = sum(depths)
    singles = sum(1 for d in depths if d == 1)

    kind_rows = conn.execute(
        "SELECT c.kind, c.ordinal, m.max_ord "
        "FROM chunks c "
        "JOIN (SELECT source_id, MAX(ordinal) AS max_ord "
        "      FROM chunks WHERE status = 'accepted' "
        "      GROUP BY source_id) m "
        "ON c.source_id = m.source_id "
        "WHERE c.status = 'accepted'"
    ).fetchall()

    first_kinds: dict[str, int] = {}
    last_kinds: dict[str, int] = {}
    for kind, ordinal, max_ord in kind_rows:
        if ordinal == 0:
            first_kinds[kind] = first_kinds.get(kind, 0) + 1
        if ordinal == max_ord and max_ord > 0:
            last_kinds[kind] = last_kinds.get(kind, 0) + 1

    dominant_first = max(first_kinds, key=first_kinds.get) if first_kinds else None
    dominant_last = max(last_kinds, key=last_kinds.get) if last_kinds else None

    return {
        "total_sources": n,
        "total_chunks": total_chunks,
        "depth_mean": round(total_chunks / n, 1) if n > 0 else 0.0,
        "depth_max": max(depths),
        "depth_min": min(depths),
        "single_chunk_sources": singles,
        "single_chunk_rate": round(singles / n, 4) if n > 0 else 0.0,
        "dominant_first_kind": dominant_first,
        "dominant_last_kind": dominant_last,
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

        sources = [
            ("s1", "paper"),
            ("s2", "local_md"),
            ("s3", "repo"),
        ]
        for sid, kind in sources:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, f"https://{sid}.com", kind, f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        # s1: 5 chunks (deep document)
        # s2: 1 chunk (single-chunk document)
        # s3: 3 chunks (medium document)
        chunks = [
            ("c1", "s1", 0, "prose", 2),
            ("c2", "s1", 1, "claim", 3),
            ("c3", "s1", 2, "code", 0),
            ("c4", "s1", 3, "prose", 1),
            ("c5", "s1", 4, "code", 0),
            ("c6", "s2", 0, "prose", 5),
            ("c7", "s3", 0, "claim", 1),
            ("c8", "s3", 1, "prose", 0),
            ("c9", "s3", 2, "code", 4),
        ]
        for cid, sid, ordinal, kind, cites in chunks:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", kind, "en",
                 f"text {cid}", f"text {cid}", 10, f"sha_{cid}",
                 0, cites, "accepted", now),
            )

        conn.commit()

        # 1: depth distribution returns entries
        dd = depth_distribution(conn)
        assert len(dd) > 0
        checks += 1

        # 2: three sources produce three depth values: 5, 1, 3
        # buckets: "1" -> 1, "2-3" -> 1, "4-5" -> 1
        bucket_map = {d["bucket"]: d["count"] for d in dd}
        assert bucket_map.get("1") == 1
        assert bucket_map.get("2-3") == 1
        assert bucket_map.get("4-5") == 1
        checks += 1

        # 3: depth shares sum to approximately 1.0
        depth_share = sum(d["share"] for d in dd)
        assert abs(depth_share - 1.0) < 0.01
        checks += 1

        # 4: kind-by-position returns entries
        kbp = kind_by_position(conn)
        assert len(kbp) > 0
        checks += 1

        # 5: "only" position has 1 chunk (s2's single chunk)
        only = next((k for k in kbp if k["position"] == "only"), None)
        assert only is not None
        assert only["total"] == 1
        checks += 1

        # 6: "first" position has entries (s1 ord 0, s3 ord 0)
        first = next((k for k in kbp if k["position"] == "first"), None)
        assert first is not None
        assert first["total"] == 2
        checks += 1

        # 7: "last" position has entries (s1 ord 4, s3 ord 2)
        last = next((k for k in kbp if k["position"] == "last"), None)
        assert last is not None
        assert last["total"] == 2
        checks += 1

        # 8: citation-by-position returns entries
        cbp = citation_by_position(conn)
        assert len(cbp) > 0
        checks += 1

        # 9: "only" position has 5 total citations (s2 c6)
        only_cite = next(
            (c for c in cbp if c["position"] == "only"), None
        )
        assert only_cite is not None
        assert only_cite["total_citations"] == 5
        checks += 1

        # 10: "first" position cited_rate > 0
        first_cite = next(
            (c for c in cbp if c["position"] == "first"), None
        )
        assert first_cite is not None
        assert first_cite["cited_rate"] > 0
        checks += 1

        # 11: summary has correct source and chunk counts
        summary = position_summary(conn)
        assert summary["total_sources"] == 3
        assert summary["total_chunks"] == 9
        checks += 1

        # 12: depth stats
        assert summary["depth_max"] == 5
        assert summary["depth_min"] == 1
        assert summary["single_chunk_sources"] == 1
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dd)
        _ = json.dumps(kbp)
        _ = json.dumps(cbp)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = depth_distribution(conn2)
        assert empty == []
        empty_summary = position_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(f"PASS chunk_position_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk position analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_depth = sub.add_parser("depth",
                             help="Document depth distribution")
    p_depth.add_argument("--db", default=DEFAULT_DB)
    p_depth.add_argument("--json", action="store_true")

    p_kind = sub.add_parser("kind-by-position",
                            help="Chunk kind by document position")
    p_kind.add_argument("--db", default=DEFAULT_DB)
    p_kind.add_argument("--json", action="store_true")

    p_cite = sub.add_parser("citation-by-position",
                            help="Citation density by position")
    p_cite.add_argument("--db", default=DEFAULT_DB)
    p_cite.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Positional statistics")
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

    if args.cmd == "depth":
        results = depth_distribution(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                bar = "#" * int(r["share"] * 40)
                print(f"  {r['bucket']:6s}  {r['count']:4d}  "
                      f"{r['share']:5.1%}  {bar}")

    elif args.cmd == "kind-by-position":
        results = kind_by_position(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['position']:8s}  n={r['total']:4d}  "
                      f"{r['breakdown']}")

    elif args.cmd == "citation-by-position":
        results = citation_by_position(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['position']:8s}  n={r['chunks']:4d}  "
                      f"cites={r['total_citations']:4d}  "
                      f"mean={r['mean_citations']:.1f}  "
                      f"cited={r['cited_rate']:.0%}")

    elif args.cmd == "summary":
        result = position_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"Chunks: {result['total_chunks']}")
            print(f"  Depth: mean={result['depth_mean']:.1f}  "
                  f"max={result['depth_max']}  "
                  f"min={result['depth_min']}")
            print(f"  Single-chunk: {result['single_chunk_sources']} "
                  f"({result['single_chunk_rate']:.0%})")
            print(f"  Dominant first kind: "
                  f"{result['dominant_first_kind']}")
            print(f"  Dominant last kind: "
                  f"{result['dominant_last_kind']}")

    conn.close()


if __name__ == "__main__":
    main()
