#!/usr/bin/env python3
"""Domain edge depth: edge density and type distribution per knowledge domain.

tag_edge_correlation.py correlates tags with claim_edges.
domain_citation_profile.py correlates domains with citations.
No tool joins chunk_domains with claim_edges to measure which
knowledge domains have the highest edge connectivity, or which
edge types dominate each domain.

Usage:
    python tools/corpus/domain_edge_depth.py by-domain [--db PATH] [--json]
    python tools/corpus/domain_edge_depth.py by-edge-type [--db PATH] [--json]
    python tools/corpus/domain_edge_depth.py cross [--db PATH] [--json]
    python tools/corpus/domain_edge_depth.py summary [--db PATH] [--json]
    python tools/corpus/domain_edge_depth.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

_CD_DDL = (
    "CREATE TABLE IF NOT EXISTS chunk_domains ("
    "  chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),"
    "  domain TEXT NOT NULL,"
    "  score REAL NOT NULL,"
    "  classified_utc TEXT NOT NULL,"
    "  PRIMARY KEY (chunk_id, domain))"
)


def edge_density_by_domain(conn) -> list[dict]:
    """Edge density per domain."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain,
               COUNT(DISTINCT cd.chunk_id) AS classified_chunks,
               COUNT(DISTINCT e.edge_id) AS total_edges,
               ROUND(
                   COUNT(DISTINCT e.edge_id) * 1.0
                   / MAX(COUNT(DISTINCT cd.chunk_id), 1),
                   4
               ) AS edges_per_chunk,
               ROUND(AVG(cd.score), 4) AS avg_domain_score
        FROM chunk_domains cd
        LEFT JOIN claim_edges e
          ON e.source_chunk = cd.chunk_id
          OR e.target_chunk = cd.chunk_id
        GROUP BY cd.domain
        ORDER BY edges_per_chunk DESC, cd.domain
        """
    ).fetchall()
    return [
        {
            "domain": r[0],
            "classified_chunks": r[1],
            "total_edges": r[2],
            "edges_per_chunk": r[3],
            "avg_domain_score": r[4],
        }
        for r in rows
    ]


def domain_by_edge_type(conn) -> list[dict]:
    """Domain distribution per edge type."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(DISTINCT cd.domain) AS distinct_domains,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT cd.chunk_id) AS classified_endpoints
        FROM claim_edges e
        JOIN chunk_domains cd
          ON cd.chunk_id = e.source_chunk
          OR cd.chunk_id = e.target_chunk
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "distinct_domains": r[1],
            "edge_count": r[2],
            "classified_endpoints": r[3],
        }
        for r in rows
    ]


def domain_edge_cross(conn) -> list[dict]:
    """Full domain x edge_type cross-tabulation."""
    conn.execute(_CD_DDL)
    rows = conn.execute(
        """
        SELECT cd.domain, e.edge_type,
               COUNT(DISTINCT e.edge_id) AS count
        FROM chunk_domains cd
        JOIN claim_edges e
          ON e.source_chunk = cd.chunk_id
          OR e.target_chunk = cd.chunk_id
        GROUP BY cd.domain, e.edge_type
        ORDER BY cd.domain, count DESC
        """
    ).fetchall()
    return [
        {"domain": r[0], "edge_type": r[1], "count": r[2]}
        for r in rows
    ]


