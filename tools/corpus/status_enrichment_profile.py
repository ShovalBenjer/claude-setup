#!/usr/bin/env python3
"""Status enrichment profile: how chunk status relates to enrichment depth.

source_enrichment_completeness.py measures enrichment per source.
cross_table_outlier_detector.py finds statistical anomalies.
No tool measures whether accepted chunks carry richer enrichment
than quarantined or rejected chunks, or how each enrichment type
distributes across chunk statuses.

Usage:
    python tools/corpus/status_enrichment_profile.py by-status [--db PATH] [--json]
    python tools/corpus/status_enrichment_profile.py by-type [--db PATH] [--json]
    python tools/corpus/status_enrichment_profile.py gaps [--db PATH] [--json]
    python tools/corpus/status_enrichment_profile.py summary [--db PATH] [--json]
    python tools/corpus/status_enrichment_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def enrichment_by_status(conn) -> list[dict]:
    """Enrichment depth per chunk status."""
    rows = conn.execute(
        """
        SELECT c.status,
               COUNT(c.chunk_id) AS chunk_count,
               COALESCE(SUM(c.word_count), 0) AS total_words,
               COALESCE(tg.tagged, 0) AS tagged_chunks,
               COALESCE(dm.classified, 0) AS classified_chunks,
               COALESCE(ci.cited, 0) AS cited_chunks,
               COALESCE(ed.edged, 0) AS edged_chunks,
               COALESCE(ar.with_artifacts, 0) AS artifact_chunks
        FROM chunks c
        LEFT JOIN (
            SELECT c2.status, COUNT(DISTINCT ct.chunk_id) AS tagged
            FROM chunk_tags ct JOIN chunks c2 ON c2.chunk_id = ct.chunk_id
            GROUP BY c2.status
        ) tg ON tg.status = c.status
        LEFT JOIN (
            SELECT c2.status, COUNT(DISTINCT cd.chunk_id) AS classified
            FROM chunk_domains cd JOIN chunks c2 ON c2.chunk_id = cd.chunk_id
            GROUP BY c2.status
        ) dm ON dm.status = c.status
        LEFT JOIN (
            SELECT c2.status, COUNT(DISTINCT ci.chunk_id) AS cited
            FROM citations ci JOIN chunks c2 ON c2.chunk_id = ci.chunk_id
            GROUP BY c2.status
        ) ci ON ci.status = c.status
        LEFT JOIN (
            SELECT c2.status, COUNT(DISTINCT e.chunk_id) AS edged
            FROM (
                SELECT source_chunk AS chunk_id FROM claim_edges
                UNION
                SELECT target_chunk FROM claim_edges
            ) e JOIN chunks c2 ON c2.chunk_id = e.chunk_id
            GROUP BY c2.status
        ) ed ON ed.status = c.status
        LEFT JOIN (
            SELECT c2.status, COUNT(DISTINCT a.chunk_id) AS with_artifacts
            FROM artifacts a JOIN chunks c2 ON c2.chunk_id = a.chunk_id
            GROUP BY c2.status
        ) ar ON ar.status = c.status
        GROUP BY c.status
        ORDER BY chunk_count DESC, c.status
        """
    ).fetchall()
    return [
        {
            "status": r[0],
            "chunk_count": r[1],
            "total_words": r[2],
            "tagged_chunks": r[3],
            "classified_chunks": r[4],
            "cited_chunks": r[5],
            "edged_chunks": r[6],
            "artifact_chunks": r[7],
            "enrichment_rate": round(
                (min(r[3], 1) + min(r[4], 1) + min(r[5], 1) + min(r[6], 1) + min(r[7], 1))
                / 5, 4
            ) if r[1] > 0 else 0.0,
        }
        for r in rows
    ]


def enrichment_type_by_status(conn) -> list[dict]:
    """Per-enrichment-type counts by chunk status."""
    queries = [
        ("tags", "SELECT c.status, COUNT(*) FROM chunk_tags ct JOIN chunks c ON c.chunk_id = ct.chunk_id GROUP BY c.status"),
        ("domains", "SELECT c.status, COUNT(*) FROM chunk_domains cd JOIN chunks c ON c.chunk_id = cd.chunk_id GROUP BY c.status"),
        ("citations", "SELECT c.status, COUNT(*) FROM citations ci JOIN chunks c ON c.chunk_id = ci.chunk_id GROUP BY c.status"),
        ("edges", """SELECT c.status, COUNT(*) FROM (
            SELECT source_chunk AS chunk_id, edge_id FROM claim_edges
            UNION ALL
            SELECT target_chunk, edge_id FROM claim_edges
        ) e JOIN chunks c ON c.chunk_id = e.chunk_id GROUP BY c.status"""),
        ("artifacts", "SELECT c.status, COUNT(*) FROM artifacts a JOIN chunks c ON c.chunk_id = a.chunk_id GROUP BY c.status"),
    ]
    results = []
    for etype, sql in queries:
        rows = conn.execute(sql).fetchall()
        for r in rows:
            results.append({
                "enrichment_type": etype,
                "status": r[0],
                "count": r[1],
            })
    results.sort(key=lambda x: (x["enrichment_type"], x["status"]))
    return results


def status_enrichment_gaps(conn) -> list[dict]:
    """Chunks missing enrichment, grouped by status."""
    rows = conn.execute(
        """
        SELECT c.chunk_id, c.source_id, c.status, c.word_count,
               CASE WHEN tg.chunk_id IS NOT NULL THEN 1 ELSE 0 END AS has_tags,
               CASE WHEN dm.chunk_id IS NOT NULL THEN 1 ELSE 0 END AS has_domains,
               CASE WHEN ci.chunk_id IS NOT NULL THEN 1 ELSE 0 END AS has_citations,
               CASE WHEN ed.chunk_id IS NOT NULL THEN 1 ELSE 0 END AS has_edges,
               CASE WHEN ar.chunk_id IS NOT NULL THEN 1 ELSE 0 END AS has_artifacts
        FROM chunks c
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_tags) tg ON tg.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM chunk_domains) dm ON dm.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM citations) ci ON ci.chunk_id = c.chunk_id
        LEFT JOIN (
            SELECT DISTINCT chunk_id FROM (
                SELECT source_chunk AS chunk_id FROM claim_edges
                UNION
                SELECT target_chunk FROM claim_edges
            )
        ) ed ON ed.chunk_id = c.chunk_id
        LEFT JOIN (SELECT DISTINCT chunk_id FROM artifacts) ar ON ar.chunk_id = c.chunk_id
        WHERE tg.chunk_id IS NULL
           OR dm.chunk_id IS NULL
           OR ci.chunk_id IS NULL
           OR ed.chunk_id IS NULL
           OR ar.chunk_id IS NULL
        ORDER BY c.status, c.chunk_id
        """
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "status": r[2],
            "word_count": r[3],
            "has_tags": bool(r[4]),
            "has_domains": bool(r[5]),
            "has_citations": bool(r[6]),
            "has_edges": bool(r[7]),
            "has_artifacts": bool(r[8]),
            "dimensions_hit": r[4] + r[5] + r[6] + r[7] + r[8],
        }
        for r in rows
    ]


def status_enrichment_summary(conn) -> dict:
    """Aggregate status-enrichment statistics."""
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    statuses = conn.execute(
        "SELECT status, COUNT(*) FROM chunks GROUP BY status ORDER BY status"
    ).fetchall()

    accepted = sum(r[1] for r in statuses if r[0] == "accepted")
    non_accepted = total - accepted

    by_status = enrichment_by_status(conn)
    acc_row = next((r for r in by_status if r["status"] == "accepted"), None)
    acc_tagged = acc_row["tagged_chunks"] if acc_row else 0
    acc_classified = acc_row["classified_chunks"] if acc_row else 0

    gaps = status_enrichment_gaps(conn)
    accepted_gaps = sum(1 for g in gaps if g["status"] == "accepted")

    return {
        "total_chunks": total,
        "accepted_chunks": accepted,
        "non_accepted_chunks": non_accepted,
        "status_count": len(statuses),
        "accepted_tagged": acc_tagged,
        "accepted_classified": acc_classified,
        "accepted_with_gaps": accepted_gaps,
        "gap_rate": round(accepted_gaps / max(accepted, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )

        # c1 accepted (tagged, classified, cited), c2 accepted (tagged only), c3 quarantined (nothing)
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "h", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "h", "claim", None, "t", "t", 30, "abc", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s1", 3, "h", "claim", None, "t", "t", 10, "abc", 3000, 0, "quarantined", None, t1))

        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c1", "law", 0.9, t1))
        conn.execute("INSERT INTO chunk_tags VALUES (?,?,?,?)", ("c2", "tech", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "legal", 0.95, t1))
        conn.execute("INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit1", "c1", "u://ref1", None, "url", None, 0, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.commit()

        # 1. by-status: accepted has 2 chunks
        bs = enrichment_by_status(conn)
        acc = [r for r in bs if r["status"] == "accepted"][0]
        assert acc["chunk_count"] == 2
        ok += 1

        # 2. accepted tagged_chunks = 2 (c1, c2)
        assert acc["tagged_chunks"] == 2
        ok += 1

        # 3. accepted classified_chunks = 1 (c1 only)
        assert acc["classified_chunks"] == 1
        ok += 1

        # 4. quarantined has 0 enrichment
        quar = [r for r in bs if r["status"] == "quarantined"][0]
        assert quar["tagged_chunks"] == 0
        assert quar["classified_chunks"] == 0
        ok += 1

        # 5. by-type: tags for accepted = 2
        bt = enrichment_type_by_status(conn)
        tag_acc = [r for r in bt if r["enrichment_type"] == "tags" and r["status"] == "accepted"]
        assert len(tag_acc) == 1
        assert tag_acc[0]["count"] == 2
        ok += 1

        # 6. citations for accepted = 1
        cit_acc = [r for r in bt if r["enrichment_type"] == "citations" and r["status"] == "accepted"]
        assert len(cit_acc) == 1
        assert cit_acc[0]["count"] == 1
        ok += 1

        # 7. gaps: c2 missing domains, citations, edges, artifacts
        gaps = status_enrichment_gaps(conn)
        c2_gap = [g for g in gaps if g["chunk_id"] == "c2"][0]
        assert c2_gap["has_tags"] is True
        assert c2_gap["has_domains"] is False
        ok += 1

        # 8. c3 missing everything (5 dimensions)
        c3_gap = [g for g in gaps if g["chunk_id"] == "c3"][0]
        assert c3_gap["dimensions_hit"] == 0
        ok += 1

        # 9. c1 still has a gap (missing artifacts)
        c1_gap = [g for g in gaps if g["chunk_id"] == "c1"][0]
        assert c1_gap["has_artifacts"] is False
        assert c1_gap["dimensions_hit"] == 4
        ok += 1

        # 10. summary: accepted_chunks = 2
        s = status_enrichment_summary(conn)
        assert s["accepted_chunks"] == 2
        ok += 1

        # 11. summary: accepted_tagged = 2
        assert s["accepted_tagged"] == 2
        ok += 1

        # 12. summary: accepted_with_gaps = 2 (c1 missing artifacts, c2 missing domains+citations+edges+artifacts)
        assert s["accepted_with_gaps"] == 2
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["gap_rate"] == s["gap_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_tags (chunk_id TEXT, tag TEXT, score REAL, tagged_utc TEXT, PRIMARY KEY(chunk_id, tag))")
        conn.execute("CREATE TABLE IF NOT EXISTS chunk_domains (chunk_id TEXT, domain TEXT, score REAL, classified_utc TEXT, PRIMARY KEY(chunk_id, domain))")
        s = status_enrichment_summary(conn)
        assert s["total_chunks"] == 0
        assert s["accepted_with_gaps"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Status enrichment profile analysis")
    ap.add_argument("command", choices=["by-status", "by-type", "gaps", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS status_enrichment_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-status":
        rows = enrichment_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No chunks found.")
            else:
                print(f"{'status':<14} {'chunks':<8} {'words':<8} {'tagged':<8} {'classified':<12} {'cited':<7} {'edged':<7} {'artifacts':<10} {'enr_rate'}")
                for r in rows:
                    print(f"{r['status']:<14} {r['chunk_count']:<8} {r['total_words']:<8} {r['tagged_chunks']:<8} {r['classified_chunks']:<12} {r['cited_chunks']:<7} {r['edged_chunks']:<7} {r['artifact_chunks']:<10} {r['enrichment_rate']:.4f}")
    elif args.command == "by-type":
        rows = enrichment_type_by_status(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No enrichment found.")
            else:
                print(f"{'type':<14} {'status':<14} {'count'}")
                for r in rows:
                    print(f"{r['enrichment_type']:<14} {r['status']:<14} {r['count']}")
    elif args.command == "gaps":
        rows = status_enrichment_gaps(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No gaps found.")
            else:
                print(f"{'chunk_id':<12} {'source_id':<14} {'status':<14} {'words':<8} {'tags':<6} {'doms':<6} {'cites':<7} {'edges':<7} {'arts':<6} {'dims'}")
                for r in rows:
                    print(f"{r['chunk_id']:<12} {r['source_id']:<14} {r['status']:<14} {r['word_count']:<8} {str(r['has_tags']):<6} {str(r['has_domains']):<6} {str(r['has_citations']):<7} {str(r['has_edges']):<7} {str(r['has_artifacts']):<6} {r['dimensions_hit']}")
    elif args.command == "summary":
        s = status_enrichment_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
