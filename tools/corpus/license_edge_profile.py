#!/usr/bin/env python3
"""License edge profile: how licenses distribute across claim edges.

license_citation_profile.py profiles licenses by citation counts.
publisher_edge_profile.py profiles publishers by claim edges.
No tool cross-tabulates sources.license_spdx with claim_edges to measure
which licenses carry the most claim edges, or how edge types distribute
across licenses.

Usage:
    python tools/corpus/license_edge_profile.py by-license [--db PATH] [--json]
    python tools/corpus/license_edge_profile.py by-type [--db PATH] [--json]
    python tools/corpus/license_edge_profile.py concentration [--db PATH] [--json]
    python tools/corpus/license_edge_profile.py summary [--db PATH] [--json]
    python tools/corpus/license_edge_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def edges_by_license(conn) -> list[dict]:
    """Edge statistics per license."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT c.chunk_id) AS chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        ORDER BY edge_count DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "edges_per_chunk": round(r[2] / max(r[1], 1), 4),
        }
        for r in rows
    ]


def licenses_by_edge_type(conn) -> list[dict]:
    """License distribution per edge type."""
    rows = conn.execute(
        """
        SELECT e.edge_type,
               COUNT(DISTINCT s.license_spdx) AS distinct_licenses,
               COUNT(DISTINCT c.chunk_id) AS chunks_involved,
               COUNT(DISTINCT e.edge_id) AS edge_count
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY e.edge_type
        ORDER BY edge_count DESC, e.edge_type
        """
    ).fetchall()
    return [
        {
            "edge_type": r[0],
            "distinct_licenses": r[1],
            "chunks_involved": r[2],
            "edge_count": r[3],
        }
        for r in rows
    ]


def license_edge_concentration(conn) -> list[dict]:
    """Per-license edge concentration ordered by edge type diversity."""
    rows = conn.execute(
        """
        SELECT s.license_spdx,
               COUNT(DISTINCT c.chunk_id) AS chunks_with_edges,
               COUNT(DISTINCT e.edge_id) AS edge_count,
               COUNT(DISTINCT e.edge_type) AS edge_types
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        JOIN (
            SELECT edge_id, source_chunk AS chunk_id, edge_type FROM claim_edges
            UNION ALL
            SELECT edge_id, target_chunk AS chunk_id, edge_type FROM claim_edges
        ) e ON e.chunk_id = c.chunk_id
        GROUP BY s.license_spdx
        ORDER BY edge_types DESC, edge_count DESC, s.license_spdx
        """
    ).fetchall()
    return [
        {
            "license_spdx": r[0],
            "chunks_with_edges": r[1],
            "edge_count": r[2],
            "edge_types": r[3],
            "type_ratio": round(r[3] / max(r[2], 1), 4),
        }
        for r in rows
    ]


