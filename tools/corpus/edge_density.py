#!/usr/bin/env python3
"""Claim edge density: how interconnected the claim network is.

Measures edges per chunk across sources, domains, and chunk kinds,
revealing which parts of the corpus are tightly linked and which are
isolated.  High density indicates well-connected knowledge; low
density flags content islands.

Usage:
    python tools/corpus/edge_density.py density [--db PATH] [--json]
    python tools/corpus/edge_density.py islands [--db PATH] [--json]
    python tools/corpus/edge_density.py summary [--db PATH] [--json]
    python tools/corpus/edge_density.py selftest
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


def edge_density(conn) -> list[dict]:
    """Per-source edge density: edges per accepted chunk."""
    sources = conn.execute(
        "SELECT s.source_id, s.title, s.kind, "
        "count(DISTINCT c.chunk_id) as chunk_count "
        "FROM sources s "
        "JOIN chunks c ON s.source_id = c.source_id "
        "WHERE c.status = 'accepted' "
        "GROUP BY s.source_id"
    ).fetchall()

    if not sources:
        return []

    results = []
    for src_id, title, kind, chunk_count in sources:
        edge_count = conn.execute(
            "SELECT count(*) FROM claim_edges "
            "WHERE source_chunk IN "
            "(SELECT chunk_id FROM chunks WHERE source_id = ?) "
            "OR target_chunk IN "
            "(SELECT chunk_id FROM chunks WHERE source_id = ?)",
            (src_id, src_id),
        ).fetchone()[0]

        density = edge_count / chunk_count if chunk_count > 0 else 0.0

        edge_types = dict(conn.execute(
            "SELECT edge_type, count(*) FROM claim_edges "
            "WHERE source_chunk IN "
            "(SELECT chunk_id FROM chunks WHERE source_id = ?) "
            "OR target_chunk IN "
            "(SELECT chunk_id FROM chunks WHERE source_id = ?) "
            "GROUP BY edge_type",
            (src_id, src_id),
        ).fetchall())

        results.append({
            "source_id": src_id,
            "title": title,
            "kind": kind,
            "chunk_count": chunk_count,
            "edge_count": edge_count,
            "density": round(density, 4),
            "edge_types": edge_types,
        })

    results.sort(key=lambda r: r["density"], reverse=True)
    return results


def island_chunks(conn) -> list[dict]:
    """Accepted chunks with no claim edges (isolated knowledge)."""
    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.heading_path, c.kind, "
        "c.word_count FROM chunks c "
        "WHERE c.status = 'accepted' "
        "AND c.chunk_id NOT IN "
        "(SELECT source_chunk FROM claim_edges) "
        "AND c.chunk_id NOT IN "
        "(SELECT target_chunk FROM claim_edges)"
    ).fetchall()

    results = []
    for chunk_id, source_id, heading, kind, word_count in rows:
        results.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "heading": heading,
            "kind": kind,
            "word_count": word_count,
        })

    results.sort(key=lambda r: r["word_count"], reverse=True)
    return results


def density_summary(conn) -> dict:
    """Aggregate edge density statistics."""
    total_accepted = conn.execute(
        "SELECT count(*) FROM chunks WHERE status = 'accepted'"
    ).fetchone()[0]

    if total_accepted == 0:
        return {
            "total_accepted_chunks": 0,
            "total_edges": 0,
            "overall_density": 0.0,
            "connected_chunks": 0,
            "island_chunks": 0,
            "island_rate": 0.0,
            "by_edge_type": {},
            "by_kind": {},
        }

    total_edges = conn.execute(
        "SELECT count(*) FROM claim_edges"
    ).fetchone()[0]

    connected_source = conn.execute(
        "SELECT count(DISTINCT source_chunk) FROM claim_edges"
    ).fetchone()[0]
    connected_target = conn.execute(
        "SELECT count(DISTINCT target_chunk) FROM claim_edges"
    ).fetchone()[0]

    connected_ids = conn.execute(
        "SELECT DISTINCT source_chunk FROM claim_edges "
        "UNION "
        "SELECT DISTINCT target_chunk FROM claim_edges"
    ).fetchall()
    connected_count = len(connected_ids)

    island_count = total_accepted - connected_count
    island_rate = island_count / total_accepted if total_accepted > 0 else 0.0

    by_type = dict(conn.execute(
        "SELECT edge_type, count(*) FROM claim_edges GROUP BY edge_type"
    ).fetchall())

    by_kind: dict[str, dict] = {}
    kind_rows = conn.execute(
        "SELECT c.kind, count(DISTINCT c.chunk_id) as total, "
        "count(DISTINCT e.edge_id) as edges "
        "FROM chunks c "
        "LEFT JOIN claim_edges e ON c.chunk_id = e.source_chunk "
        "OR c.chunk_id = e.target_chunk "
        "WHERE c.status = 'accepted' "
        "GROUP BY c.kind"
    ).fetchall()
    for kind, total, edges in kind_rows:
        by_kind[kind] = {
            "chunks": total,
            "edges": edges,
            "density": round(edges / total, 4) if total > 0 else 0.0,
        }

    return {
        "total_accepted_chunks": total_accepted,
        "total_edges": total_edges,
        "overall_density": round(
            total_edges / total_accepted, 4) if total_accepted > 0 else 0.0,
        "connected_chunks": connected_count,
        "island_chunks": island_count,
        "island_rate": round(island_rate, 4),
        "by_edge_type": by_type,
        "by_kind": by_kind,
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

        for sid in ("s1", "s2"):
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
            ("c1", "s1", "Heading A", "claim", "text about topic a"),
            ("c2", "s1", "Heading B", "claim", "text about topic b"),
            ("c3", "s1", "Heading C", "code", "function example code"),
            ("c4", "s2", "Heading D", "claim", "text about topic d"),
            ("c5", "s2", "Heading E", "prose", "isolated prose content"),
        ]
        for i, (cid, sid, heading, kind, text) in enumerate(chunk_data):
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, i, heading, kind, "en",
                 text, text, len(text.split()), f"n_{cid}",
                 "accepted", now),
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) VALUES "
            "(?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c2", "supports", "textual", 0.9, now),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) VALUES "
            "(?, ?, ?, ?, ?, ?, ?)",
            ("e2", "c1", "c4", "contradicts", "semantic", 0.7, now),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) VALUES "
            "(?, ?, ?, ?, ?, ?, ?)",
            ("e3", "c2", "c3", "refines", "structural", 0.8, now),
        )

        conn.commit()

        # 1: density returns results for both sources
        dens = edge_density(conn)
        assert len(dens) == 2
        checks += 1

        # 2: sorted by density descending
        densities = [d["density"] for d in dens]
        assert densities == sorted(densities, reverse=True)
        checks += 1

        # 3: s1 has higher density (3 edges, 3 chunks)
        s1 = next(d for d in dens if d["source_id"] == "s1")
        assert s1["edge_count"] >= 2
        assert s1["density"] > 0
        checks += 1

        # 4: edge_types breakdown present
        assert len(s1["edge_types"]) > 0
        checks += 1

        # 5: island chunks returns isolated chunks
        islands = island_chunks(conn)
        island_ids = [i["chunk_id"] for i in islands]
        assert "c5" in island_ids
        checks += 1

        # 6: connected chunks excluded from islands
        assert "c1" not in island_ids
        assert "c2" not in island_ids
        checks += 1

        # 7: islands sorted by word_count descending
        if len(islands) > 1:
            wcs = [i["word_count"] for i in islands]
            assert wcs == sorted(wcs, reverse=True)
        checks += 1

        # 8: summary has required keys
        summary = density_summary(conn)
        assert summary["total_accepted_chunks"] == 5
        assert summary["total_edges"] == 3
        assert "island_rate" in summary
        checks += 1

        # 9: connected + island = total
        assert (summary["connected_chunks"]
                + summary["island_chunks"]) == summary["total_accepted_chunks"]
        checks += 1

        # 10: overall density is positive
        assert summary["overall_density"] > 0
        checks += 1

        # 11: by_edge_type has entries
        assert len(summary["by_edge_type"]) > 0
        assert "supports" in summary["by_edge_type"]
        checks += 1

        # 12: by_kind has entries
        assert len(summary["by_kind"]) > 0
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dens)
        _ = json.dumps(islands)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = edge_density(conn2)
        assert empty == []
        empty_summary = density_summary(conn2)
        assert empty_summary["total_accepted_chunks"] == 0
        checks += 1

    print(f"PASS edge_density selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Claim edge density: network interconnectedness"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dens = sub.add_parser("density",
                            help="Per-source edge density")
    p_dens.add_argument("--db", default=DEFAULT_DB)
    p_dens.add_argument("--json", action="store_true")

    p_island = sub.add_parser("islands",
                              help="Chunks with no claim edges")
    p_island.add_argument("--db", default=DEFAULT_DB)
    p_island.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Density statistics")
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

    if args.cmd == "density":
        results = edge_density(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['density']:.3f}  {r['edge_count']:3d} edges  "
                      f"{r['chunk_count']:3d} chunks  "
                      f"{r['source_id'][:12]:12s}  {r['title']}")

    elif args.cmd == "islands":
        results = island_chunks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("All chunks participate in claim edges.")
            else:
                print(f"{len(results)} isolated chunks:")
                for c in results:
                    print(f"  {c['word_count']:5d}w  {c['kind']:6s}  "
                          f"{c['chunk_id'][:12]:12s}  {c['heading']}")

    elif args.cmd == "summary":
        result = density_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Edge Density: {result['overall_density']:.3f} "
                  f"({result['total_edges']} edges / "
                  f"{result['total_accepted_chunks']} chunks)")
            print(f"  Connected: {result['connected_chunks']}  "
                  f"Islands: {result['island_chunks']} "
                  f"({result['island_rate']:.1%})")
            if result["by_edge_type"]:
                types = ", ".join(
                    f"{t}: {c}" for t, c
                    in sorted(result["by_edge_type"].items()))
                print(f"  Edge types: {types}")

    conn.close()


if __name__ == "__main__":
    main()
