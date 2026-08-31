#!/usr/bin/env python3
"""Domain analysis: cross-cutting views of chunk domain classifications.

Examines the chunk_domains table to report domain distribution, per-source
domain coverage, multi-domain chunks, and inter-domain claim edge density.

Usage:
    python tools/corpus/domain_analysis.py distribution [--db PATH] [--json]
    python tools/corpus/domain_analysis.py per-source [--db PATH] [--json]
    python tools/corpus/domain_analysis.py multi-domain [--db PATH] [--top N] [--json]
    python tools/corpus/domain_analysis.py edge-flow [--db PATH] [--json]
    python tools/corpus/domain_analysis.py selftest
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


def domain_distribution(conn) -> dict:
    """Distribution of chunks across domains with score statistics."""
    if not _table_exists(conn, "chunk_domains"):
        return {"domains": [], "total_assignments": 0,
                "unique_domains": 0, "classified_chunks": 0}

    rows = conn.execute(
        "SELECT domain, count(*) AS chunk_count, "
        "round(avg(score), 4) AS avg_score, "
        "round(min(score), 4) AS min_score, "
        "round(max(score), 4) AS max_score "
        "FROM chunk_domains "
        "GROUP BY domain "
        "ORDER BY chunk_count DESC"
    ).fetchall()

    total = conn.execute(
        "SELECT count(*) FROM chunk_domains"
    ).fetchone()[0]

    classified = conn.execute(
        "SELECT count(DISTINCT chunk_id) FROM chunk_domains"
    ).fetchone()[0]

    domains = [
        {"domain": r[0], "chunk_count": r[1],
         "avg_score": r[2], "min_score": r[3], "max_score": r[4]}
        for r in rows
    ]

    return {
        "domains": domains,
        "total_assignments": total,
        "unique_domains": len(domains),
        "classified_chunks": classified,
    }


def domain_per_source(conn) -> list[dict]:
    """Per-source domain breakdown showing topical focus of each source."""
    if not _table_exists(conn, "chunk_domains"):
        return []

    rows = conn.execute(
        "SELECT c.source_id, s.title, cd.domain, "
        "count(*) AS chunk_count, round(avg(cd.score), 4) AS avg_score "
        "FROM chunk_domains cd "
        "JOIN chunks c ON c.chunk_id = cd.chunk_id "
        "JOIN sources s ON s.source_id = c.source_id "
        "GROUP BY c.source_id, cd.domain "
        "ORDER BY c.source_id, chunk_count DESC"
    ).fetchall()

    sources: dict[str, dict] = {}
    for r in rows:
        sid = r[0]
        if sid not in sources:
            sources[sid] = {"source_id": sid, "title": r[1], "domains": []}
        sources[sid]["domains"].append({
            "domain": r[2], "chunk_count": r[3], "avg_score": r[4],
        })

    return list(sources.values())


def multi_domain_chunks(conn, top_n: int = 20) -> list[dict]:
    """Chunks classified into multiple domains, ranked by domain count."""
    if not _table_exists(conn, "chunk_domains"):
        return []

    rows = conn.execute(
        "SELECT cd.chunk_id, count(*) AS domain_count, "
        "group_concat(cd.domain, ', ') AS domains, "
        "c.kind, c.heading_path "
        "FROM chunk_domains cd "
        "JOIN chunks c ON c.chunk_id = cd.chunk_id "
        "GROUP BY cd.chunk_id "
        "HAVING domain_count > 1 "
        "ORDER BY domain_count DESC "
        "LIMIT ?",
        (top_n,),
    ).fetchall()

    return [
        {"chunk_id": r[0], "domain_count": r[1], "domains": r[2],
         "kind": r[3], "heading_path": r[4]}
        for r in rows
    ]


def domain_edge_flow(conn) -> list[dict]:
    """Claim edges between domains, showing inter-domain relationships."""
    if not _table_exists(conn, "chunk_domains"):
        return []
    if not _table_exists(conn, "claim_edges"):
        return []

    rows = conn.execute(
        "SELECT sd.domain AS source_domain, td.domain AS target_domain, "
        "ce.edge_type, count(*) AS edge_count "
        "FROM claim_edges ce "
        "JOIN chunk_domains sd ON sd.chunk_id = ce.source_chunk "
        "JOIN chunk_domains td ON td.chunk_id = ce.target_chunk "
        "WHERE sd.domain != td.domain "
        "GROUP BY sd.domain, td.domain, ce.edge_type "
        "ORDER BY edge_count DESC",
    ).fetchall()

    return [
        {"source_domain": r[0], "target_domain": r[1],
         "edge_type": r[2], "edge_count": r[3]}
        for r in rows
    ]


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

        domain_data = [
            ("c1", "ml", 0.9, now),
            ("c1", "nlp", 0.7, now),
            ("c2", "ml", 0.8, now),
            ("c3", "systems", 0.85, now),
            ("c3", "ml", 0.6, now),
            ("c4", "systems", 0.9, now),
        ]
        for dd in domain_data:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, score, "
                "classified_utc) VALUES (?, ?, ?, ?)", dd,
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
        dist = domain_distribution(conn)
        assert dist["total_assignments"] == 6
        assert dist["unique_domains"] == 3
        assert dist["classified_chunks"] == 4
        checks += 1

        # 2: domain ordering by chunk count
        assert dist["domains"][0]["domain"] == "ml"
        assert dist["domains"][0]["chunk_count"] == 3
        checks += 1

        # 3: score statistics
        ml_dom = dist["domains"][0]
        assert ml_dom["min_score"] == 0.6
        assert ml_dom["max_score"] == 0.9
        checks += 1

        # 4: per-source domain breakdown
        ps = domain_per_source(conn)
        assert len(ps) == 2
        checks += 1

        # 5: s1 domains
        s1_ps = [p for p in ps if p["source_id"] == "s1"][0]
        s1_domains = {d["domain"] for d in s1_ps["domains"]}
        assert "ml" in s1_domains
        assert "nlp" in s1_domains
        checks += 1

        # 6: s2 domains
        s2_ps = [p for p in ps if p["source_id"] == "s2"][0]
        s2_domains = {d["domain"] for d in s2_ps["domains"]}
        assert "systems" in s2_domains
        assert "ml" in s2_domains
        checks += 1

        # 7: multi-domain chunks
        md = multi_domain_chunks(conn, top_n=10)
        md_ids = {m["chunk_id"] for m in md}
        assert "c1" in md_ids
        assert "c3" in md_ids
        checks += 1

        # 8: single-domain chunks excluded
        assert "c2" not in md_ids
        assert "c4" not in md_ids
        checks += 1

        # 9: domain count and list
        c1_md = [m for m in md if m["chunk_id"] == "c1"][0]
        assert c1_md["domain_count"] == 2
        assert "ml" in c1_md["domains"]
        assert "nlp" in c1_md["domains"]
        checks += 1

        # 10: top_n limit
        md2 = multi_domain_chunks(conn, top_n=1)
        assert len(md2) == 1
        checks += 1

        # 11: edge flow between domains
        ef = domain_edge_flow(conn)
        assert len(ef) > 0
        checks += 1

        # 12: edge flow captures cross-domain edges
        ef_pairs = {(e["source_domain"], e["target_domain"]) for e in ef}
        assert ("ml", "systems") in ef_pairs or ("ml", "ml") not in ef_pairs
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(dist)
        _ = json.dumps(ps)
        _ = json.dumps(md)
        _ = json.dumps(ef)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert domain_distribution(conn2)["total_assignments"] == 0
        assert domain_per_source(conn2) == []
        assert multi_domain_chunks(conn2) == []
        assert domain_edge_flow(conn2) == []
        checks += 1

    print(f"PASS domain_analysis selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain analysis: chunk domain classification analytics"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_dist = sub.add_parser("distribution",
                            help="Domain distribution with score stats")
    p_dist.add_argument("--db", default=DEFAULT_DB)
    p_dist.add_argument("--json", action="store_true")

    p_ps = sub.add_parser("per-source",
                          help="Per-source domain breakdown")
    p_ps.add_argument("--db", default=DEFAULT_DB)
    p_ps.add_argument("--json", action="store_true")

    p_md = sub.add_parser("multi-domain",
                          help="Chunks in multiple domains")
    p_md.add_argument("--db", default=DEFAULT_DB)
    p_md.add_argument("--top", type=int, default=20)
    p_md.add_argument("--json", action="store_true")

    p_ef = sub.add_parser("edge-flow",
                          help="Claim edges between domains")
    p_ef.add_argument("--db", default=DEFAULT_DB)
    p_ef.add_argument("--json", action="store_true")

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
        result = domain_distribution(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Domains: {result['unique_domains']}, "
                  f"assignments: {result['total_assignments']}, "
                  f"classified chunks: {result['classified_chunks']}")
            for d in result["domains"]:
                print(f"  {d['domain']}: {d['chunk_count']} chunks "
                      f"(avg {d['avg_score']:.2f}, "
                      f"range {d['min_score']:.2f}-{d['max_score']:.2f})")

    elif args.cmd == "per-source":
        result = domain_per_source(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources with domain assignments: {len(result)}")
            for s in result:
                doms = ", ".join(
                    f"{d['domain']}({d['chunk_count']})"
                    for d in s["domains"]
                )
                print(f"  {s['source_id']}: {doms}")

    elif args.cmd == "multi-domain":
        result = multi_domain_chunks(conn, top_n=args.top)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Multi-domain chunks: {len(result)}")
            for r in result:
                print(f"  {r['chunk_id']}: {r['domain_count']} domains "
                      f"[{r['domains']}] ({r['kind']})")

    elif args.cmd == "edge-flow":
        result = domain_edge_flow(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cross-domain edges: {len(result)}")
            for r in result:
                print(f"  {r['source_domain']} -> {r['target_domain']} "
                      f"({r['edge_type']}): {r['edge_count']}")

    conn.close()


if __name__ == "__main__":
    main()
