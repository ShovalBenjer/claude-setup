#!/usr/bin/env python3
"""Tag co-occurrence analysis for the research corpus.

Analyses which tags appear together on the same chunks, finds
disproportionately linked tag pairs via PMI, discovers tag
communities, and identifies hub tags that bridge groups.

Usage:
    python tools/corpus/tag_cooccurrence.py matrix [--db PATH] [--top N] [--min-pmi F] [--json]
    python tools/corpus/tag_cooccurrence.py communities [--db PATH] [--json]
    python tools/corpus/tag_cooccurrence.py hubs [--db PATH] [--top N] [--json]
    python tools/corpus/tag_cooccurrence.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, connect, init_schema  # noqa: E402

# ── helpers ──────────────────────────────────────────────────────────


def _tag_sets(conn) -> list[set[str]]:
    rows = conn.execute(
        "SELECT ct.chunk_id, ct.tag "
        "FROM chunk_tags ct "
        "JOIN chunks c ON c.chunk_id = ct.chunk_id "
        "WHERE c.status != 'superseded'"
    ).fetchall()
    by_chunk: dict[str, set[str]] = defaultdict(set)
    for chunk_id, tag in rows:
        by_chunk[chunk_id].add(tag)
    return list(by_chunk.values())


def _cooccurrence_counts(tag_sets: list[set[str]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for tags in tag_sets:
        ordered = sorted(tags)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                counts[(a, b)] += 1
    return dict(counts)


def _tag_freqs(tag_sets: list[set[str]]) -> dict[str, int]:
    freqs: dict[str, int] = defaultdict(int)
    for tags in tag_sets:
        for t in tags:
            freqs[t] += 1
    return dict(freqs)


def _pmi(pair_count: int, freq_a: int, freq_b: int, n: int) -> float:
    if n == 0 or freq_a == 0 or freq_b == 0 or pair_count == 0:
        return 0.0
    p_ab = pair_count / n
    p_a = freq_a / n
    p_b = freq_b / n
    return math.log2(p_ab / (p_a * p_b))


# ── subcommands ──────────────────────────────────────────────────────


def cooccurrence_matrix(conn, top_n: int = 20,
                        min_pmi: float = 0.0) -> list[dict]:
    tag_sets = _tag_sets(conn)
    n = len(tag_sets)
    if n == 0:
        return []

    pair_counts = _cooccurrence_counts(tag_sets)
    freqs = _tag_freqs(tag_sets)

    results = []
    for (a, b), count in pair_counts.items():
        pmi_val = _pmi(count, freqs[a], freqs[b], n)
        if pmi_val < min_pmi:
            continue
        results.append({
            "tag_a": a,
            "tag_b": b,
            "co_count": count,
            "pmi": round(pmi_val, 4),
            "freq_a": freqs[a],
            "freq_b": freqs[b],
        })

    results.sort(key=lambda r: r["pmi"], reverse=True)
    return results[:top_n]


def tag_communities(conn) -> list[dict]:
    tag_sets = _tag_sets(conn)
    if not tag_sets:
        return []

    pair_counts = _cooccurrence_counts(tag_sets)
    all_tags = set()
    for tags in tag_sets:
        all_tags.update(tags)

    adj: dict[str, set[str]] = defaultdict(set)
    for (a, b), count in pair_counts.items():
        if count >= 2:
            adj[a].add(b)
            adj[b].add(a)

    visited: set[str] = set()
    communities = []

    for tag in sorted(all_tags):
        if tag in visited:
            continue
        component: set[str] = set()
        stack = [tag]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(
                nb for nb in adj.get(current, set()) if nb not in visited
            )
        communities.append(sorted(component))

    freqs = _tag_freqs(tag_sets)
    result = []
    for members in sorted(communities, key=len, reverse=True):
        total_freq = sum(freqs.get(m, 0) for m in members)
        result.append({
            "size": len(members),
            "members": members,
            "total_frequency": total_freq,
        })
    return result


def hub_tags(conn, top_n: int = 10) -> list[dict]:
    tag_sets = _tag_sets(conn)
    if not tag_sets:
        return []

    pair_counts = _cooccurrence_counts(tag_sets)
    freqs = _tag_freqs(tag_sets)

    neighbors: dict[str, set[str]] = defaultdict(set)
    for (a, b), count in pair_counts.items():
        if count >= 2:
            neighbors[a].add(b)
            neighbors[b].add(a)

    comms = tag_communities(conn)
    tag_to_community: dict[str, int] = {}
    for idx, comm in enumerate(comms):
        for m in comm["members"]:
            tag_to_community[m] = idx

    results = []
    for tag in freqs:
        nbrs = neighbors.get(tag, set())
        comm_ids = {tag_to_community.get(nb, -1) for nb in nbrs}
        own_comm = tag_to_community.get(tag, -1)
        bridged = comm_ids - {own_comm, -1}
        results.append({
            "tag": tag,
            "frequency": freqs[tag],
            "neighbor_count": len(nbrs),
            "communities_bridged": len(bridged),
        })

    results.sort(key=lambda r: (r["communities_bridged"], r["neighbor_count"]),
                 reverse=True)
    return results[:top_n]


# ── selftest ─────────────────────────────────────────────────────────


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

        conn.execute(
            "INSERT INTO sources (source_id, canonical_uri, kind, title, "
            "license_spdx, license_verdict, license_evidence, publisher, "
            "published_utc, fetched_utc, upstream_rev, upstream_mtime, "
            "liveness, content_sha256, bytes, supersedes) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", "https://example.com/1", "paper", "Test",
             "CC-BY-4.0", "vendor", "declared", "Test Pub",
             now, now, "", "", "live", "abc123", 1000, None),
        )

        chunks_data = [
            ("c1", "s1", 0, "H1", "claim", "en", "alpha beta", "alpha beta", 2, "sha1"),
            ("c2", "s1", 1, "H2", "claim", "en", "gamma delta", "gamma delta", 2, "sha2"),
            ("c3", "s1", 2, "H3", "claim", "en", "epsilon zeta", "epsilon zeta", 2, "sha3"),
            ("c4", "s1", 3, "H4", "claim", "en", "eta theta", "eta theta", 2, "sha4"),
            ("c5", "s1", 4, "H5", "claim", "en", "iota kappa", "iota kappa", 2, "sha5"),
        ]
        for cd in chunks_data:
            conn.execute(
                "INSERT INTO chunks (chunk_id, source_id, ordinal, "
                "heading_path, kind, lang, norm_text, raw_text, "
                "word_count, norm_sha256, simhash, status, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (*cd, now),
            )

        tags_data = [
            ("c1", "ml", 0.9), ("c1", "nlp", 0.8), ("c1", "ethics", 0.3),
            ("c2", "ml", 0.7), ("c2", "nlp", 0.6),
            ("c3", "ml", 0.5), ("c3", "security", 0.8),
            ("c4", "security", 0.9), ("c4", "ethics", 0.4),
            ("c5", "biology", 0.9),
        ]
        for chunk_id, tag, score in tags_data:
            conn.execute(
                "INSERT INTO chunk_tags (chunk_id, tag, score, tagged_utc) "
                "VALUES (?, ?, ?, ?)",
                (chunk_id, tag, score, now),
            )
        conn.commit()

        # 1: matrix returns results
        mat = cooccurrence_matrix(conn, top_n=50)
        assert len(mat) > 0, "matrix should return pairs"
        checks += 1

        # 2: ml-nlp is a strong pair
        ml_nlp = [r for r in mat if {r["tag_a"], r["tag_b"]} == {"ml", "nlp"}]
        assert len(ml_nlp) == 1, "ml-nlp pair should exist"
        assert ml_nlp[0]["co_count"] == 2, "ml-nlp co-occurs on c1 and c2"
        checks += 1

        # 3: PMI is positive for related pairs
        assert ml_nlp[0]["pmi"] > 0, "PMI should be positive for ml-nlp"
        checks += 1

        # 4: communities returns groups
        comms = tag_communities(conn)
        assert len(comms) > 0, "should find communities"
        checks += 1

        # 5: biology is isolated (only on c5, no co-occurrence >= 2)
        bio_comms = [c for c in comms if "biology" in c["members"]]
        assert len(bio_comms) == 1, "biology should be in a community"
        assert bio_comms[0]["size"] == 1, "biology should be isolated"
        checks += 1

        # 6: ml and nlp are in the same community
        ml_comm = [c for c in comms if "ml" in c["members"]]
        assert len(ml_comm) == 1
        assert "nlp" in ml_comm[0]["members"], "ml and nlp same community"
        checks += 1

        # 7: hubs returns results
        hubs = hub_tags(conn, top_n=10)
        assert len(hubs) > 0, "should find hub tags"
        checks += 1

        # 8: hub frequency matches
        ml_hub = [h for h in hubs if h["tag"] == "ml"]
        assert len(ml_hub) == 1
        assert ml_hub[0]["frequency"] == 3, "ml appears on 3 chunks"
        checks += 1

        # 9: JSON output for matrix
        for row in mat:
            _ = json.dumps(row)
        checks += 1

        # 10: JSON output for communities
        for row in comms:
            _ = json.dumps(row)
        checks += 1

        # 11: JSON output for hubs
        for row in hubs:
            _ = json.dumps(row)
        checks += 1

        # 12: empty corpus
        conn2 = connect(":memory:")
        init_schema(conn2)
        assert cooccurrence_matrix(conn2) == []
        assert tag_communities(conn2) == []
        assert hub_tags(conn2) == []
        checks += 1

        # 13: min_pmi filter
        high_pmi = cooccurrence_matrix(conn, min_pmi=5.0)
        assert len(high_pmi) <= len(mat), "high pmi filter should reduce results"
        checks += 1

        # 14: superseded chunks excluded
        conn.execute("UPDATE chunks SET status = 'superseded' WHERE chunk_id = 'c1'")
        conn.commit()
        mat2 = cooccurrence_matrix(conn, top_n=50)
        ml_nlp2 = [r for r in mat2 if {r["tag_a"], r["tag_b"]} == {"ml", "nlp"}]
        if ml_nlp2:
            assert ml_nlp2[0]["co_count"] < 2, "c1 superseded, count should drop"
        checks += 1

    print(f"PASS tag_cooccurrence selftest ({checks} checks)")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tag co-occurrence analysis for the research corpus"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_mat = sub.add_parser("matrix", help="Top co-occurring tag pairs by PMI")
    p_mat.add_argument("--db", default=DEFAULT_DB)
    p_mat.add_argument("--top", type=int, default=20)
    p_mat.add_argument("--min-pmi", type=float, default=0.0)
    p_mat.add_argument("--json", action="store_true")

    p_comm = sub.add_parser("communities", help="Tag communities via co-occurrence")
    p_comm.add_argument("--db", default=DEFAULT_DB)
    p_comm.add_argument("--json", action="store_true")

    p_hub = sub.add_parser("hubs", help="Hub tags bridging communities")
    p_hub.add_argument("--db", default=DEFAULT_DB)
    p_hub.add_argument("--top", type=int, default=10)
    p_hub.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-test")

    args = parser.parse_args()

    if args.cmd == "selftest":
        _selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "matrix":
        results = cooccurrence_matrix(conn, top_n=args.top, min_pmi=args.min_pmi)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No co-occurring tag pairs found.")
                return
            print(f"{'Tag A':<20} {'Tag B':<20} {'Count':>6} {'PMI':>8}")
            print("-" * 58)
            for r in results:
                print(f"{r['tag_a']:<20} {r['tag_b']:<20} "
                      f"{r['co_count']:>6} {r['pmi']:>8.4f}")

    elif args.cmd == "communities":
        results = tag_communities(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No tag communities found.")
                return
            for i, c in enumerate(results, 1):
                print(f"Community {i} ({c['size']} tags, "
                      f"freq {c['total_frequency']}): "
                      f"{', '.join(c['members'])}")

    elif args.cmd == "hubs":
        results = hub_tags(conn, top_n=args.top)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("No hub tags found.")
                return
            print(f"{'Tag':<20} {'Freq':>6} {'Neighbors':>10} "
                  f"{'Bridged':>8}")
            print("-" * 48)
            for r in results:
                print(f"{r['tag']:<20} {r['frequency']:>6} "
                      f"{r['neighbor_count']:>10} "
                      f"{r['communities_bridged']:>8}")

    conn.close()


if __name__ == "__main__":
    main()