def license_edge_summary(conn) -> dict:
    """Aggregate license-edge statistics."""
    total_licenses = conn.execute(
        "SELECT COUNT(DISTINCT license_spdx) FROM sources"
    ).fetchone()[0]

    licenses_with_edges = conn.execute(
        """
        SELECT COUNT(DISTINCT s.license_spdx)
        FROM sources s
        JOIN chunks c ON c.source_id = s.source_id
        WHERE c.chunk_id IN (
            SELECT source_chunk FROM claim_edges
            UNION
            SELECT target_chunk FROM claim_edges
        )
        """
    ).fetchone()[0]

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges"
    ).fetchone()[0]

    total_edge_types = conn.execute(
        "SELECT COUNT(DISTINCT edge_type) FROM claim_edges"
    ).fetchone()[0]

    multi_type_licenses = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT s.license_spdx
            FROM sources s
            JOIN chunks c ON c.source_id = s.source_id
            JOIN (
                SELECT source_chunk AS chunk_id, edge_type FROM claim_edges
                UNION ALL
                SELECT target_chunk AS chunk_id, edge_type FROM claim_edges
            ) e ON e.chunk_id = c.chunk_id
            GROUP BY s.license_spdx
            HAVING COUNT(DISTINCT e.edge_type) > 1
        )
        """
    ).fetchone()[0]

    return {
        "total_licenses": total_licenses,
        "licenses_with_edges": licenses_with_edges,
        "license_edge_rate": round(licenses_with_edges / max(total_licenses, 1), 4),
        "total_edges": total_edges,
        "total_edge_types": total_edge_types,
        "multi_type_licenses": multi_type_licenses,
        "multi_type_rate": round(multi_type_licenses / max(licenses_with_edges, 1), 4),
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        # s1 MIT, s2 Apache-2.0, s3 CC-BY-4.0 (no edges)
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "Apache-2.0", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s3", "u://s3", "local_md", "S3", "CC-BY-4.0", "vendor", "self", None, None, t1, None, None, "live", "ghi", 150, None))

        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "abc", 1000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "methods", "claim", None, "t", "t", 30, "def", 1001, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 25, "ghi", 2000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s3", 1, "results", "claim", None, "t", "t", 35, "jkl", 3000, 0, "accepted", None, t1))

        # e1: c1->c2 supports (MIT internal), e2: c1->c3 contradicts (MIT->Apache cross)
        # e3: c3->c2 refines (Apache->MIT cross)
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e1", "c1", "c2", "supports", "text", 0.9, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e2", "c1", "c3", "contradicts", "text", 0.8, t1, None, None))
        conn.execute("INSERT INTO claim_edges VALUES (?,?,?,?,?,?,?,?,?)",
            ("e3", "c3", "c2", "refines", "text", 0.7, t1, None, None))
        conn.commit()

        # 1. by-license: MIT has 2 chunks with edges (c1, c2)
        bl = edges_by_license(conn)
        mit = [r for r in bl if r["license_spdx"] == "MIT"][0]
        assert mit["chunks_with_edges"] == 2
        ok += 1

        # 2. MIT has 3 distinct edges (e1, e2, e3)
        assert mit["edge_count"] == 3, f"expected 3, got {mit['edge_count']}"
        ok += 1

        # 3. Apache-2.0 has 1 chunk with edges (c3)
        apache = [r for r in bl if r["license_spdx"] == "Apache-2.0"][0]
        assert apache["chunks_with_edges"] == 1
        ok += 1

        # 4. CC-BY-4.0 not in by-license (c4 has no edges)
        ccby = [r for r in bl if r["license_spdx"] == "CC-BY-4.0"]
        assert len(ccby) == 0
        ok += 1

        # 5. by-type: "supports" spans 1 license (MIT)
        bt = licenses_by_edge_type(conn)
        supports = [r for r in bt if r["edge_type"] == "supports"][0]
        assert supports["distinct_licenses"] == 1
        ok += 1

        # 6. "contradicts" spans 2 licenses (MIT, Apache)
        contradicts = [r for r in bt if r["edge_type"] == "contradicts"][0]
        assert contradicts["distinct_licenses"] == 2
        ok += 1

        # 7. "refines" spans 2 licenses (Apache, MIT)
        refines = [r for r in bt if r["edge_type"] == "refines"][0]
        assert refines["distinct_licenses"] == 2
        ok += 1

        # 8. concentration: MIT has 3 edge types
        conc = license_edge_concentration(conn)
        c_mit = [r for r in conc if r["license_spdx"] == "MIT"][0]
        assert c_mit["edge_types"] == 3
        ok += 1

        # 9. Apache has 2 edge types (contradicts, refines)
        c_apache = [r for r in conc if r["license_spdx"] == "Apache-2.0"][0]
        assert c_apache["edge_types"] == 2
        ok += 1

        # 10. summary: total_licenses = 3
        s = license_edge_summary(conn)
        assert s["total_licenses"] == 3
        ok += 1

        # 11. licenses_with_edges = 2 (MIT, Apache)
        assert s["licenses_with_edges"] == 2
        ok += 1

        # 12. total_edges = 3
        assert s["total_edges"] == 3
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["multi_type_rate"] == s["multi_type_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = license_edge_summary(conn)
        assert s["total_licenses"] == 0
        assert s["licenses_with_edges"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="License edge profile analysis")
    ap.add_argument("command", choices=["by-license", "by-type", "concentration", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS license_edge_profile selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "by-license":
        rows = edges_by_license(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license edge data found.")
            else:
                print(f"{'license':<16} {'chunks':<8} {'edges':<8} {'types':<8} {'edges/chunk'}")
                for r in rows:
                    print(f"{r['license_spdx']:<16} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['edges_per_chunk']:.4f}")
    elif args.command == "by-type":
        rows = licenses_by_edge_type(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No edge type data found.")
            else:
                print(f"{'edge_type':<15} {'licenses':<10} {'chunks':<8} {'edges'}")
                for r in rows:
                    print(f"{r['edge_type']:<15} {r['distinct_licenses']:<10} {r['chunks_involved']:<8} {r['edge_count']}")
    elif args.command == "concentration":
        rows = license_edge_concentration(conn)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No license edge data found.")
            else:
                print(f"{'license':<16} {'chunks':<8} {'edges':<8} {'types':<8} {'type_ratio'}")
                for r in rows:
                    print(f"{r['license_spdx']:<16} {r['chunks_with_edges']:<8} {r['edge_count']:<8} {r['edge_types']:<8} {r['type_ratio']:.4f}")
    elif args.command == "summary":
        s = license_edge_summary(conn)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
