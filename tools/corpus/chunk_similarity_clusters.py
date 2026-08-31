#!/usr/bin/env python3
"""Chunk similarity clustering: group chunks by simhash distance.

heading_simhash_profile.py profiles simhash collisions by heading.
No tool clusters chunks by simhash bit distance to find near-duplicate
content, measuring how much of the corpus contains closely related
material and which sources contribute the most redundancy.

Usage:
    python tools/corpus/chunk_similarity_clusters.py clusters [--db PATH] [--json] [--threshold N]
    python tools/corpus/chunk_similarity_clusters.py by-source [--db PATH] [--json] [--threshold N]
    python tools/corpus/chunk_similarity_clusters.py cross-source [--db PATH] [--json] [--threshold N]
    python tools/corpus/chunk_similarity_clusters.py summary [--db PATH] [--json] [--threshold N]
    python tools/corpus/chunk_similarity_clusters.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402


def _hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two simhash values."""
    return bin(a ^ b).count("1")


def _build_clusters(chunks: list[tuple[str, str, int]], threshold: int) -> list[list[tuple[str, str, int]]]:
    """Group chunks where any pair within the cluster has hamming distance <= threshold.

    Uses single-linkage clustering: if chunk A is near chunk B and chunk B
    is near chunk C, all three join the same cluster.
    """
    n = len(chunks)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            if _hamming_distance(chunks[i][2], chunks[j][2]) <= threshold:
                union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    clusters = []
    for indices in groups.values():
        if len(indices) >= 2:
            clusters.append([chunks[i] for i in indices])

    clusters.sort(key=lambda c: -len(c))
    return clusters


def find_clusters(conn, threshold: int = 3) -> list[dict]:
    """Find clusters of similar chunks by simhash distance."""
    rows = conn.execute(
        "SELECT chunk_id, source_id, simhash FROM chunks WHERE simhash IS NOT NULL"
    ).fetchall()
    chunks = [(r[0], r[1], r[2]) for r in rows]
    clusters = _build_clusters(chunks, threshold)

    result = []
    for i, cluster in enumerate(clusters):
        sources = set(c[1] for c in cluster)
        chunk_ids = [c[0] for c in cluster]
        result.append({
            "cluster_id": i,
            "size": len(cluster),
            "chunk_ids": sorted(chunk_ids),
            "source_count": len(sources),
            "sources": sorted(sources),
            "cross_source": len(sources) > 1,
        })
    return result


def clusters_by_source(conn, threshold: int = 3) -> list[dict]:
    """Per-source cluster participation statistics."""
    clusters = find_clusters(conn, threshold)
    sources: dict[str, dict] = defaultdict(lambda: {"cluster_count": 0, "chunks_in_clusters": 0, "cross_source_clusters": 0})
    for c in clusters:
        for src in c["sources"]:
            sources[src]["cluster_count"] += 1
            chunks_from_src = sum(1 for cid in c["chunk_ids"]
                                  if any(cl[0] == cid and cl[1] == src
                                         for cl in _get_chunk_source_map(conn, c["chunk_ids"])))
            sources[src]["chunks_in_clusters"] += chunks_from_src
            if c["cross_source"]:
                sources[src]["cross_source_clusters"] += 1

    total_by_source = dict(conn.execute(
        "SELECT source_id, COUNT(*) FROM chunks GROUP BY source_id"
    ).fetchall())

    return sorted(
        [
            {
                "source_id": sid,
                "cluster_count": d["cluster_count"],
                "chunks_in_clusters": d["chunks_in_clusters"],
                "total_chunks": total_by_source.get(sid, 0),
                "cluster_rate": round(d["chunks_in_clusters"] / max(total_by_source.get(sid, 0), 1), 4),
            }
            for sid, d in sources.items()
        ],
        key=lambda r: -r["chunks_in_clusters"],
    )


