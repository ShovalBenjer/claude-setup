#!/usr/bin/env python3
"""Artifact dependency graph: maps relationships between artifacts.

Discovers co-occurrence between artifacts through shared chunks, shared
sources, and claim edges linking chunks that reference different
artifacts.  Produces a dependency graph and identifies artifact clusters.

Usage:
    python tools/corpus/artifact_graph.py edges [--db PATH] [--json]
    python tools/corpus/artifact_graph.py clusters [--db PATH] [--json]
    python tools/corpus/artifact_graph.py summary [--db PATH] [--json]
    python tools/corpus/artifact_graph.py selftest
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


def artifact_edges(conn) -> list[dict]:
    """Find relationships between artifacts.

    Two artifacts are related when:
    - They share a chunk (co-mention in same text)
    - Their chunks share a source (co-presence in same document)
    - Their chunks are linked by a claim_edge (semantic relationship)
    """
    if not _table_exists(conn, "artifacts"):
        return []

    arts = conn.execute(
        "SELECT artifact_id, chunk_id, name, artifact_type "
        "FROM artifacts"
    ).fetchall()

    if len(arts) < 2:
        return []

    art_by_chunk: dict[str, list[dict]] = {}
    art_info: dict[str, dict] = {}
    for aid, cid, name, atype in arts:
        art_info[aid] = {"name": name, "type": atype, "chunk_id": cid}
        if cid not in art_by_chunk:
            art_by_chunk[cid] = []
        art_by_chunk[cid].append({"artifact_id": aid, "name": name})

    chunk_source: dict[str, str] = {}
    chunk_ids = list(art_by_chunk.keys())
    if chunk_ids:
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = conn.execute(
            f"SELECT chunk_id, source_id FROM chunks "
            f"WHERE chunk_id IN ({placeholders})",
            chunk_ids,
        ).fetchall()
        chunk_source = {r[0]: r[1] for r in rows}

    edges: dict[tuple[str, str], dict] = {}

    def _add_edge(a1: str, a2: str, relation: str) -> None:
        key = (min(a1, a2), max(a1, a2))
        if key not in edges:
            edges[key] = {
                "artifact_a": key[0],
                "artifact_b": key[1],
                "name_a": art_info[key[0]]["name"],
                "name_b": art_info[key[1]]["name"],
                "relations": [],
            }
        if relation not in edges[key]["relations"]:
            edges[key]["relations"].append(relation)

    for cid, chunk_arts in art_by_chunk.items():
        if len(chunk_arts) >= 2:
            for i in range(len(chunk_arts)):
                for j in range(i + 1, len(chunk_arts)):
                    _add_edge(
                        chunk_arts[i]["artifact_id"],
                        chunk_arts[j]["artifact_id"],
                        "co_mention",
                    )

    source_arts: dict[str, list[str]] = {}
    for aid, info in art_info.items():
        sid = chunk_source.get(info["chunk_id"])
        if sid:
            if sid not in source_arts:
                source_arts[sid] = []
            source_arts[sid].append(aid)

    for sid, aids in source_arts.items():
        if len(aids) >= 2:
            for i in range(len(aids)):
                for j in range(i + 1, len(aids)):
                    _add_edge(aids[i], aids[j], "co_source")

    art_by_aid_chunk = {info["chunk_id"]: aid for aid, info in art_info.items()}
    claim_rows = conn.execute(
        "SELECT source_chunk, target_chunk FROM claim_edges"
    ).fetchall()
    for src_chunk, tgt_chunk in claim_rows:
        if src_chunk in art_by_aid_chunk and tgt_chunk in art_by_aid_chunk:
            a1 = art_by_aid_chunk[src_chunk]
            a2 = art_by_aid_chunk[tgt_chunk]
            if a1 != a2:
                _add_edge(a1, a2, "claim_linked")

    result = list(edges.values())
    result.sort(key=lambda e: len(e["relations"]), reverse=True)
    return result


def artifact_clusters(conn) -> list[dict]:
    """Group artifacts into connected components via their edges.

    Uses union-find to cluster artifacts that share any relationship.
    """
    all_edges = artifact_edges(conn)

    if not all_edges:
        arts = conn.execute(
            "SELECT artifact_id, name, artifact_type FROM artifacts"
        ).fetchall() if _table_exists(conn, "artifacts") else []
        return [
            {"cluster_id": i, "artifacts": [{"artifact_id": a[0],
             "name": a[1], "type": a[2]}], "size": 1}
            for i, a in enumerate(arts)
        ]

    all_ids: set[str] = set()
    art_names: dict[str, str] = {}
    art_types: dict[str, str] = {}
    for e in all_edges:
        all_ids.add(e["artifact_a"])
        all_ids.add(e["artifact_b"])

    if _table_exists(conn, "artifacts"):
        rows = conn.execute(
            "SELECT artifact_id, name, artifact_type FROM artifacts"
        ).fetchall()
        for aid, name, atype in rows:
            all_ids.add(aid)
            art_names[aid] = name
            art_types[aid] = atype

    parent: dict[str, str] = {aid: aid for aid in all_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in all_edges:
        union(e["artifact_a"], e["artifact_b"])

    groups: dict[str, list[str]] = {}
    for aid in all_ids:
        root = find(aid)
        if root not in groups:
            groups[root] = []
        groups[root].append(aid)

    clusters = []
    for i, (_, members) in enumerate(sorted(groups.items(),
                                             key=lambda g: len(g[1]),
                                             reverse=True)):
        clusters.append({
            "cluster_id": i,
            "artifacts": [
                {"artifact_id": m,
                 "name": art_names.get(m, m),
                 "type": art_types.get(m, "")}
                for m in sorted(members)
            ],
            "size": len(members),
        })

    return clusters


def graph_summary(conn) -> dict:
    """Aggregate artifact graph statistics."""
    if not _table_exists(conn, "artifacts"):
        return {
            "total_artifacts": 0,
            "total_edges": 0,
            "connected_artifacts": 0,
            "isolated_artifacts": 0,
            "cluster_count": 0,
            "relation_counts": {},
        }

    total = conn.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    all_edges = artifact_edges(conn)
    clusters = artifact_clusters(conn)

    connected = {e["artifact_a"] for e in all_edges} | {e["artifact_b"] for e in all_edges}

    relation_counts: dict[str, int] = {}
    for e in all_edges:
        for r in e["relations"]:
            relation_counts[r] = relation_counts.get(r, 0) + 1

    return {
        "total_artifacts": total,
        "total_edges": len(all_edges),
        "connected_artifacts": len(connected),
        "isolated_artifacts": total - len(connected),
        "cluster_count": len(clusters),
        "relation_counts": relation_counts,
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

        for sid, uri in [("s1", "https://a.com"), ("s2", "https://b.com")]:
            conn.execute(
                "INSERT INTO sources (source_id, canonical_uri, kind, title, "
                "license_spdx, license_verdict, license_evidence, publisher, "
                "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
                "liveness, content_sha256, bytes, supersedes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, uri, "paper", f"Source {sid}",
                 "CC-BY-4.0", "vendor", "declared", "Pub",
                 now, now, "", "", "live", f"sha_{sid}", 1000, None),
            )

        chunk_data = [
            ("c1", "s1", 0, "Chunk A"),
            ("c2", "s1", 1, "Chunk B"),
            ("c3", "s2", 0, "Chunk C"),
            ("c4", "s2", 1, "Chunk D"),
        ]
        for cid, sid, ordinal, heading in chunk_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, ordinal, heading, "claim", "en",
                 "text", "text", 10, f"n_{cid}", "accepted", now),
            )

        artifacts_data = [
            ("a1", "c1", "library", "numpy", "1.26"),
            ("a2", "c1", "library", "pandas", "2.0"),
            ("a3", "c2", "command", "pip", None),
            ("a4", "c3", "library", "numpy", "1.26"),
            ("a5", "c4", "api", "openai", "1.0"),
        ]
        for aid, cid, atype, name, ver in artifacts_data:
            conn.execute(
                "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
                "name, version, snippet, implemented, evidence_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, atype, name, ver, None, 1, None),
            )

        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("e1", "c1", "c3", "supports", "semantic", 0.9, now),
        )

        conn.commit()

        # 1: co-mention edge for numpy and pandas (same chunk c1)
        edges = artifact_edges(conn)
        co_mention = [e for e in edges if "co_mention" in e["relations"]]
        assert len(co_mention) >= 1
        checks += 1

        # 2: co-source edge for artifacts in same source
        co_source = [e for e in edges if "co_source" in e["relations"]]
        assert len(co_source) >= 1
        checks += 1

        # 3: claim-linked edge between c1 and c3 artifacts
        claim_linked = [e for e in edges if "claim_linked" in e["relations"]]
        assert len(claim_linked) >= 1
        checks += 1

        # 4: edges sorted by relation count descending
        counts = [len(e["relations"]) for e in edges]
        assert counts == sorted(counts, reverse=True)
        checks += 1

        # 5: edge names are populated
        for e in edges:
            assert e["name_a"] != ""
            assert e["name_b"] != ""
        checks += 1

        # 6: clusters group connected artifacts
        clusters = artifact_clusters(conn)
        assert len(clusters) >= 1
        sizes = [c["size"] for c in clusters]
        assert max(sizes) >= 2
        checks += 1

        # 7: all artifacts appear in exactly one cluster
        all_in_clusters = []
        for c in clusters:
            all_in_clusters.extend(a["artifact_id"] for a in c["artifacts"])
        assert len(all_in_clusters) == len(set(all_in_clusters))
        assert len(all_in_clusters) == 5
        checks += 1

        # 8: clusters sorted by size descending
        assert sizes == sorted(sizes, reverse=True)
        checks += 1

        # 9: summary has required keys
        summary = graph_summary(conn)
        assert summary["total_artifacts"] == 5
        assert summary["total_edges"] > 0
        assert "relation_counts" in summary
        checks += 1

        # 10: connected vs isolated artifacts
        assert summary["connected_artifacts"] > 0
        assert (summary["connected_artifacts"]
                + summary["isolated_artifacts"]) == 5
        checks += 1

        # 11: relation_counts has at least co_mention
        assert "co_mention" in summary["relation_counts"]
        checks += 1

        # 12: cluster_count matches
        assert summary["cluster_count"] == len(clusters)
        checks += 1

        # 13: JSON serialisable
        _ = json.dumps(edges)
        _ = json.dumps(clusters)
        _ = json.dumps(summary)
        checks += 1

        # 14: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        empty = artifact_edges(conn2)
        assert empty == []
        empty_summary = graph_summary(conn2)
        assert empty_summary["total_artifacts"] == 0
        checks += 1

    print(f"PASS artifact_graph selftest ({checks} checks)")


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Artifact dependency graph"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_edges = sub.add_parser("edges",
                             help="Artifact relationship edges")
    p_edges.add_argument("--db", default=DEFAULT_DB)
    p_edges.add_argument("--json", action="store_true")

    p_clust = sub.add_parser("clusters",
                             help="Connected artifact clusters")
    p_clust.add_argument("--db", default=DEFAULT_DB)
    p_clust.add_argument("--json", action="store_true")

    p_sum = sub.add_parser("summary",
                           help="Graph statistics")
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

    if args.cmd == "edges":
        results = artifact_edges(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No artifact edges found.")
            else:
                for e in results:
                    rels = ",".join(e["relations"])
                    print(f"  {e['name_a']:15s} <-> {e['name_b']:15s}  "
                          f"[{rels}]")

    elif args.cmd == "clusters":
        results = artifact_clusters(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for c in results:
                names = ", ".join(a["name"] for a in c["artifacts"])
                print(f"  Cluster {c['cluster_id']} "
                      f"({c['size']} artifacts): {names}")

    elif args.cmd == "summary":
        result = graph_summary(conn)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Artifacts: {result['total_artifacts']} total, "
                  f"{result['connected_artifacts']} connected, "
                  f"{result['isolated_artifacts']} isolated")
            print(f"Edges: {result['total_edges']}  "
                  f"Clusters: {result['cluster_count']}")
            if result["relation_counts"]:
                for rel, count in result["relation_counts"].items():
                    print(f"  {rel}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
