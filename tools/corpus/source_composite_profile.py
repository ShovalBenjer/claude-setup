#!/usr/bin/env python3
"""Source composite profile: per-source richness across all metadata tables.

No tool joins sources with all six downstream tables (chunks, citations,
claim_edges, artifacts, chunk_tags, chunk_domains) to build a single
per-source vector.  Understanding which sources are metadata-rich vs
metadata-sparse required manual multi-table joins.  This tool answers
that by computing a composite profile per source.

Usage:
    python tools/corpus/source_composite_profile.py profile [--db PATH] [--json]
    python tools/corpus/source_composite_profile.py sparse [--db PATH] [--json]
    python tools/corpus/source_composite_profile.py ranking [--db PATH] [--json]
    python tools/corpus/source_composite_profile.py summary [--db PATH] [--json]
    python tools/corpus/source_composite_profile.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def source_profiles(conn) -> list[dict]:
    """Per-source richness vector across all metadata tables."""
    rows = conn.execute(
        "SELECT s.source_id, s.title, s.kind, "
        "  (SELECT count(*) FROM chunks c "
        "   WHERE c.source_id = s.source_id) AS chunk_cnt, "
        "  (SELECT count(*) FROM citations ct "
        "   JOIN chunks c2 ON ct.chunk_id = c2.chunk_id "
        "   WHERE c2.source_id = s.source_id) AS citation_cnt, "
        "  (SELECT count(DISTINCT e.edge_id) FROM claim_edges e "
        "   JOIN chunks c3 ON (e.source_chunk = c3.chunk_id "
        "       OR e.target_chunk = c3.chunk_id) "
        "   WHERE c3.source_id = s.source_id) AS edge_cnt, "
        "  (SELECT count(*) FROM artifacts a "
        "   JOIN chunks c4 ON a.chunk_id = c4.chunk_id "
        "   WHERE c4.source_id = s.source_id) AS artifact_cnt, "
        "  (SELECT count(DISTINCT ct2.tag) FROM chunk_tags ct2 "
        "   JOIN chunks c5 ON ct2.chunk_id = c5.chunk_id "
        "   WHERE c5.source_id = s.source_id) AS tag_cnt, "
        "  (SELECT count(DISTINCT cd.domain) FROM chunk_domains cd "
        "   JOIN chunks c6 ON cd.chunk_id = c6.chunk_id "
        "   WHERE c6.source_id = s.source_id) AS domain_cnt "
        "FROM sources s "
        "ORDER BY s.source_id"
    ).fetchall()

    if not rows:
        return []

    results = []
    for sid, title, kind, chunks, cits, edges, arts, tags, doms in rows:
        dimensions = sum(1 for v in (chunks, cits, edges, arts, tags, doms)
                         if v > 0)
        results.append({
            "source_id": sid,
            "title": title,
            "kind": kind,
            "chunks": chunks,
            "citations": cits,
            "edges": edges,
            "artifacts": arts,
            "tags": tags,
            "domains": doms,
            "dimensions_populated": dimensions,
        })

    return results


def sparse_sources(conn) -> list[dict]:
    """Sources with fewer than 3 populated dimensions."""
    profiles = source_profiles(conn)
    return [p for p in profiles if p["dimensions_populated"] < 3]


def source_ranking(conn) -> list[dict]:
    """Sources ranked by number of populated dimensions, richest first."""
    profiles = source_profiles(conn)
    profiles.sort(
        key=lambda p: (
            p["dimensions_populated"],
            p["chunks"] + p["citations"] + p["edges"]
            + p["artifacts"] + p["tags"] + p["domains"],
        ),
        reverse=True,
    )
    for i, p in enumerate(profiles, 1):
        p["rank"] = i
    return profiles


def composite_summary(conn) -> dict:
    """Aggregate source composite statistics."""
    profiles = source_profiles(conn)

    if not profiles:
        return {
            "total_sources": 0,
            "fully_populated": 0,
            "sparse_sources": 0,
            "mean_dimensions": 0.0,
            "richest_source": None,
            "sparsest_source": None,
        }

    dims = [p["dimensions_populated"] for p in profiles]
    n = len(dims)
    fully = sum(1 for d in dims if d == 6)
    sparse = sum(1 for d in dims if d < 3)
    richest = max(profiles, key=lambda p: (
        p["dimensions_populated"],
        p["chunks"] + p["citations"] + p["edges"]
        + p["artifacts"] + p["tags"] + p["domains"],
    ))
    sparsest = min(profiles, key=lambda p: (
        p["dimensions_populated"],
        p["chunks"] + p["citations"] + p["edges"]
        + p["artifacts"] + p["tags"] + p["domains"],
    ))

    return {
        "total_sources": n,
        "fully_populated": fully,
        "sparse_sources": sparse,
        "mean_dimensions": round(sum(dims) / n, 2),
        "richest_source": richest["source_id"],
        "sparsest_source": sparsest["source_id"],
    }


# -- selftest ----------------------------------------------------------------


def _selftest() -> None:
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = connect(str(db))
        init_schema(conn)

        now = "2026-06-01T00:00:00Z"

        for i in range(3):
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, "
                "title, license_spdx, license_verdict, license_evidence, "
                "publisher, published_utc, fetched_utc, upstream_rev, "
                "upstream_mtime, liveness, content_sha256, bytes, "
                "supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"s{i+1}", f"https://s{i+1}.com", "paper",
                 f"Source {i+1}", "CC-BY-4.0", "vendor", "declared",
                 "Pub", now, now, "", "", "live", f"sha_s{i+1}",
                 1000, None),
            )

        # s1: 3 chunks, s2: 2 chunks, s3: 1 chunk
        chunk_data = [
            ("c1", "s1", 0), ("c2", "s1", 1), ("c3", "s1", 2),
            ("c4", "s2", 0), ("c5", "s2", 1),
            ("c6", "s3", 0),
        ]
        for cid, sid, ordinal in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, citation_count, "
                "status, ingested_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ordinal, f"/h/{cid}", "claim", "en",
                 f"text {cid}", f"text {cid}", 10,
                 f"sha_{cid}", 0, 0, "accepted", now),
            )

        # Citations: s1 has 3 citations, s2 has 1
        cits = [
            ("ct1", "c1", "https://r1.com", None, "url", None, 1, now),
            ("ct2", "c2", "https://r2.com", None, "doi", None, 0, None),
            ("ct3", "c3", "https://r3.com", None, "url", None, 1, now),
            ("ct4", "c4", "https://r4.com", None, "doi", None, 0, None),
        ]
        for ct in cits:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, "
                "target_uri, target_source_id, tag, locator, "
                "verified, verified_utc) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", ct,
            )

        # Edges: s1 chunks involved in 2 edges, s2 in 1
        edges = [
            ("e1", "c1", "c2", "supports", "shared API", 0.9, now),
            ("e2", "c1", "c3", "refines", "design", 0.7, now),
            ("e3", "c4", "c5", "supports", "tooling", 0.85, now),
        ]
        for e in edges:
            conn.execute(
                "INSERT INTO claim_edges (edge_id, source_chunk, "
                "target_chunk, edge_type, basis, confidence, "
                "detected_utc) VALUES (?, ?, ?, ?, ?, ?, ?)", e,
            )

        # Artifacts: s1 has 2, s2 has 1
        arts = [
            ("a1", "c1", "library", "React", None, None, 1, None),
            ("a2", "c2", "api", "REST", None, None, 1, None),
            ("a3", "c4", "command", "npm", None, None, 0, None),
        ]
        for a in arts:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, "
                "artifact_type, name, version, snippet, "
                "implemented, evidence_path) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?)", a,
            )

        # Tags: s1 has 2 distinct tags, s2 has 1
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "tag TEXT NOT NULL, score REAL NOT NULL, "
            "tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )
        tags = [
            ("c1", "ml", 0.9, now), ("c2", "security", 0.8, now),
            ("c4", "ml", 0.7, now),
        ]
        for t in tags:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, "
                "tagged_utc) VALUES (?, ?, ?, ?)", t,
            )

        # Domains: s1 has 2 distinct domains, s3 has 0
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id), "
            "domain TEXT NOT NULL, score REAL NOT NULL, "
            "classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        doms = [
            ("c1", "nlp", 0.9, now), ("c3", "systems", 0.8, now),
        ]
        for d in doms:
            conn.execute(
                "INSERT INTO chunk_domains (chunk_id, domain, "
                "score, classified_utc) VALUES (?, ?, ?, ?)", d,
            )

        conn.commit()

        # 1: profiles returns 3 sources
        profiles = source_profiles(conn)
        assert len(profiles) == 3
        checks += 1

        # 2: s1 is richest (all 6 dimensions populated)
        s1 = next(p for p in profiles if p["source_id"] == "s1")
        assert s1["chunks"] == 3
        assert s1["citations"] == 3
        assert s1["edges"] == 2
        assert s1["artifacts"] == 2
        assert s1["tags"] == 2
        assert s1["domains"] == 2
        assert s1["dimensions_populated"] == 6
        checks += 1

        # 3: s2 has 5 dimensions (no domains)
        s2 = next(p for p in profiles if p["source_id"] == "s2")
        assert s2["chunks"] == 2
        assert s2["domains"] == 0
        assert s2["dimensions_populated"] == 5
        checks += 1

        # 4: s3 is sparsest (1 chunk only)
        s3 = next(p for p in profiles if p["source_id"] == "s3")
        assert s3["chunks"] == 1
        assert s3["citations"] == 0
        assert s3["edges"] == 0
        assert s3["artifacts"] == 0
        assert s3["dimensions_populated"] == 1
        checks += 1

        # 5: sparse sources returns s3
        sparse = sparse_sources(conn)
        assert len(sparse) == 1
        assert sparse[0]["source_id"] == "s3"
        checks += 1

        # 6: ranking puts s1 first
        ranked = source_ranking(conn)
        assert ranked[0]["source_id"] == "s1"
        assert ranked[0]["rank"] == 1
        checks += 1

        # 7: ranking puts s3 last
        assert ranked[-1]["source_id"] == "s3"
        assert ranked[-1]["rank"] == 3
        checks += 1

        # 8: summary totals correct
        summary = composite_summary(conn)
        assert summary["total_sources"] == 3
        checks += 1

        # 9: fully populated count
        assert summary["fully_populated"] == 1
        checks += 1

        # 10: sparse count
        assert summary["sparse_sources"] == 1
        checks += 1

        # 11: richest source identified
        assert summary["richest_source"] == "s1"
        checks += 1

        # 12: sparsest source identified
        assert summary["sparsest_source"] == "s3"
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(profiles)
        _ = json.dumps(sparse)
        _ = json.dumps(ranked)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_tags ("
            "chunk_id TEXT NOT NULL, tag TEXT NOT NULL, "
            "score REAL NOT NULL, tagged_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, tag))"
        )
        conn2.execute(
            "CREATE TABLE IF NOT EXISTS chunk_domains ("
            "chunk_id TEXT NOT NULL, domain TEXT NOT NULL, "
            "score REAL NOT NULL, classified_utc TEXT NOT NULL, "
            "PRIMARY KEY (chunk_id, domain))"
        )
        empty = source_profiles(conn2)
        assert empty == []
        empty_summary = composite_summary(conn2)
        assert empty_summary["total_sources"] == 0
        checks += 1

    print(
        f"PASS source_composite_profile selftest ({checks} checks)"
    )


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Source composite profile analysis"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_prof = sub.add_parser("profile",
                            help="Per-source richness vector")
    p_prof.add_argument("--db", default=DEFAULT_DB)
    p_prof.add_argument("--json", action="store_true")

    p_sparse = sub.add_parser("sparse",
                              help="Sources with low dimension count")
    p_sparse.add_argument("--db", default=DEFAULT_DB)
    p_sparse.add_argument("--json", action="store_true")

    p_rank = sub.add_parser("ranking",
                            help="Sources ranked by richness")
    p_rank.add_argument("--db", default=DEFAULT_DB)
    p_rank.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Composite profile statistics")
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

    if args.cmd == "profile":
        results = source_profiles(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_id']:12s}  "
                      f"chunks={r['chunks']:3d}  "
                      f"cites={r['citations']:3d}  "
                      f"edges={r['edges']:3d}  "
                      f"arts={r['artifacts']:3d}  "
                      f"tags={r['tags']:2d}  "
                      f"doms={r['domains']:2d}  "
                      f"dims={r['dimensions_populated']}/6")

    elif args.cmd == "sparse":
        results = sparse_sources(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  {r['source_id']:12s}  "
                      f"{r['title']}  "
                      f"dims={r['dimensions_populated']}/6")

    elif args.cmd == "ranking":
        results = source_ranking(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  #{r['rank']:2d}  "
                      f"{r['source_id']:12s}  "
                      f"dims={r['dimensions_populated']}/6  "
                      f"{r['title']}")

    elif args.cmd == "summary":
        result = composite_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Sources: {result['total_sources']}  "
                  f"Fully populated: {result['fully_populated']}  "
                  f"Sparse: {result['sparse_sources']}")
            print(f"  Mean dimensions: "
                  f"{result['mean_dimensions']:.1f}/6")
            if result["richest_source"]:
                print(f"  Richest: {result['richest_source']}  "
                      f"Sparsest: {result['sparsest_source']}")

    conn.close()


if __name__ == "__main__":
    main()