def _get_chunk_source_map(conn, chunk_ids: list[str]) -> list[tuple[str, str]]:
    """Get (chunk_id, source_id) pairs for given chunk_ids."""
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    rows = conn.execute(
        f"SELECT chunk_id, source_id FROM chunks WHERE chunk_id IN ({placeholders})",
        chunk_ids,
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def cross_source_clusters(conn, threshold: int = 3) -> list[dict]:
    """Clusters spanning multiple sources."""
    clusters = find_clusters(conn, threshold)
    return [c for c in clusters if c["cross_source"]]


def cluster_summary(conn, threshold: int = 3) -> dict:
    """Aggregate cluster statistics."""
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    total_with_simhash = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE simhash IS NOT NULL"
    ).fetchone()[0]

    clusters = find_clusters(conn, threshold)

    if not clusters:
        return {
            "total_chunks": total_chunks,
            "chunks_with_simhash": total_with_simhash,
            "total_clusters": 0,
            "chunks_in_clusters": 0,
            "cluster_rate": 0,
            "cross_source_clusters": 0,
            "largest_cluster": 0,
            "avg_cluster_size": 0,
            "threshold": threshold,
        }

    all_clustered = set()
    for c in clusters:
        all_clustered.update(c["chunk_ids"])
    cross = sum(1 for c in clusters if c["cross_source"])
    sizes = [c["size"] for c in clusters]

    return {
        "total_chunks": total_chunks,
        "chunks_with_simhash": total_with_simhash,
        "total_clusters": len(clusters),
        "chunks_in_clusters": len(all_clustered),
        "cluster_rate": round(len(all_clustered) / max(total_with_simhash, 1), 4),
        "cross_source_clusters": cross,
        "largest_cluster": max(sizes),
        "avg_cluster_size": round(sum(sizes) / len(sizes), 4),
        "threshold": threshold,
    }


def _selftest():
    import sqlite3
    ok = 0

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)

        t1 = "2026-01-01T00:00:00Z"
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "u://s1", "local_md", "S1", "MIT", "vendor", "self", None, None, t1, None, None, "live", "abc", 100, None))
        conn.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "u://s2", "local_md", "S2", "MIT", "vendor", "self", None, None, t1, None, None, "live", "def", 200, None))

        # c1, c2: simhash distance 1 (same source s1) -> cluster
        # c3: simhash distance 2 from c1 (source s2) -> same cluster at threshold 3
        # c4: simhash far from all (source s1) -> no cluster
        # c5, c6: simhash identical (source s2) -> separate cluster
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "s1", 1, "intro", "claim", None, "t", "t", 20, "h1", 0x0000000F, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "s1", 2, "intro", "claim", None, "t", "t", 20, "h2", 0x0000000E, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "s2", 1, "intro", "claim", None, "t", "t", 20, "h3", 0x0000000D, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "s1", 3, "methods", "claim", None, "t", "t", 20, "h4", 0xFFFF0000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "s2", 2, "results", "claim", None, "t", "t", 20, "h5", 0x00FF0000, 0, "accepted", None, t1))
        conn.execute("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "s2", 3, "results", "claim", None, "t", "t", 20, "h6", 0x00FF0000, 0, "accepted", None, t1))
        conn.commit()

        # 1. hamming distance: 0b1000 vs 0b1001 = 1
        assert _hamming_distance(0b1000, 0b1001) == 1
        ok += 1

        # 2. hamming distance: 0b1000 vs 0b1011 = 2
        assert _hamming_distance(0b1000, 0b1011) == 2
        ok += 1

        # 3. clusters at threshold 3: c1,c2,c3 form one cluster (single-linkage)
        cl = find_clusters(conn, threshold=3)
        big_cluster = [c for c in cl if "c1" in c["chunk_ids"]]
        assert len(big_cluster) == 1
        assert set(big_cluster[0]["chunk_ids"]) == {"c1", "c2", "c3"}
        ok += 1

        # 4. c5,c6 form a separate cluster (distance 0)
        small_cluster = [c for c in cl if "c5" in c["chunk_ids"]]
        assert len(small_cluster) == 1
        assert set(small_cluster[0]["chunk_ids"]) == {"c5", "c6"}
        ok += 1

        # 5. c4 is not in any cluster
        all_clustered = set()
        for c in cl:
            all_clustered.update(c["chunk_ids"])
        assert "c4" not in all_clustered
        ok += 1

        # 6. total clusters = 2
        assert len(cl) == 2
        ok += 1

        # 7. cross-source: c1,c2,c3 cluster spans s1 and s2
        assert big_cluster[0]["cross_source"] is True
        ok += 1

        # 8. cross-source: c5,c6 cluster is single-source s2
        assert small_cluster[0]["cross_source"] is False
        ok += 1

        # 9. cross_source_clusters returns only the cross-source one
        xsc = cross_source_clusters(conn, threshold=3)
        assert len(xsc) == 1
        ok += 1

        # 10. by-source: s1 has chunks in clusters
        bs = clusters_by_source(conn, threshold=3)
        s1_row = [r for r in bs if r["source_id"] == "s1"][0]
        assert s1_row["chunks_in_clusters"] >= 2
        ok += 1

        # 11. summary: total_clusters = 2
        s = cluster_summary(conn, threshold=3)
        assert s["total_clusters"] == 2
        ok += 1

        # 12. chunks_in_clusters = 5 (c1,c2,c3,c5,c6)
        assert s["chunks_in_clusters"] == 5
        ok += 1

        # 13. JSON round-trip
        j = json.loads(json.dumps(s))
        assert j["cluster_rate"] == s["cluster_rate"]
        ok += 1

    # 14. empty corpus
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(db))
        init_schema(conn)
        s = cluster_summary(conn, threshold=3)
        assert s["total_clusters"] == 0
        assert s["chunks_in_clusters"] == 0
        ok += 1

    return ok


