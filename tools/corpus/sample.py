#!/usr/bin/env python3
"""Corpus chunk sampling: stratified random samples for quality review.

Draws random samples from the corpus, optionally stratified by source,
kind, or status. Useful for spot-checking chunk quality, reviewing
quarantined content, and auditing ingestion results.

Usage:
    python tools/corpus/sample.py draw [--db PATH] [--n N] [--kind KIND]
        [--status STATUS] [--source SOURCE_ID] [--min-words N]
        [--max-words N] [--seed SEED] [--json]
    python tools/corpus/sample.py stratified [--db PATH] [--per-stratum N]
        [--by {kind,status,source}] [--json]
    python tools/corpus/sample.py selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def draw(conn, n: int = 10, kind: str | None = None,
         status: str | None = None, source_id: str | None = None,
         min_words: int | None = None, max_words: int | None = None,
         seed: int | None = None) -> list[dict]:
    where_parts: list[str] = []
    params: list = []

    if kind:
        where_parts.append("c.kind = ?")
        params.append(kind)
    if status:
        where_parts.append("c.status = ?")
        params.append(status)
    if source_id:
        where_parts.append("c.source_id = ?")
        params.append(source_id)
    if min_words is not None:
        where_parts.append("c.word_count >= ?")
        params.append(min_words)
    if max_words is not None:
        where_parts.append("c.word_count <= ?")
        params.append(max_words)

    where = " AND ".join(where_parts) if where_parts else "1=1"

    rows = conn.execute(
        f"SELECT c.chunk_id, c.source_id, c.kind, c.status, c.word_count, "
        f"       c.norm_text, c.heading_path, s.title, s.canonical_uri "
        f"FROM chunks c "
        f"JOIN sources s ON c.source_id = s.source_id "
        f"WHERE {where}",
        params,
    ).fetchall()

    if seed is not None:
        random.seed(seed)

    sample_size = min(n, len(rows))
    selected = random.sample(rows, sample_size) if rows else []

    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "kind": r[2],
            "status": r[3],
            "word_count": r[4],
            "text": r[5][:500],
            "heading_path": r[6],
            "source_title": r[7],
            "source_uri": r[8],
        }
        for r in selected
    ]


def stratified(conn, by: str = "kind",
               per_stratum: int = 3) -> dict:
    queries = {
        "kind": "SELECT DISTINCT kind FROM chunks",
        "status": "SELECT DISTINCT status FROM chunks",
        "source": "SELECT DISTINCT source_id FROM chunks",
    }
    strata_rows = conn.execute(queries.get(by, queries["kind"])).fetchall()
    strata = [r[0] for r in strata_rows]

    result: dict = {"by": by, "strata": {}}
    for stratum in sorted(strata):
        if by == "source":
            samples = draw(conn, n=per_stratum, source_id=stratum)
        elif by == "status":
            samples = draw(conn, n=per_stratum, status=stratum)
        else:
            samples = draw(conn, n=per_stratum, kind=stratum)
        result["strata"][stratum] = {
            "count": len(samples),
            "samples": samples,
        }

    result["total_strata"] = len(strata)
    result["samples_per_stratum"] = per_stratum
    return result


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        for sid, uri in [("s1", "/doc1.md"), ("s2", "/doc2.md"),
                         ("s3", "/doc3.md")]:
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Doc', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (sid, uri, now, now, _sha256(sid)),
            )

        chunk_data = [
            ("c1", "s1", "prose", "accepted", "first chunk of prose text", 0),
            ("c2", "s1", "code", "accepted", "def hello(): pass", 1),
            ("c3", "s2", "prose", "quarantined", "quarantined text here", 0),
            ("c4", "s2", "claim", "accepted", "claim about something", 1),
            ("c5", "s3", "prose", "accepted", "more prose content for test", 0),
            ("c6", "s3", "prose", "rejected", "rejected prose chunk here", 1),
            ("c7", "s1", "prose", "accepted", "a very short one", 2),
            ("c8", "s2", "code", "accepted", "import os; print(os.getcwd())", 2),
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
        conn.commit()

        # 1: draw returns results
        samples = draw(conn, n=3, seed=42)
        checks += 1
        if len(samples) != 3:
            failures.append(f"draw(3) returned {len(samples)}")

        # 2: draw respects n limit
        samples = draw(conn, n=2, seed=42)
        checks += 1
        if len(samples) != 2:
            failures.append(f"draw(2) returned {len(samples)}")

        # 3: draw with kind filter
        samples = draw(conn, n=10, kind="code", seed=42)
        checks += 1
        if not all(s["kind"] == "code" for s in samples):
            failures.append("kind filter not applied")
        if len(samples) != 2:
            failures.append(f"code filter returned {len(samples)}, expected 2")

        # 4: draw with status filter
        samples = draw(conn, n=10, status="quarantined", seed=42)
        checks += 1
        if len(samples) != 1:
            failures.append(f"quarantined filter returned {len(samples)}")

        # 5: draw with source filter
        samples = draw(conn, n=10, source_id="s1", seed=42)
        checks += 1
        if len(samples) != 3:
            failures.append(f"source filter returned {len(samples)}, expected 3")

        # 6: draw with min_words filter
        samples = draw(conn, n=10, min_words=5, seed=42)
        checks += 1
        if any(s["word_count"] < 5 for s in samples):
            failures.append("min_words filter not applied")

        # 7: draw with max_words filter
        samples = draw(conn, n=10, max_words=3, seed=42)
        checks += 1
        if any(s["word_count"] > 3 for s in samples):
            failures.append("max_words filter not applied")

        # 8: draw with seed is reproducible
        a = draw(conn, n=5, seed=123)
        b = draw(conn, n=5, seed=123)
        checks += 1
        if [s["chunk_id"] for s in a] != [s["chunk_id"] for s in b]:
            failures.append("seed does not produce reproducible results")

        # 9: result shape has required fields
        samples = draw(conn, n=1, seed=42)
        checks += 1
        if samples:
            required = {"chunk_id", "source_id", "kind", "status",
                        "word_count", "text", "source_title"}
            missing = required - set(samples[0].keys())
            if missing:
                failures.append(f"missing fields: {missing}")

        # 10: text is truncated to 500 chars
        checks += 1
        if samples and len(samples[0]["text"]) > 500:
            failures.append("text not truncated to 500")

        # 11: draw n > population returns all
        samples = draw(conn, n=100, seed=42)
        checks += 1
        if len(samples) != 8:
            failures.append(f"n>pop returned {len(samples)}, expected 8")

        # 12: stratified by kind
        result = stratified(conn, by="kind", per_stratum=2)
        checks += 1
        if result["total_strata"] != 3:
            failures.append(f"strata by kind = {result['total_strata']}, expected 3")

        # 13: stratified by status
        result = stratified(conn, by="status", per_stratum=2)
        checks += 1
        if result["total_strata"] != 3:
            failures.append(
                f"strata by status = {result['total_strata']}, expected 3"
            )

        # 14: stratified by source
        result = stratified(conn, by="source", per_stratum=1)
        checks += 1
        if result["total_strata"] != 3:
            failures.append(
                f"strata by source = {result['total_strata']}, expected 3"
            )

        # 15: stratified result has expected structure
        checks += 1
        if "strata" not in result or "total_strata" not in result:
            failures.append("stratified missing expected keys")

        # 16: JSON serializable
        checks += 1
        try:
            json.dumps(result)
            json.dumps(draw(conn, n=3, seed=42))
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS sample selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_draw = sub.add_parser("draw", help="Draw random sample")
    p_draw.add_argument("--db", default=None)
    p_draw.add_argument("--n", type=int, default=10)
    p_draw.add_argument("--kind", default=None)
    p_draw.add_argument("--status", default=None)
    p_draw.add_argument("--source", default=None, dest="source_id")
    p_draw.add_argument("--min-words", type=int, default=None)
    p_draw.add_argument("--max-words", type=int, default=None)
    p_draw.add_argument("--seed", type=int, default=None)
    p_draw.add_argument("--json", action="store_true", dest="as_json")

    p_strat = sub.add_parser("stratified",
                             help="Stratified sample by kind/status/source")
    p_strat.add_argument("--db", default=None)
    p_strat.add_argument("--per-stratum", type=int, default=3)
    p_strat.add_argument("--by", choices=["kind", "status", "source"],
                         default="kind")
    p_strat.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    conn = connect(args.db)

    if args.command == "draw":
        results = draw(conn, args.n, args.kind, args.status,
                       args.source_id, args.min_words, args.max_words,
                       args.seed)
        if args.as_json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  no matching chunks")
            else:
                for r in results:
                    print(f"  {r['chunk_id'][:16]} [{r['kind']}] "
                          f"({r['word_count']} words) {r['status']}")
                    print(f"    source: {r['source_title']}")
                    print(f"    {r['text'][:120]}")
                    print()
                print(f"  {len(results)} sample(s)")
        conn.close()
        return 0

    if args.command == "stratified":
        result = stratified(conn, args.by, args.per_stratum)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"  Stratified by: {result['by']}")
            print(f"  Strata: {result['total_strata']}")
            print()
            for name, data in result["strata"].items():
                print(f"  [{name}] ({data['count']} samples)")
                for s in data["samples"]:
                    print(f"    {s['chunk_id'][:16]} ({s['word_count']} words)")
                    print(f"      {s['text'][:100]}")
                print()
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
