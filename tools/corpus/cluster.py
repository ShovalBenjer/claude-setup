#!/usr/bin/env python3
"""Corpus chunk clustering: group chunks by topic similarity.

Groups chunks by simhash distance, shared citations, or co-occurrence
within sources. Useful for understanding topical structure, finding
related content across sources, and identifying potential duplicates
that escaped dedup.

Usage:
    python tools/corpus/cluster.py simhash [--db PATH] [--threshold N]
        [--status STATUS] [--json]
    python tools/corpus/cluster.py citation [--db PATH] [--min-shared N]
        [--json]
    python tools/corpus/cluster.py source-overlap [--db PATH]
        [--min-overlap N] [--json]
    python tools/corpus/cluster.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def cluster_by_simhash(conn, threshold: int = 8,
                       status: str | None = None) -> list[dict]:
    where = "1=1"
    params: list = []
    if status:
        where = "c.status = ?"
        params.append(status)

    rows = conn.execute(
        "SELECT c.chunk_id, c.simhash, c.source_id, c.kind, "
        "       c.word_count, s.title "
        "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
        "WHERE " + where + " "
        "ORDER BY c.simhash",
        params,
    ).fetchall()

    clusters: list[list[tuple]] = []
    assigned: set[int] = set()

    for i, row_i in enumerate(rows):
        if i in assigned:
            continue
        group = [row_i]
        assigned.add(i)
        for j in range(i + 1, len(rows)):
            if j in assigned:
                continue
            if _hamming(row_i[1], rows[j][1]) <= threshold:
                group.append(rows[j])
                assigned.add(j)
        if len(group) > 1:
            clusters.append(group)

    return [
        {
            "cluster_id": idx,
            "size": len(group),
            "chunks": [
                {
                    "chunk_id": r[0],
                    "source_id": r[2],
                    "kind": r[3],
                    "word_count": r[4],
                    "source_title": r[5],
                }
                for r in group
            ],
        }
        for idx, group in enumerate(clusters)
    ]


def cluster_by_citation(conn, min_shared: int = 2) -> list[dict]:
    rows = conn.execute(
        "SELECT a.chunk_id, b.chunk_id, a.target_uri "
        "FROM citations a "
        "JOIN citations b ON a.target_uri = b.target_uri "
        "  AND a.chunk_id < b.chunk_id"
    ).fetchall()

    pair_uris: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        pair_uris[(r[0], r[1])].append(r[2])

    clusters: list[dict] = []
    for (cid_a, cid_b), uris in pair_uris.items():
        if len(uris) >= min_shared:
            info_a = conn.execute(
                "SELECT c.kind, c.word_count, s.title "
                "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
                "WHERE c.chunk_id = ?", (cid_a,)
            ).fetchone()
            info_b = conn.execute(
                "SELECT c.kind, c.word_count, s.title "
                "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
                "WHERE c.chunk_id = ?", (cid_b,)
            ).fetchone()
            clusters.append({
                "chunk_a": cid_a,
                "chunk_b": cid_b,
                "shared_uris": len(uris),
                "uris": uris[:10],
                "a_info": {
                    "kind": info_a[0], "word_count": info_a[1],
                    "source_title": info_a[2],
                } if info_a else {},
                "b_info": {
                    "kind": info_b[0], "word_count": info_b[1],
                    "source_title": info_b[2],
                } if info_b else {},
            })

    clusters.sort(key=lambda c: c["shared_uris"], reverse=True)
    return clusters


def cluster_by_source_overlap(conn, min_overlap: int = 3) -> list[dict]:
    rows = conn.execute(
        "SELECT ca.source_id, cb.source_id, COUNT(*) as overlap "
        "FROM citations a "
        "JOIN citations b ON a.target_uri = b.target_uri "
        "  AND a.chunk_id < b.chunk_id "
        "JOIN chunks ca ON a.chunk_id = ca.chunk_id "
        "JOIN chunks cb ON b.chunk_id = cb.chunk_id "
        "WHERE ca.source_id < cb.source_id "
        "GROUP BY ca.source_id, cb.source_id "
        "HAVING overlap >= ?",
        (min_overlap,),
    ).fetchall()

    results = []
    for r in rows:
        title_a = conn.execute(
            "SELECT title FROM sources WHERE source_id = ?", (r[0],)
        ).fetchone()
        title_b = conn.execute(
            "SELECT title FROM sources WHERE source_id = ?", (r[1],)
        ).fetchone()
        results.append({
            "source_a": r[0],
            "source_b": r[1],
            "title_a": title_a[0] if title_a else r[0],
            "title_b": title_b[0] if title_b else r[1],
            "shared_citations": r[2],
        })

    results.sort(key=lambda x: x["shared_citations"], reverse=True)
    return results


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        for sid, uri in [("s1", "/doc1.md"), ("s2", "/doc2.md")]:
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Doc', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (sid, uri, now, now, _sha256(sid)),
            )

        texts = [
            ("c1", "s1", "alpha bravo charlie delta echo", 0, 0b1010101010),
            ("c2", "s1", "alpha bravo charlie delta foxtrot", 1, 0b1010101011),
            ("c3", "s2", "golf hotel india juliet kilo", 0, 0b0000000000),
            ("c4", "s2", "lima mike november oscar papa", 1, 0b1111111111),
            ("c5", "s1", "alpha bravo charlie delta golf", 2, 0b1010101000),
        ]
        for cid, sid, text, ordinal, simhash in texts:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', 'prose', ?, ?, ?, ?, ?, "
                " 'accepted', ?)",
                (cid, sid, ordinal, text, text, len(text.split()),
                 _sha256(text), simhash, now),
            )

        for cit_id, chunk_id, uri in [
            ("ci1", "c1", "https://example.com/ref1"),
            ("ci2", "c2", "https://example.com/ref1"),
            ("ci3", "c1", "https://example.com/ref2"),
            ("ci4", "c2", "https://example.com/ref2"),
            ("ci5", "c3", "https://example.com/ref1"),
            ("ci6", "c3", "https://example.com/ref3"),
        ]:
            conn.execute(
                "INSERT INTO citations (citation_id, chunk_id, target_uri, "
                "tag, locator, verified) VALUES (?, ?, ?, 'ref', 'p1', 0)",
                (cit_id, chunk_id, uri),
            )
        conn.commit()

        # 1: simhash clustering finds near-duplicates
        clusters = cluster_by_simhash(conn, threshold=3)
        checks += 1
        if not clusters:
            failures.append("simhash found no clusters")

        # 2: c1, c2, c5 should cluster (hamming <= 3)
        checks += 1
        found_group = False
        for cl in clusters:
            ids = {c["chunk_id"] for c in cl["chunks"]}
            if "c1" in ids and "c2" in ids:
                found_group = True
        if not found_group:
            failures.append("c1 and c2 not clustered together")

        # 3: cluster has expected shape
        checks += 1
        if clusters:
            required = {"cluster_id", "size", "chunks"}
            missing = required - set(clusters[0].keys())
            if missing:
                failures.append(f"cluster missing fields: {missing}")

        # 4: chunk in cluster has expected shape
        checks += 1
        if clusters and clusters[0]["chunks"]:
            required = {"chunk_id", "source_id", "kind", "word_count",
                        "source_title"}
            missing = required - set(clusters[0]["chunks"][0].keys())
            if missing:
                failures.append(f"chunk missing fields: {missing}")

        # 5: status filter works
        conn.execute(
            "UPDATE chunks SET status = 'quarantined' WHERE chunk_id = 'c5'"
        )
        conn.commit()
        clusters = cluster_by_simhash(conn, threshold=3, status="accepted")
        checks += 1
        for cl in clusters:
            ids = {c["chunk_id"] for c in cl["chunks"]}
            if "c5" in ids:
                failures.append("quarantined c5 in accepted-only cluster")
        conn.execute(
            "UPDATE chunks SET status = 'accepted' WHERE chunk_id = 'c5'"
        )
        conn.commit()

        # 6: high threshold groups more
        all_clusters = cluster_by_simhash(conn, threshold=64)
        checks += 1
        if not all_clusters:
            failures.append("threshold=64 found no clusters")

        # 7: threshold=0 only groups exact simhash matches
        exact = cluster_by_simhash(conn, threshold=0)
        checks += 1
        for cl in exact:
            hashes = set()
            for c in cl["chunks"]:
                row = conn.execute(
                    "SELECT simhash FROM chunks WHERE chunk_id = ?",
                    (c["chunk_id"],)
                ).fetchone()
                hashes.add(row[0])
            if len(hashes) > 1:
                failures.append("threshold=0 grouped different simhashes")

        # 8: citation clustering finds shared-citation pairs
        cit_clusters = cluster_by_citation(conn, min_shared=2)
        checks += 1
        if not cit_clusters:
            failures.append("citation clustering found no pairs")

        # 9: c1-c2 share 2 citations
        checks += 1
        found_pair = False
        for cl in cit_clusters:
            pair = {cl["chunk_a"], cl["chunk_b"]}
            if pair == {"c1", "c2"}:
                found_pair = True
                if cl["shared_uris"] < 2:
                    failures.append(
                        f"c1-c2 shared_uris = {cl['shared_uris']}"
                    )
        if not found_pair:
            failures.append("c1-c2 citation pair not found")

        # 10: citation cluster has info fields
        checks += 1
        if cit_clusters:
            if "a_info" not in cit_clusters[0]:
                failures.append("citation cluster missing a_info")

        # 11: min_shared filter works
        high_min = cluster_by_citation(conn, min_shared=5)
        checks += 1
        if high_min:
            failures.append(f"min_shared=5 returned {len(high_min)} pairs")

        # 12: source overlap finds related sources
        overlap = cluster_by_source_overlap(conn, min_overlap=1)
        checks += 1
        if not overlap:
            failures.append("source overlap found no pairs")

        # 13: source overlap has expected shape
        checks += 1
        if overlap:
            required = {"source_a", "source_b", "title_a", "title_b",
                        "shared_citations"}
            missing = required - set(overlap[0].keys())
            if missing:
                failures.append(f"overlap missing fields: {missing}")

        # 14: high min_overlap filters correctly
        no_overlap = cluster_by_source_overlap(conn, min_overlap=100)
        checks += 1
        if no_overlap:
            failures.append("min_overlap=100 returned results")

        # 15: JSON serializable
        checks += 1
        try:
            json.dumps(clusters)
            json.dumps(cit_clusters)
            json.dumps(overlap)
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        # 16: empty corpus returns empty
        conn2 = connect(Path(tmp) / "empty.db")
        init_schema(conn2)
        checks += 1
        if cluster_by_simhash(conn2):
            failures.append("empty corpus returned simhash clusters")
        if cluster_by_citation(conn2):
            failures.append("empty corpus returned citation clusters")
        conn2.close()

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS cluster selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_sim = sub.add_parser("simhash",
                           help="Cluster by simhash similarity")
    p_sim.add_argument("--db", default=None)
    p_sim.add_argument("--threshold", type=int, default=8)
    p_sim.add_argument("--status", default=None)
    p_sim.add_argument("--json", action="store_true", dest="as_json")

    p_cit = sub.add_parser("citation",
                           help="Cluster by shared citations")
    p_cit.add_argument("--db", default=None)
    p_cit.add_argument("--min-shared", type=int, default=2)
    p_cit.add_argument("--json", action="store_true", dest="as_json")

    p_src = sub.add_parser("source-overlap",
                           help="Find sources with overlapping citations")
    p_src.add_argument("--db", default=None)
    p_src.add_argument("--min-overlap", type=int, default=3)
    p_src.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    conn = connect(args.db)

    if args.command == "simhash":
        clusters = cluster_by_simhash(conn, args.threshold, args.status)
        if args.as_json:
            print(json.dumps(clusters, indent=2))
        else:
            if not clusters:
                print("  no clusters found")
            else:
                for cl in clusters:
                    print(f"  Cluster {cl['cluster_id']} "
                          f"({cl['size']} chunks):")
                    for c in cl["chunks"]:
                        print(f"    {c['chunk_id'][:16]} [{c['kind']}] "
                              f"({c['word_count']} words)")
                        print(f"      source: {c['source_title']}")
                    print()
                print(f"  {len(clusters)} cluster(s)")
        conn.close()
        return 0

    if args.command == "citation":
        pairs = cluster_by_citation(conn, args.min_shared)
        if args.as_json:
            print(json.dumps(pairs, indent=2))
        else:
            if not pairs:
                print("  no shared-citation pairs found")
            else:
                for p in pairs:
                    print(f"  {p['chunk_a'][:16]} <-> {p['chunk_b'][:16]}"
                          f"  ({p['shared_uris']} shared)")
                    if p["a_info"]:
                        print(f"    a: {p['a_info'].get('source_title', '')}")
                    if p["b_info"]:
                        print(f"    b: {p['b_info'].get('source_title', '')}")
                    print()
                print(f"  {len(pairs)} pair(s)")
        conn.close()
        return 0

    if args.command == "source-overlap":
        pairs = cluster_by_source_overlap(conn, args.min_overlap)
        if args.as_json:
            print(json.dumps(pairs, indent=2))
        else:
            if not pairs:
                print("  no overlapping source pairs found")
            else:
                for p in pairs:
                    print(f"  {p['title_a']}")
                    print(f"    <-> {p['title_b']}")
                    print(f"    shared citations: {p['shared_citations']}")
                    print()
                print(f"  {len(pairs)} pair(s)")
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