def main():
    ap = argparse.ArgumentParser(description="Chunk similarity clustering")
    ap.add_argument("command", choices=["clusters", "by-source", "cross-source", "summary", "selftest"])
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--threshold", type=int, default=3)
    args = ap.parse_args()

    if args.command == "selftest":
        ok = _selftest()
        print(f"PASS chunk_similarity_clusters selftest ({ok} checks)")
        return

    conn = connect(args.db)
    if args.command == "clusters":
        rows = find_clusters(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No clusters found.")
            else:
                print(f"{'id':<6} {'size':<6} {'sources':<8} {'cross':<8} {'chunks'}")
                for r in rows:
                    chunks = ", ".join(r["chunk_ids"][:5])
                    if len(r["chunk_ids"]) > 5:
                        chunks += "..."
                    print(f"{r['cluster_id']:<6} {r['size']:<6} {r['source_count']:<8} {r['cross_source']!s:<8} {chunks}")
    elif args.command == "by-source":
        rows = clusters_by_source(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No source cluster data found.")
            else:
                print(f"{'source_id':<16} {'clusters':<10} {'in_clusters':<12} {'total':<8} {'rate'}")
                for r in rows:
                    print(f"{r['source_id']:<16} {r['cluster_count']:<10} {r['chunks_in_clusters']:<12} {r['total_chunks']:<8} {r['cluster_rate']:.4f}")
    elif args.command == "cross-source":
        rows = cross_source_clusters(conn, args.threshold)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            if not rows:
                print("No cross-source clusters found.")
            else:
                print(f"{'id':<6} {'size':<6} {'sources':<8} {'chunks'}")
                for r in rows:
                    chunks = ", ".join(r["chunk_ids"][:5])
                    if len(r["chunk_ids"]) > 5:
                        chunks += "..."
                    print(f"{r['cluster_id']:<6} {r['size']:<6} {r['source_count']:<8} {chunks}")
    elif args.command == "summary":
        s = cluster_summary(conn, args.threshold)
        if args.json:
            print(json.dumps(s, indent=2))
        else:
            for k, v in s.items():
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