def domain_edge_summary(conn) -> dict:
    """Aggregate domain-edge statistics."""
    conn.execute(_CD_DDL)
    total_domains = conn.execute(
        "SELECT COUNT(DISTINCT domain) FROM chunk_domains"
    ).fetchone()[0]
    classified_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM chunk_domains"
    ).fetchone()[0]
    classified_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT cd.chunk_id)
        FROM chunk_domains cd
        JOIN claim_edges e
          ON e.source_chunk = cd.chunk_id
          OR e.target_chunk = cd.chunk_id
        """
    ).fetchone()[0]
    classified_without = classified_chunks - classified_with_edges
    edge_coverage = round(classified_with_edges / max(classified_chunks, 1), 4)

    edges_on_classified = conn.execute(
        """
        SELECT COUNT(DISTINCT e.edge_id)
        FROM chunk_domains cd
        JOIN claim_edges e
          ON e.source_chunk = cd.chunk_id
          OR e.target_chunk = cd.chunk_id
        """
    ).fetchone()[0]
    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]
    classified_edge_share = round(edges_on_classified / max(total_edges, 1), 4)

    by_domain = edge_density_by_domain(conn)
    densest = by_domain[0]["domain"] if by_domain and by_domain[0]["total_edges"] > 0 else None

    return {
        "total_domains": total_domains,
        "classified_chunks": classified_chunks,
        "classified_with_edges": classified_with_edges,
        "classified_without_edges": classified_without,
        "edge_coverage_rate": edge_coverage,
        "edges_on_classified": edges_on_classified,
        "classified_edge_share": classified_edge_share,
        "densest_domain": densest,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        conn.execute(_CD_DDL)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None),
        )
        for i in range(1, 6):
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"c{i}", "s1", i, "h", "claim", None, "t", "t", 10, "abc", i * 1000, 0, "accepted", None, t1),
            )

        # domains: c1 ml+web, c2 devops, c3 ml, c4 security (no edges)
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "ml", 0.9, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c1", "web", 0.7, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c2", "devops", 0.85, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c3", "ml", 0.8, t1))
        conn.execute("INSERT INTO chunk_domains VALUES (?,?,?,?)", ("c4", "security", 0.6, t1))

        # edges: c1->c2 supports, c1->c3 contradicts, c5->c3 refines
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text match", 0.9, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "semantic", 0.8, t1, None, None),
        )
        conn.execute(
            "INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c5", "c3", "refines", "detail", 0.7, t1, None, None),
        )
        conn.commit()

        # 1. ml has 3 edges (e1+e2 via c1, e2+e3 via c3)
        bd = edge_density_by_domain(conn)
        ml_row = [r for r in bd if r["domain"] == "ml"][0]
        assert ml_row["total_edges"] == 3, f"ml edges {ml_row['total_edges']}"
        ok += 1

        # 2. web has 2 edges (e1+e2 via c1)
        web_row = [r for r in bd if r["domain"] == "web"][0]
        assert web_row["total_edges"] == 2
        ok += 1

        # 3. devops has 1 edge (e1 via c2)
        devops_row = [r for r in bd if r["domain"] == "devops"][0]
        assert devops_row["total_edges"] == 1
        ok += 1

        # 4. security has 0 edges
        sec_row = [r for r in bd if r["domain"] == "security"][0]
        assert sec_row["total_edges"] == 0
        ok += 1

        # 5. domain_by_edge_type: supports has domains
        bt = domain_by_edge_type(conn)
        sup_row = [r for r in bt if r["edge_type"] == "supports"][0]
        assert sup_row["edge_count"] == 1
        ok += 1

        # 6. contradicts has domains
        con_row = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert con_row["edge_count"] == 1
        ok += 1

        # 7. refines has classified endpoints (c3)
        ref_row = [r for r in bt if r["edge_type"] == "refines"][0]
        assert ref_row["classified_endpoints"] >= 1
        ok += 1

        # 8. cross-tabulation has entries
        cr = domain_edge_cross(conn)
        assert len(cr) >= 1
        ok += 1

        # 9. ml/contradicts in cross
        ml_con = [r for r in cr if r["domain"] == "ml" and r["edge_type"] == "contradicts"]
        assert len(ml_con) == 1 and ml_con[0]["count"] == 1
        ok += 1

        # 10. summary: classified_with_edges is 3 (c1, c2, c3)
        s = domain_edge_summary(conn)
        assert s["classified_with_edges"] == 3
        ok += 1

        # 11. classified_without is 1 (c4)
        assert s["classified_without_edges"] == 1
        ok += 1

        # 12. edges_on_classified is 3
        assert s["edges_on_classified"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["edge_coverage_rate"] == s["edge_coverage_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = domain_edge_summary(conn)
        assert s["total_domains"] == 0
        assert s["classified_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Domain edge depth analysis")
    ap.add_argument("command", choices=["by-domain", "by-edge-type", "cross", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS domain_edge_depth selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-domain":
        rows = edge_density_by_domain(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No classified chunks found.")
            else:
                print(f"{'domain':<16} {'chunks':<8} {'edges':<8} {'edges/chunk':<12} {'avg_score'}")
                for r in rows:
                    print(f"{r['domain']:<16} {r['classified_chunks']:<8} {r['total_edges']:<8} {r['edges_per_chunk']:<12.4f} {r['avg_domain_score']:.4f}")
    elif args.command == "by-edge-type":
        rows = domain_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'edge_type':<16} {'domains':<10} {'edges':<8} {'classified_endpoints'}")
            for r in rows:
                print(f"{r['edge_type']:<16} {r['distinct_domains']:<10} {r['edge_count']:<8} {r['classified_endpoints']}")
    elif args.command == "cross":
        rows = domain_edge_cross(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(f"{'domain':<16} {'edge_type':<16} {'count'}")
            for r in rows:
                print(f"{r['domain']:<16} {r['edge_type']:<16} {r['count']}")
    elif args.command == "summary":
        s = domain_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
