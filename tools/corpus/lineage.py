#!/usr/bin/env python3
"""Corpus lineage: trace provenance chains through the corpus.

Given a chunk or source, traces its citation chain, contradiction edges,
supersession history, and derivation relationships. Answers "where did
this come from" and "what depends on it."

Usage:
    python tools/corpus/lineage.py chunk CHUNK_ID [--db PATH] [--depth N]
        [--json]
    python tools/corpus/lineage.py source SOURCE_ID [--db PATH] [--json]
    python tools/corpus/lineage.py orphans [--db PATH] [--json]
    python tools/corpus/lineage.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def chunk_lineage(conn, chunk_id: str, depth: int = 3) -> dict:
    row = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, c.status, c.word_count, "
        "       c.heading_path, s.title, s.canonical_uri "
        "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.chunk_id = ?",
        (chunk_id,),
    ).fetchone()

    if not row:
        return {"chunk_id": chunk_id, "found": False}

    chunk_info = {
        "chunk_id": row[0], "source_id": row[1], "kind": row[2],
        "status": row[3], "word_count": row[4], "heading_path": row[5],
        "source_title": row[6], "source_uri": row[7],
    }

    citations = conn.execute(
        "SELECT citation_id, target_uri, tag, locator, verified "
        "FROM citations WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchall()
    cite_list = [
        {
            "citation_id": r[0], "target_uri": r[1], "tag": r[2],
            "locator": r[3], "verified": bool(r[4]),
        }
        for r in citations
    ]

    outgoing = conn.execute(
        "SELECT edge_id, target_chunk, edge_type, basis, confidence, "
        "       resolution "
        "FROM claim_edges WHERE source_chunk = ?",
        (chunk_id,),
    ).fetchall()
    out_edges = [
        {
            "edge_id": r[0], "target_chunk": r[1], "edge_type": r[2],
            "basis": r[3], "confidence": r[4], "resolution": r[5],
        }
        for r in outgoing
    ]

    incoming = conn.execute(
        "SELECT edge_id, source_chunk, edge_type, basis, confidence, "
        "       resolution "
        "FROM claim_edges WHERE target_chunk = ?",
        (chunk_id,),
    ).fetchall()
    in_edges = [
        {
            "edge_id": r[0], "source_chunk": r[1], "edge_type": r[2],
            "basis": r[3], "confidence": r[4], "resolution": r[5],
        }
        for r in incoming
    ]

    artifacts = conn.execute(
        "SELECT artifact_id, artifact_type, name, implemented, evidence_path "
        "FROM artifacts WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchall()
    art_list = [
        {
            "artifact_id": r[0], "artifact_type": r[1], "name": r[2],
            "implemented": bool(r[3]), "evidence_path": r[4],
        }
        for r in artifacts
    ]

    downstream = []
    if depth > 0:
        for edge in out_edges:
            child = chunk_lineage(conn, edge["target_chunk"], depth - 1)
            if child.get("found", False):
                downstream.append({
                    "edge_type": edge["edge_type"],
                    "chunk": child,
                })

    return {
        "found": True,
        "chunk": chunk_info,
        "citations": cite_list,
        "outgoing_edges": out_edges,
        "incoming_edges": in_edges,
        "artifacts": art_list,
        "downstream": downstream,
    }


def source_lineage(conn, source_id: str) -> dict:
    row = conn.execute(
        "SELECT source_id, canonical_uri, kind, title, liveness, "
        "       fetched_utc, content_sha256, bytes, supersedes "
        "FROM sources WHERE source_id = ?",
        (source_id,),
    ).fetchone()

    if not row:
        return {"source_id": source_id, "found": False}

    source_info = {
        "source_id": row[0], "uri": row[1], "kind": row[2],
        "title": row[3], "liveness": row[4], "fetched_utc": row[5],
        "bytes": row[7], "supersedes": row[8],
    }

    chunks = conn.execute(
        "SELECT chunk_id, kind, status, word_count, ordinal "
        "FROM chunks WHERE source_id = ? ORDER BY ordinal",
        (source_id,),
    ).fetchall()
    chunk_list = [
        {
            "chunk_id": r[0], "kind": r[1], "status": r[2],
            "word_count": r[3], "ordinal": r[4],
        }
        for r in chunks
    ]

    superseded_by = conn.execute(
        "SELECT source_id, title FROM sources WHERE supersedes = ?",
        (source_id,),
    ).fetchall()
    superseded_list = [
        {"source_id": r[0], "title": r[1]} for r in superseded_by
    ]

    supersedes_info = None
    if source_info["supersedes"]:
        sup = conn.execute(
            "SELECT source_id, title, canonical_uri "
            "FROM sources WHERE source_id = ?",
            (source_info["supersedes"],),
        ).fetchone()
        if sup:
            supersedes_info = {
                "source_id": sup[0], "title": sup[1], "uri": sup[2],
            }

    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations ci "
        "JOIN chunks c ON ci.chunk_id = c.chunk_id "
        "WHERE c.source_id = ?",
        (source_id,),
    ).fetchone()[0]

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM claim_edges e "
        "JOIN chunks c ON e.source_chunk = c.chunk_id "
        "WHERE c.source_id = ?",
        (source_id,),
    ).fetchone()[0]

    return {
        "found": True,
        "source": source_info,
        "chunks": chunk_list,
        "chunk_count": len(chunk_list),
        "superseded_by": superseded_list,
        "supersedes_target": supersedes_info,
        "total_citations": total_citations,
        "total_outgoing_edges": total_edges,
    }


def find_orphans(conn) -> dict:
    uncited_accepted = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' AND c.kind = 'claim' "
        "  AND ci.citation_id IS NULL"
    ).fetchall()

    isolated = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id "
        "LEFT JOIN claim_edges eo ON eo.source_chunk = c.chunk_id "
        "LEFT JOIN claim_edges ei ON ei.target_chunk = c.chunk_id "
        "LEFT JOIN artifacts a ON a.chunk_id = c.chunk_id "
        "WHERE c.status = 'accepted' "
        "  AND ci.citation_id IS NULL "
        "  AND eo.edge_id IS NULL "
        "  AND ei.edge_id IS NULL "
        "  AND a.artifact_id IS NULL"
    ).fetchall()

    return {
        "uncited_claims": [
            {"chunk_id": r[0], "source_id": r[1], "kind": r[2],
             "source_title": r[3]}
            for r in uncited_accepted[:50]
        ],
        "uncited_claim_count": len(uncited_accepted),
        "isolated_chunks": [
            {"chunk_id": r[0], "source_id": r[1], "kind": r[2],
             "source_title": r[3]}
            for r in isolated[:50]
        ],
        "isolated_count": len(isolated),
    }


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

        for cid, sid, kind, text, ordinal in [
            ("c1", "s1", "claim", "first claim text", 0),
            ("c2", "s1", "prose", "supporting prose", 1),
            ("c3", "s2", "claim", "second doc claim", 0),
            ("c4", "s2", "prose", "isolated chunk no links", 1),
        ]:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, ordinal, kind, text, text, len(text.split()),
                 _sha256(text), now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) "
            "VALUES ('ci1', 'c1', 'https://example.com', 'S1', 'p1', 1)"
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES ('e1', 'c1', 'c3', 'contradicts', 'test', 0.8, ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES ('a1', 'c1', 'library', 'numpy', 'import numpy', 1, "
            " 'tools/x.py:1')"
        )
        conn.commit()

        # 1: chunk lineage returns found=True for existing chunk
        lin = chunk_lineage(conn, "c1")
        checks += 1
        if not lin.get("found"):
            failures.append("c1 not found")

        # 2: chunk info populated
        checks += 1
        if lin["chunk"]["kind"] != "claim":
            failures.append(f"c1 kind = {lin['chunk']['kind']}")

        # 3: citations listed
        checks += 1
        if len(lin["citations"]) != 1:
            failures.append(f"c1 citations = {len(lin['citations'])}")

        # 4: outgoing edges listed
        checks += 1
        if len(lin["outgoing_edges"]) != 1:
            failures.append(f"c1 outgoing = {len(lin['outgoing_edges'])}")

        # 5: artifacts listed
        checks += 1
        if len(lin["artifacts"]) != 1:
            failures.append(f"c1 artifacts = {len(lin['artifacts'])}")

        # 6: downstream traversal works
        checks += 1
        if len(lin["downstream"]) != 1:
            failures.append(f"c1 downstream = {len(lin['downstream'])}")

        # 7: incoming edges on target
        lin3 = chunk_lineage(conn, "c3")
        checks += 1
        if len(lin3["incoming_edges"]) != 1:
            failures.append(f"c3 incoming = {len(lin3['incoming_edges'])}")

        # 8: not found for nonexistent chunk
        lin_bad = chunk_lineage(conn, "nonexistent")
        checks += 1
        if lin_bad.get("found", True):
            failures.append("nonexistent chunk returned found=True")

        # 9: source lineage works
        slin = source_lineage(conn, "s1")
        checks += 1
        if not slin.get("found"):
            failures.append("s1 source not found")
        if slin["chunk_count"] != 2:
            failures.append(f"s1 chunk_count = {slin['chunk_count']}")

        # 10: source lineage citations counted
        checks += 1
        if slin["total_citations"] != 1:
            failures.append(f"s1 citations = {slin['total_citations']}")

        # 11: source not found
        slin_bad = source_lineage(conn, "nonexistent")
        checks += 1
        if slin_bad.get("found", True):
            failures.append("nonexistent source returned found=True")

        # 12: orphans finds uncited claims
        orph = find_orphans(conn)
        checks += 1
        if orph["uncited_claim_count"] != 1:
            failures.append(
                f"uncited claims = {orph['uncited_claim_count']}, expected 1"
            )

        # 13: orphans finds isolated chunks
        checks += 1
        if orph["isolated_count"] < 1:
            failures.append(f"isolated = {orph['isolated_count']}")

        # 14: depth=0 stops traversal
        lin_shallow = chunk_lineage(conn, "c1", depth=0)
        checks += 1
        if lin_shallow["downstream"]:
            failures.append("depth=0 still traversed downstream")

        # 15: JSON serializable
        checks += 1
        try:
            json.dumps(lin)
            json.dumps(slin)
            json.dumps(orph)
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        # 16: supersedes tracking
        conn.execute(
            "UPDATE sources SET supersedes = 's1' WHERE source_id = 's2'"
        )
        conn.commit()
        slin2 = source_lineage(conn, "s1")
        checks += 1
        if not slin2["superseded_by"]:
            failures.append("s1 not showing superseded_by s2")
        slin2b = source_lineage(conn, "s2")
        if not slin2b["supersedes_target"]:
            failures.append("s2 not showing supersedes_target s1")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS lineage selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_c = sub.add_parser("chunk", help="Trace chunk lineage")
    p_c.add_argument("chunk_id")
    p_c.add_argument("--db", default=None)
    p_c.add_argument("--depth", type=int, default=3)
    p_c.add_argument("--json", action="store_true", dest="as_json")

    p_s = sub.add_parser("source", help="Trace source lineage")
    p_s.add_argument("source_id")
    p_s.add_argument("--db", default=None)
    p_s.add_argument("--json", action="store_true", dest="as_json")

    p_o = sub.add_parser("orphans", help="Find unlinked chunks")
    p_o.add_argument("--db", default=None)
    p_o.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    conn = connect(args.db)

    if args.command == "chunk":
        result = chunk_lineage(conn, args.chunk_id, args.depth)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if not result.get("found"):
                print(f"  chunk {args.chunk_id} not found")
            else:
                c = result["chunk"]
                print(f"  {c['chunk_id']} [{c['kind']}] {c['status']}")
                print(f"  source: {c['source_title']}")
                print(f"  heading: {c['heading_path']}")
                if result["citations"]:
                    print(f"\n  Citations ({len(result['citations'])}):")
                    for ci in result["citations"]:
                        v = "verified" if ci["verified"] else "unverified"
                        print(f"    {ci['target_uri']} ({v})")
                if result["outgoing_edges"]:
                    print(f"\n  Outgoing edges ({len(result['outgoing_edges'])}):")
                    for e in result["outgoing_edges"]:
                        print(f"    {e['edge_type']} -> {e['target_chunk'][:16]}")
                if result["incoming_edges"]:
                    print(f"\n  Incoming edges ({len(result['incoming_edges'])}):")
                    for e in result["incoming_edges"]:
                        print(f"    {e['source_chunk'][:16]} -> {e['edge_type']}")
                if result["artifacts"]:
                    print(f"\n  Artifacts ({len(result['artifacts'])}):")
                    for a in result["artifacts"]:
                        impl = "implemented" if a["implemented"] else "discussed"
                        print(f"    {a['name']} ({impl})")
        conn.close()
        return 0

    if args.command == "source":
        result = source_lineage(conn, args.source_id)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if not result.get("found"):
                print(f"  source {args.source_id} not found")
            else:
                s = result["source"]
                print(f"  {s['source_id']} [{s['kind']}] {s['liveness']}")
                print(f"  {s['title']}")
                print(f"  {s['uri']}")
                print(f"\n  Chunks: {result['chunk_count']}")
                for c in result["chunks"]:
                    print(f"    {c['chunk_id'][:16]} [{c['kind']}] {c['status']}")
                print(f"\n  Citations: {result['total_citations']}")
                print(f"  Outgoing edges: {result['total_outgoing_edges']}")
                if result["supersedes_target"]:
                    t = result["supersedes_target"]
                    print(f"  Supersedes: {t['title']}")
                if result["superseded_by"]:
                    print("  Superseded by:")
                    for sb in result["superseded_by"]:
                        print(f"    {sb['title']}")
        conn.close()
        return 0

    if args.command == "orphans":
        result = find_orphans(conn)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"  Uncited claims: {result['uncited_claim_count']}")
            if result["uncited_claims"]:
                for c in result["uncited_claims"][:10]:
                    print(f"    {c['chunk_id'][:16]} from {c['source_title']}")
            print(f"\n  Isolated chunks: {result['isolated_count']}")
            if result["isolated_chunks"]:
                for c in result["isolated_chunks"][:10]:
                    print(f"    {c['chunk_id'][:16]} [{c['kind']}] "
                          f"from {c['source_title']}")
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
