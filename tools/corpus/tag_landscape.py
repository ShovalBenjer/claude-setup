#!/usr/bin/env python3
"""Tag landscape: distribution and correlation analysis of chunk tags.

Analyses the chunk_tags table to report tag frequency distribution,
per-source tag profiles, tag-edge correlation, and score distribution.

Usage:
    python tools/corpus/tag_landscape.py distribution [--db PATH] [--json]
    python tools/corpus/tag_landscape.py per-source [--db PATH] [--json]
    python tools/corpus/tag_landscape.py edge-tags [--db PATH] [--json]
    python tools/corpus/tag_landscape.py score-bands [--db PATH] [--json]
    python tools/corpus/tag_landscape.py selftest
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


def tag_distribution(conn) -> dict:
    """Tag frequency distribution across the corpus."""
    if not _table_exists(conn, "chunk_tags"):
        return {"tags": [], "total_assignments": 0,
                "unique_tags": 0, "tagged_chunks": 0}

    rows = conn.execute(
        "SELECT tag, count(*) AS chunk_count, "
        "round(avg(score), 4) AS avg_score "
        "FROM chunk_tags "
        "GROUP BY tag "
        "ORDER BY chunk_count DESC"
    ).fetchall()

    total = conn.execute(
        "SELECT count(*) FROM chunk_tags"
    ).fetchone()[0]

    tagged = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_tags"
    ).fetchone()[0]

    return {
        "tags": [
            {"tag": r[0], "chunk_count": r[1], "avg_score": r[2]}
            for r in rows
        ],
        "total_assignments": total,
        "unique_tags": len(rows),
        "tagged_chunks": tagged,
    }


def tag_per_source(conn) -> list[dict]:
    """Per-source tag profile showing which tags each source contributes."""
    if not _table_exists(conn, "chunk_tags"):
        return []

    rows = conn.execute(
        "SELECT c.source_id, s.title, ct.tag, "
        "count(*) AS chunk_count, round(avg(ct.score), 4) AS avg_score "
        "FROM chunk_tags ct "
        "JOIN chunks c ON c.chunk_id = ct.chunk_id "
        "JOIN sources s ON s.source_id = c.source_id "
        "GROUP BY c.source_id, ct.tag "
        "ORDER BY c.source_id, chunk_count DESC"
    ).fetchall()

    sources: dict[str, dict] = {}
    for r in rows:
        sid = r[0]
        if sid not in sources:
            sources[sid] = {"source_id": sid, "title": r[1], "tags": []}
        sources[sid]["tags"].append({
            "tag": r[2], "chunk_count": r[3], "avg_score": r[4],
        })

    return list(sources.values())


def edge_tag_correlation(conn) -> list[dict]:
    """Tags that appear on chunks involved in claim edges."""
    if not _table_exists(conn, "chunk_tags"):
        return []
    if not _table_exists(conn, "claim_edges"):
        return []

    rows = conn.execute(
        "SELECT ct.tag, ce.edge_type, count(*) AS edge_count "
        "FROM claim_edges ce "
        "JOIN chunk_tags ct ON ct.chunk_id IN "
        "  (ce.source_chunk, ce.target_chunk) "
        "GROUP BY ct.tag, ce.edge_type "
        "ORDER BY edge_count DESC"
    ).fetchall()

    return [
        {"tag": r[0], "edge_type": r[1], "edge_count": r[2]}
        for r in rows
    ]


def score_bands(conn) -> list[dict]:
    """Tag score distribution in bands (0-0.25, 0.25-0.5, 0.5-0.75, 0.75-1.0)."""
    if not _table_exists(conn, "chunk_tags"):
        return []

    bands = [
        ("0.00-0.25", 0.0, 0.25),
        ("0.25-0.50", 0.25, 0.50),
        ("0.50-0.75", 0.50, 0.75),
        ("0.75-1.00", 0.75, 1.01),
    ]

    result = []
    for label, lo, hi in bands:
        count = conn.execute(
            "SELECT count(*) FROM chunk_tags "
            "WHERE score >= ? AND score < ?",
            (lo, hi),
        ).fetchone()[0]
        result.append({"band": label, "count": count})

    return result


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
            ("c3", "s2", 0, "H3", "claim"),
            ("c4", "s2", 1, "H4", "prose"),
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

        tag_data = [
            ("c1", "ml", 0.9, now),
            ("c1", "transformers", 0.8, now),
            ("c2", "ml", 0.7, now),
            ("c3", "systems", 0.6, now),
            ("c3", "ml", 0.3, now),
            ("c4", "systems", 0.15, now),
        ]
        for td_row in tag_data:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
                "VALUES (?, ?, ?, ?)", td_row,
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c3", "supports", "semantic", 0.8, now),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e2", "c2", "c3", "contradicts", "semantic", 0.7, now),
        )
        conn.commit()

        # 1: distribution totals
        dist = tag_distribution(conn)
        assert dist["total_assignments"] == 6
        assert dist["unique_tags"] == 3
        assert dist["tagged_chunks"] == 4
        checks += 1

        # 2: tag ordering by frequency
        assert dist["tags"][0]["tag"] == "ml"
        assert dist["tags"][0]["chunk_count"] == 3
        checks += 1

        # 3: avg score
        ml_tag = dist["tags"][0]
        expected_avg = round((0.9 + 0.7 + 0.3) / 3, 4)
        assert ml_tag["avg_score"] == expected_avg
        checks += 1

        # 4: per-source tag profiles
        ps = tag_per_source(conn)
        assert len(ps) == 2
        checks += 1

        # 5: s1 tags
        s1_ps = [p for p in ps if p["source_id"] == "s1"][0]
        s1_tags = {t["tag"] for t in s1_ps["tags"]}
        assert "ml" in s1_tags
        assert "transformers" in s1_tags
        checks += 1

        # 6: s2 tags
        s2_ps = [p for p in ps if p["source_id"] == "s2"][0]
        s2_tags = {t["tag"] for t in s2_ps["tags"]}
        assert "systems" in s2_tags
        assert "ml" in s2_tags
        checks += 1

        # 7: edge-tag correlation
        et = edge_tag_correlation(conn)
        assert len(et) > 0
        checks += 1

        # 8: ml tag appears in edge correlation (c1, c2, c3 all tagged ml)
        ml_edges = [e for e in et if e["tag"] == "ml"]
        assert len(ml_edges) > 0
        checks += 1

        # 9: edge types in correlation
        et_types = {e["edge_type"] for e in et}
        assert "supports" in et_types
        assert "contradicts" in et_types
        checks += 1

        # 10: score bands
        sb = score_bands(conn)
        assert len(sb) == 4
        checks += 1

        # 11: band counts
        band_map = {b["band"]: b["count"] for b in sb}
        assert band_map["0.00-0.25"] == 1
        assert band_map["0.25-0.50"] == 1
        assert band_map["0.50-0.75"] == 2
        assert band_map["0.75-1.00"] == 2
        checks += 1

        # 12: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(ps)
        _ = json.dumps(et)
        _ = json.dumps(sb)
        checks += 1

        # 13: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert tag_distribution(conn2)["total_assignments"] == 0
        assert tag_per_source(conn2) == []
        assert edge_tag_correlation(conn2) == []
        sb2 = score_bands(conn2)
        assert all(b["count"] == 0 for b in sb2)
        checks += 1

        # 14: transformers tag only on s1
        assert "transformers" not in s2_tags
        checks += 1

    print(f"PASS tag_landscape selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag landscape: distribution and correlation analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Tag frequency distribution")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_ps = sub.add_parser("per-source",
                          help="Per-source tag profile")
    p_ps.add_argument("--db", default=DEFAULT_DB)
    p_ps.add_argument("--json", action="store_true")

    p_et = sub.add_parser("edge-tags",
                          help="Tags on edge-involved chunks")
    p_et.add_argument("--db", default=DEFAULT_DB)
    p_et.add_argument("--json", action="store_true")

    p_sb = sub.add_parser("score-bands",
                          help="Tag score distribution in bands")
    p_sb.add_argument("--db", default=DEFAULT_DB)
    p_sb.add_argument("--json", action="store_true")

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
        result = tag_distribution(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tags: {result['unique_tags']}, "
                  f"assignments: {result['total_assignments']}, "
                  f"tagged chunks: {result['tagged_chunks']}")
            for t in result["tags"]:
                print(f"  {t['tag']}: {t['chunk_count']} chunks "
                      f"(avg score {t['avg_score']:.2f})")

    elif args.cmd == "per-source":
        result = tag_per_source(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources with tags: {len(result)}")
            for s in result:
                tags = ", ".join(
                    f"{t['tag']}({t['chunk_count']})"
                    for t in s["tags"]
                )
                print(f"  {s['source_id']}: {tags}")

    elif args.cmd == "edge-tags":
        result = edge_tag_correlation(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Tag-edge correlations: {len(result)}")
            for r in result:
                print(f"  {r['tag']} + {r['edge_type']}: "
                      f"{r['edge_count']} edges")

    elif args.cmd == "score-bands":
        result = score_bands(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("Score distribution:")
            for b in result:
                print(f"  {b['band']}: {b['count']} assignments")

    conn.close()


if __name__ == "__main__":
    main()
