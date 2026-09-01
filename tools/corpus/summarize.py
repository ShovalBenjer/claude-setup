#!/usr/bin/env python3
"""Corpus summary: comprehensive profile of the research corpus.

Generates a detailed statistical profile of the corpus including chunk
distribution, citation density, contradiction status, artifact adoption,
freshness, and source-level breakdowns.

Usage:
    python tools/corpus/summarize.py report [--db PATH] [--json]
    python tools/corpus/summarize.py top-sources [--db PATH] [--n N] [--json]
    python tools/corpus/summarize.py freshness [--db PATH] [--json]
    python tools/corpus/summarize.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def report(conn) -> dict:
    src_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    cit_count = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    art_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

    by_status = conn.execute(
        "SELECT status, COUNT(*) FROM chunks GROUP BY status"
    ).fetchall()

    by_kind = conn.execute(
        "SELECT kind, COUNT(*) FROM chunks GROUP BY kind"
    ).fetchall()

    word_stats = conn.execute(
        "SELECT MIN(word_count), MAX(word_count), AVG(word_count), "
        "       SUM(word_count) FROM chunks"
    ).fetchone()

    cit_verified = conn.execute(
        "SELECT COUNT(*) FROM citations WHERE verified = 1"
    ).fetchone()[0]

    open_contradictions = conn.execute(
        "SELECT COUNT(*) FROM claim_edges "
        "WHERE edge_type = 'contradicts' AND resolution IS NULL"
    ).fetchone()[0]

    implemented = conn.execute(
        "SELECT COUNT(*) FROM artifacts WHERE implemented = 1"
    ).fetchone()[0]

    by_source_kind = conn.execute(
        "SELECT kind, COUNT(*) FROM sources GROUP BY kind"
    ).fetchall()

    by_liveness = conn.execute(
        "SELECT liveness, COUNT(*) FROM sources GROUP BY liveness"
    ).fetchall()

    return {
        "totals": {
            "sources": src_count,
            "chunks": chunk_count,
            "citations": cit_count,
            "claim_edges": edge_count,
            "artifacts": art_count,
        },
        "chunks_by_status": {r[0]: r[1] for r in by_status},
        "chunks_by_kind": {r[0]: r[1] for r in by_kind},
        "word_count": {
            "min": word_stats[0] or 0,
            "max": word_stats[1] or 0,
            "avg": round(word_stats[2] or 0, 1),
            "total": word_stats[3] or 0,
        },
        "citations": {
            "total": cit_count,
            "verified": cit_verified,
            "unverified": cit_count - cit_verified,
            "density": round(cit_count / chunk_count, 2) if chunk_count else 0,
        },
        "contradictions": {
            "total": edge_count,
            "open": open_contradictions,
            "resolved": edge_count - open_contradictions,
        },
        "artifacts": {
            "total": art_count,
            "implemented": implemented,
            "discussed_only": art_count - implemented,
            "adoption_rate": (
                round(implemented / art_count, 2) if art_count else 0
            ),
        },
        "sources_by_kind": {r[0]: r[1] for r in by_source_kind},
        "sources_by_liveness": {r[0]: r[1] for r in by_liveness},
    }


def top_sources(conn, n: int = 15) -> list[dict]:
    rows = conn.execute(
        "SELECT s.source_id, s.title, s.canonical_uri, s.kind, "
        "       COUNT(c.chunk_id) as chunk_count, "
        "       SUM(c.word_count) as total_words "
        "FROM sources s "
        "LEFT JOIN chunks c ON s.source_id = c.source_id "
        "GROUP BY s.source_id "
        "ORDER BY chunk_count DESC "
        "LIMIT ?",
        (n,),
    ).fetchall()

    return [
        {
            "source_id": r[0],
            "title": r[1],
            "uri": r[2],
            "kind": r[3],
            "chunk_count": r[4],
            "total_words": r[5] or 0,
        }
        for r in rows
    ]


def freshness_profile(conn) -> dict:
    by_liveness = conn.execute(
        "SELECT liveness, COUNT(*) FROM sources GROUP BY liveness"
    ).fetchall()

    stale_sources = conn.execute(
        "SELECT s.source_id, s.title, s.liveness, s.fetched_utc "
        "FROM sources s WHERE s.liveness IN ('stale', 'archived', 'dead') "
        "ORDER BY s.fetched_utc"
    ).fetchall()

    superseded = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'superseded'"
    ).fetchone()[0]

    total_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    return {
        "sources_by_liveness": {r[0]: r[1] for r in by_liveness},
        "stale_sources": [
            {
                "source_id": r[0],
                "title": r[1],
                "liveness": r[2],
                "fetched_utc": r[3],
            }
            for r in stale_sources[:20]
        ],
        "superseded_chunks": superseded,
        "total_chunks": total_chunks,
        "superseded_rate": (
            round(superseded / total_chunks, 3) if total_chunks else 0
        ),
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        for sid, uri, liveness in [
            ("s1", "/doc1.md", "live"),
            ("s2", "/doc2.md", "live"),
            ("s3", "/doc3.md", "stale"),
        ]:
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Doc', 'MIT', 'vendor', "
                " 'test', ?, ?, ?, ?, 100, NULL)",
                (sid, uri, now, liveness, now, _sha256(sid)),
            )

        chunk_data = [
            ("c1", "s1", "prose", "accepted", "chunk one text here", 0),
            ("c2", "s1", "code", "accepted", "def f(): pass", 1),
            ("c3", "s2", "prose", "quarantined", "quarantined text", 0),
            ("c4", "s2", "claim", "accepted", "a claim about x", 1),
            ("c5", "s3", "prose", "superseded", "old text here", 0),
        ]
        for cid, sid, kind, status, text, ordinal in chunk_data:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, ordinal, kind, text, text, len(text.split()),
                 _sha256(text), status, now),
            )

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) "
            "VALUES ('ci1', 'c1', 'https://example.com', 'ref', 'p1', 1)"
        )
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) "
            "VALUES ('ci2', 'c4', 'https://other.com', 'ref', 'p2', 0)"
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES ('e1', 'c1', 'c4', 'contradicts', 'test', 0.8, ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES ('a1', 'c1', 'library', 'numpy', 'import numpy', 1, "
            " 'tools/x.py:1')"
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES ('a2', 'c4', 'library', 'pandas', 'import pandas', 0, "
            " NULL)"
        )
        conn.commit()

        # 1: report returns totals
        r = report(conn)
        checks += 1
        if r["totals"]["sources"] != 3:
            failures.append(f"sources = {r['totals']['sources']}")
        if r["totals"]["chunks"] != 5:
            failures.append(f"chunks = {r['totals']['chunks']}")

        # 2: chunks_by_status counts
        checks += 1
        if r["chunks_by_status"].get("accepted") != 3:
            failures.append(
                f"accepted = {r['chunks_by_status'].get('accepted')}"
            )

        # 3: chunks_by_kind counts
        checks += 1
        if r["chunks_by_kind"].get("prose") != 3:
            failures.append(
                f"prose = {r['chunks_by_kind'].get('prose')}"
            )

        # 4: word_count stats
        checks += 1
        if r["word_count"]["total"] <= 0:
            failures.append("word_count total <= 0")
        if r["word_count"]["min"] <= 0:
            failures.append("word_count min <= 0")

        # 5: citation density
        checks += 1
        if r["citations"]["total"] != 2:
            failures.append(f"citations = {r['citations']['total']}")
        if r["citations"]["verified"] != 1:
            failures.append(f"verified = {r['citations']['verified']}")

        # 6: contradictions
        checks += 1
        if r["contradictions"]["open"] != 1:
            failures.append(f"open = {r['contradictions']['open']}")

        # 7: artifacts adoption
        checks += 1
        if r["artifacts"]["implemented"] != 1:
            failures.append(
                f"implemented = {r['artifacts']['implemented']}"
            )
        if r["artifacts"]["adoption_rate"] != 0.5:
            failures.append(
                f"adoption = {r['artifacts']['adoption_rate']}"
            )

        # 8: sources_by_kind
        checks += 1
        if "local_md" not in r["sources_by_kind"]:
            failures.append("sources_by_kind missing local_md")

        # 9: top_sources returns ranked list
        tops = top_sources(conn, n=5)
        checks += 1
        if len(tops) != 3:
            failures.append(f"top_sources returned {len(tops)}")
        if tops and tops[0]["chunk_count"] < tops[-1]["chunk_count"]:
            failures.append("top_sources not sorted by chunk_count")

        # 10: top_sources result shape
        checks += 1
        if tops:
            required = {"source_id", "title", "uri", "kind",
                        "chunk_count", "total_words"}
            missing = required - set(tops[0].keys())
            if missing:
                failures.append(f"top_sources missing: {missing}")

        # 11: freshness_profile works
        fp = freshness_profile(conn)
        checks += 1
        if "live" not in fp["sources_by_liveness"]:
            failures.append("freshness missing live")
        if "stale" not in fp["sources_by_liveness"]:
            failures.append("freshness missing stale")

        # 12: stale_sources listed
        checks += 1
        if len(fp["stale_sources"]) != 1:
            failures.append(
                f"stale_sources = {len(fp['stale_sources'])}, expected 1"
            )

        # 13: superseded rate
        checks += 1
        if fp["superseded_chunks"] != 1:
            failures.append(f"superseded = {fp['superseded_chunks']}")
        if fp["superseded_rate"] != 0.2:
            failures.append(f"superseded_rate = {fp['superseded_rate']}")

        # 14: top_sources respects limit
        tops_1 = top_sources(conn, n=1)
        checks += 1
        if len(tops_1) != 1:
            failures.append(f"top_sources(1) returned {len(tops_1)}")

        # 15: JSON serializable
        checks += 1
        try:
            json.dumps(r)
            json.dumps(tops)
            json.dumps(fp)
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        # 16: empty corpus
        conn2 = connect(Path(tmp) / "empty.db")
        init_schema(conn2)
        r2 = report(conn2)
        checks += 1
        if r2["totals"]["sources"] != 0:
            failures.append("empty corpus sources != 0")
        if r2["citations"]["density"] != 0:
            failures.append("empty corpus density != 0")
        conn2.close()

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS summarize selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_r = sub.add_parser("report", help="Full corpus summary report")
    p_r.add_argument("--db", default=None)
    p_r.add_argument("--json", action="store_true", dest="as_json")

    p_t = sub.add_parser("top-sources", help="Top sources by chunk count")
    p_t.add_argument("--db", default=None)
    p_t.add_argument("--n", type=int, default=15)
    p_t.add_argument("--json", action="store_true", dest="as_json")

    p_f = sub.add_parser("freshness", help="Freshness profile")
    p_f.add_argument("--db", default=None)
    p_f.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    conn = connect(args.db)

    if args.command == "report":
        r = report(conn)
        if args.as_json:
            print(json.dumps(r, indent=2))
        else:
            t = r["totals"]
            print(f"  Sources: {t['sources']}, Chunks: {t['chunks']}, "
                  f"Citations: {t['citations']}")
            print(f"  Edges: {t['claim_edges']}, Artifacts: {t['artifacts']}")
            print()
            print("  Chunks by status:")
            for s, c in sorted(r["chunks_by_status"].items()):
                print(f"    {s}: {c}")
            print()
            print("  Chunks by kind:")
            for k, c in sorted(r["chunks_by_kind"].items()):
                print(f"    {k}: {c}")
            print()
            w = r["word_count"]
            print(f"  Words: {w['total']} total, "
                  f"{w['min']}-{w['max']} range, {w['avg']} avg")
            print()
            ci = r["citations"]
            print(f"  Citations: {ci['verified']} verified / "
                  f"{ci['total']} total (density: {ci['density']})")
            ct = r["contradictions"]
            print(f"  Contradictions: {ct['open']} open / {ct['total']} total")
            a = r["artifacts"]
            print(f"  Artifacts: {a['implemented']} implemented / "
                  f"{a['total']} total ({a['adoption_rate']} adoption)")
        conn.close()
        return 0

    if args.command == "top-sources":
        tops = top_sources(conn, args.n)
        if args.as_json:
            print(json.dumps(tops, indent=2))
        else:
            for t in tops:
                print(f"  {t['chunk_count']:4d} chunks  "
                      f"{t['total_words']:6d} words  {t['title']}")
            print()
            print(f"  {len(tops)} source(s)")
        conn.close()
        return 0

    if args.command == "freshness":
        fp = freshness_profile(conn)
        if args.as_json:
            print(json.dumps(fp, indent=2))
        else:
            print("  Sources by liveness:")
            for l, c in sorted(fp["sources_by_liveness"].items()):
                print(f"    {l}: {c}")
            print()
            print(f"  Superseded chunks: {fp['superseded_chunks']} / "
                  f"{fp['total_chunks']} "
                  f"({fp['superseded_rate']:.1%})")
            if fp["stale_sources"]:
                print()
                print("  Stale/archived/dead sources:")
                for s in fp["stale_sources"]:
                    print(f"    [{s['liveness']}] {s['title']}")
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
