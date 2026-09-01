#!/usr/bin/env python3
"""Cross-table outlier detector: finds statistical anomalies across corpus tables.

source_enrichment_completeness.py measures enrichment coverage.
enrichment_lag_profile.py measures enrichment timing.
No tool detects statistical outliers that span multiple tables,
such as chunks with extreme word counts relative to their source,
sources whose edge density deviates from the corpus mean, or
citations concentrated in a narrow band of chunks.

Usage:
    python tools/corpus/cross_table_outlier_detector.py chunk-words [--db PATH] [--json]
    python tools/corpus/cross_table_outlier_detector.py edge-confidence [--db PATH] [--json]
    python tools/corpus/cross_table_outlier_detector.py citation-concentration [--db PATH] [--json]
    python tools/corpus/cross_table_outlier_detector.py summary [--db PATH] [--json]
    python tools/corpus/cross_table_outlier_detector.py selftest
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


def _stddev(values: list[float]) -> tuple[float, float]:
    """Return (mean, stddev) for a list of numbers."""
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return mean, math.sqrt(variance)


def chunk_word_outliers(conn, threshold: float = 2.0) -> list[dict]:
    """Chunks whose word count deviates more than threshold stddevs from their source mean."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.source_id, c.word_count, c.status
        FROM chunks c
        JOIN (
            SELECT source_id
            FROM chunks
            GROUP BY source_id
            HAVING COUNT(*) >= 2
        ) src ON src.source_id = c.source_id
        ORDER BY c.source_id, c.chunk_id
        """
    ).fetchall()

    per_source: dict[str, list[tuple]] = {}
    for r in rows:
        per_source.setdefault(r[1], []).append(r)

    results = []
    for source_id, chunk_rows in per_source.items():
        wcs = [r[2] for r in chunk_rows]
        mean, sd = _stddev(wcs)
        if sd == 0:
            continue
        for r in chunk_rows:
            z = abs(r[2] - mean) / sd
            if z > threshold:
                results.append({
                    "chunk_id": r[0],
                    "source_id": r[1],
                    "word_count": r[2],
                    "status": r[3],
                    "source_mean": round(mean, 2),
                    "source_stddev": round(sd, 2),
                    "z_score": round(z, 4),
                })
    results.sort(key=lambda x: -x["z_score"])
    return results


def edge_confidence_outliers(conn, threshold: float = 2.0) -> list[dict]:
    """Edges whose confidence deviates more than threshold stddevs from the type mean."""
    rows = conn.execute(
        """
        SELECT edge_id, source_chunk, target_chunk, edge_type, confidence
        FROM claim_edges
        WHERE confidence IS NOT NULL
        ORDER BY edge_type, edge_id
        """
    ).fetchall()

    per_type: dict[str, list[tuple]] = {}
    for r in rows:
        per_type.setdefault(r[3], []).append(r)

    results = []
    for edge_type, edge_rows in per_type.items():
        confs = [r[4] for r in edge_rows]
        mean, sd = _stddev(confs)
        if sd == 0:
            continue
        for r in edge_rows:
            z = abs(r[4] - mean) / sd
            if z > threshold:
                results.append({
                    "edge_id": r[0],
                    "source_chunk": r[1],
                    "target_chunk": r[2],
                    "edge_type": r[3],
                    "confidence": r[4],
                    "type_mean": round(mean, 4),
                    "type_stddev": round(sd, 4),
                    "z_score": round(z, 4),
                })
    results.sort(key=lambda x: -x["z_score"])
    return results


def citation_concentration(conn) -> list[dict]:
    """Sources where citations concentrate in a small fraction of chunks."""
    rows = conn.execute(
        """
        SELECT cw.source_id, s.title,
               cw.total_chunks,
               COALESCE(cc.cited_chunks, 0) AS cited_chunks,
               COALESCE(cc.citation_count, 0) AS citation_count
        FROM (
            SELECT source_id, COUNT(*) AS total_chunks
            FROM chunks GROUP BY source_id
        ) cw
        JOIN sources s ON s.source_id = cw.source_id
        LEFT JOIN (
            SELECT c.source_id,
                   COUNT(DISTINCT ci.chunk_id) AS cited_chunks,
                   COUNT(ci.citation_id) AS citation_count
            FROM citations ci
            JOIN chunks c ON c.chunk_id = ci.chunk_id
            GROUP BY c.source_id
        ) cc ON cc.source_id = cw.source_id
        WHERE COALESCE(cc.citation_count, 0) > 0
        ORDER BY citation_count DESC, cw.source_id
        """
    ).fetchall()
    return [
        {
            "source_id": r[0],
            "title": r[1],
            "total_chunks": r[2],
            "cited_chunks": r[3],
            "citation_count": r[4],
            "cited_fraction": round(r[3] / max(r[2], 1), 4),
            "citations_per_cited_chunk": round(r[4] / max(r[3], 1), 4),
        }
        for r in rows
    ]


def outlier_summary(conn) -> dict:
    """Aggregate outlier detection statistics."""
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    total_citations = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]

    word_outliers = len(chunk_word_outliers(conn, threshold=2.0))
    conf_outliers = len(edge_confidence_outliers(conn, threshold=2.0))

    conc = citation_concentration(conn)
    highly_concentrated = sum(1 for r in conc if r["cited_fraction"] < 0.5 and r["total_chunks"] >= 2)

    wc_vals = [r[0] for r in conn.execute("SELECT word_count FROM chunks").fetchall()]
    wc_mean, wc_sd = _stddev(wc_vals)

    conf_vals = [r[0] for r in conn.execute(
        "SELECT confidence FROM claim_edges WHERE confidence IS NOT NULL"
    ).fetchall()]
    conf_mean, conf_sd = _stddev(conf_vals)

    return {
        "total_chunks": total_chunks,
        "total_edges": total_edges,
        "total_citations": total_citations,
        "total_sources": total_sources,
        "chunk_word_outliers": word_outliers,
        "edge_confidence_outliers": conf_outliers,
        "highly_concentrated_sources": highly_concentrated,
        "corpus_word_mean": round(wc_mean, 2),
        "corpus_word_stddev": round(wc_sd, 2),
        "corpus_confidence_mean": round(conf_mean, 4),
        "corpus_confidence_stddev": round(conf_sd, 4),
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
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None),
        )

        # s1: c1 (10w), c2 (12w), c3 (11w), c4 (10w), c5s1 (11w), c6s1 (500w outlier)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "h", "claim", None, "t", "t", 10, "abc", 1000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "h", "claim", None, "t", "t", 12, "abc", 2000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "h", "claim", None, "t", "t", 11, "abc", 3000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 4, "h", "claim", None, "t", "t", 10, "abc", 4000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5s1", "s1", 5, "h", "claim", None, "t", "t", 11, "abc", 4500, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6s1", "s1", 6, "h", "claim", None, "t", "t", 500, "abc", 4600, 0, "accepted", None, t1),
        )
        # s2: c5 (50w), c6 (50w) -- no outliers (identical word counts)
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 1, "h", "claim", None, "t", "t", 50, "abc", 5000, 0, "accepted", None, t1),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s2", 2, "h", "claim", None, "t", "t", 50, "abc", 6000, 0, "accepted", None, t1),
        )

        # Edges: 6 supports at ~0.9, one outlier at 0.1
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.90, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c2", "c3", "supports", "text", 0.88, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c4", "supports", "text", 0.91, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e5", "c4", "c5s1", "supports", "text", 0.89, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e6", "c5s1", "c6s1", "supports", "text", 0.92, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e7", "c1", "c4", "supports", "text", 0.87, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e4", "c1", "c3", "supports", "text", 0.1, t1, None, None),
        )

        # Citations: concentrated on c1 only in s1
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "u://ref1", None, "url", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit2", "c1", "u://ref2", None, "url", None, 0, None),
        )
        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit3", "c1", "u://ref3", None, "url", None, 0, None),
        )
        conn.commit()

        # 1. chunk-word outliers: c6s1 (500w) is an outlier in s1
        cwo = chunk_word_outliers(conn, threshold=2.0)
        assert len(cwo) >= 1
        assert cwo[0]["chunk_id"] == "c6s1"
        ok += 1

        # 2. c6s1 z_score should be above threshold
        assert cwo[0]["z_score"] > 2.0
        ok += 1

        # 3. no outliers from s2 (identical word counts, stddev=0)
        s2_outliers = [r for r in cwo if r["source_id"] == "s2"]
        assert len(s2_outliers) == 0
        ok += 1

        # 4. edge confidence outliers: e4 (0.1) is an outlier among supports
        eco = edge_confidence_outliers(conn, threshold=1.5)
        assert len(eco) >= 1
        e4_rows = [r for r in eco if r["edge_id"] == "e4"]
        assert len(e4_rows) == 1
        ok += 1

        # 5. e4 z_score above threshold
        assert e4_rows[0]["z_score"] > 1.5
        ok += 1

        # 6. citation concentration: s1 has 3 citations on 1 of 4 chunks
        cc = citation_concentration(conn)
        s1_row = [r for r in cc if r["source_id"] == "s1"][0]
        assert s1_row["cited_chunks"] == 1
        assert s1_row["citation_count"] == 3
        ok += 1

        # 7. cited_fraction = 1/6
        assert s1_row["cited_fraction"] == round(1 / 6, 4)
        ok += 1

        # 8. citations_per_cited_chunk = 3/1 = 3.0
        assert s1_row["citations_per_cited_chunk"] == 3.0
        ok += 1

        # 9. s2 not in concentration list (no citations)
        s2_rows = [r for r in cc if r["source_id"] == "s2"]
        assert len(s2_rows) == 0
        ok += 1

        # 10. summary: chunk_word_outliers >= 1
        s = outlier_summary(conn)
        assert s["chunk_word_outliers"] >= 1
        ok += 1

        # 11. summary: total_chunks = 8
        assert s["total_chunks"] == 8
        ok += 1

        # 12. summary: highly_concentrated_sources >= 1 (s1 has cited_fraction 0.25 < 0.5)
        assert s["highly_concentrated_sources"] >= 1
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["corpus_word_mean"] == s["corpus_word_mean"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = outlier_summary(conn)
        assert s["total_chunks"] == 0
        assert s["chunk_word_outliers"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Cross-table outlier detection")
    ap.add_argument("command", choices=["chunk-words", "edge-confidence", "citation-concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS cross_table_outlier_detector selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "chunk-words":
        rows = chunk_word_outliers(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No chunk word count outliers found.")
            else:
                print(f"{'chunk_id':<12} {'source_id':<14} {'words':<8} {'status':<12} {'src_mean':<10} {'src_sd':<10} {'z_score'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['source_id']:<14} {r['word_count']:<8} {r['status']:<12} {r['source_mean']:<10} {r['source_stddev']:<10} {r['z_score']:.4f}")
    elif args.command == "edge-confidence":
        rows = edge_confidence_outliers(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge confidence outliers found.")
            else:
                print(f"{'edge_id':<12} {'type':<14} {'confidence':<12} {'type_mean':<12} {'type_sd':<10} {'z_score'}")
                for r in rows:
                    print(f"{r['edge_id']:<12} {r['edge_type']:<14} {r['confidence']:<12} {r['type_mean']:<12} {r['type_stddev']:<10} {r['z_score']:.4f}")
    elif args.command == "citation-concentration":
        rows = citation_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cited sources found.")
            else:
                print(f"{'source_id':<14} {'title':<20} {'chunks':<8} {'cited':<7} {'citations':<10} {'fraction':<10} {'per_cited'}")
                for r in rows:
                    print(f"{r['source_id']:<14} {r['title']:<20} {r['total_chunks']:<8} {r['cited_chunks']:<7} {r['citation_count']:<10} {r['cited_fraction']:<10.4f} {r['citations_per_cited_chunk']:.4f}")
    elif args.command == "summary":
        s = outlier_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
