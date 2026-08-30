#!/usr/bin/env python3
"""Unified corpus retrieval returning the spec section 7.2 record shape.

Combines FTS5 search, vector reranking, staleness computation, trust
classification, contradiction detection, and artifact attachment into
a single query path. Each result is a record with provenance, not a
paragraph.

Usage:
    python tools/corpus/retrieve.py query TEXT [--kind KIND] [--implemented]
        [--max-age DAYS] [--k N] [--db PATH] [--json]
    python tools/corpus/retrieve.py selftest
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    _sha256,
    connect,
    init_schema,
)

try:
    from embed import _vec_paths
    from embed import rerank as _rerank
except ImportError:
    _rerank = None
    _vec_paths = None

try:
    from license_gate import check_source as _check_trust
except ImportError:
    _check_trust = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import repo_root  # noqa: E402

ROOT = repo_root.resolve()

STALE_SOURCE_DAYS = 548
UNVERIFIED_FETCH_DAYS = 90


def _now_utc():
    return datetime.datetime.utcnow()


def _parse_utc(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _staleness(source_row, chunk_row, db_path=None):
    """Compute staleness verdict per spec section 7.3.

    Four signals; verdict is the worst of them.
    """
    now = _now_utc()
    reasons = []
    age_days = None

    upstream_mtime = _parse_utc(source_row["upstream_mtime"])
    if upstream_mtime:
        age_days = (now - upstream_mtime).days
        if source_row["liveness"] == "archived":
            reasons.append("archived")
        elif age_days > STALE_SOURCE_DAYS:
            reasons.append("stale")

    fetched_utc = _parse_utc(source_row["fetched_utc"])
    if fetched_utc:
        fetch_age = (now - fetched_utc).days
        if fetch_age > UNVERIFIED_FETCH_DAYS:
            reasons.append("unverified")

    if source_row["kind"] == "local_md":
        canonical = source_row.get("canonical_uri") or source_row.get("uri", "")
        p = Path(canonical)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            content = p.read_text(errors="replace")
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if file_hash != source_row["content_sha256"]:
                reasons.append("drifted")

    if db_path is not None and _vec_paths is not None:
        npy_path, meta_path = _vec_paths(db_path)
        if meta_path and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            from embed import _get_generation
            conn_temp = connect(db_path)
            current_gen = _get_generation(conn_temp)
            conn_temp.close()
            if meta.get("generation") != current_gen:
                reasons.append("rerank_unavailable")

    if not reasons:
        verdict = "fresh"
    elif "drifted" in reasons:
        verdict = "drifted"
    elif "archived" in reasons:
        verdict = "archived"
    elif "stale" in reasons:
        verdict = "stale"
    elif "unverified" in reasons:
        verdict = "unverified"
    else:
        verdict = "fresh"

    return {
        "verdict": verdict,
        "age_days": age_days,
        "reasons": reasons,
    }


def _trust_for_source(source_row):
    verdict = source_row["license_verdict"]
    if verdict in ("vendor",):
        return "trusted"
    if verdict == "index_only":
        return "untrusted"
    return "untrusted"


def _get_citations(conn, chunk_id):
    rows = conn.execute(
        "SELECT target_uri, verified FROM citations WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchall()
    return [{"target_uri": r[0], "verified": bool(r[1])} for r in rows]


def _get_contradictions(conn, chunk_id):
    rows = conn.execute(
        "SELECT target_chunk, basis, confidence, resolution "
        "FROM claim_edges WHERE source_chunk = ? AND edge_type = 'contradicts'",
        (chunk_id,),
    ).fetchall()
    return [
        {"target_chunk": r[0], "basis": r[1],
         "confidence": r[2], "resolution": r[3]}
        for r in rows
    ]


def _get_artifacts(conn, chunk_id):
    rows = conn.execute(
        "SELECT name, artifact_type, implemented, evidence_path, snippet "
        "FROM artifacts WHERE chunk_id = ?",
        (chunk_id,),
    ).fetchall()
    return [
        {"name": r[0], "type": r[1], "implemented": bool(r[2]),
         "evidence_path": r[3], "snippet": r[4]}
        for r in rows
    ]


def query(conn, query_text, kind=None, implemented_only=False,
          max_age_days=None, top_k=10, db_path=None):
    """Execute a corpus query returning section 7.2 records.

    Returns a list of result records.
    """
    words = query_text.lower().split()
    if not words:
        return []

    fts_query = " OR ".join(words)

    status_filter = "c.status = 'accepted'"
    kind_filter = ""
    if kind:
        kinds = [k.strip() for k in kind.split(",")]
        placeholders = ",".join("?" * len(kinds))
        kind_filter = f" AND c.kind IN ({placeholders})"

    sql = (
        f"SELECT c.chunk_id, c.norm_text, c.kind, c.source_id, c.word_count "
        f"FROM chunks_fts f JOIN chunks c ON f.rowid = c.rowid "
        f"WHERE f.norm_text MATCH ? AND {status_filter}{kind_filter} "
        f"LIMIT 200"
    )
    params = [fts_query]
    if kind:
        params.extend(kinds)

    fts_results = conn.execute(sql, params).fetchall()

    if not fts_results:
        return []

    reranked = False
    if _rerank is not None:
        try:
            rr_results, rr_status = _rerank(
                conn, query_text, top_n=200, db_path=db_path
            )
            if rr_status == "reranked" and rr_results:
                fts_chunk_ids = {r[0] for r in fts_results}
                ranked_ids = [r[0] for r in rr_results if r[0] in fts_chunk_ids]
                missing = [cid for cid in fts_chunk_ids
                           if cid not in set(ranked_ids)]
                ordered_ids = ranked_ids + missing
                reranked = True
            else:
                ordered_ids = [r[0] for r in fts_results]
        except Exception:
            ordered_ids = [r[0] for r in fts_results]
    else:
        ordered_ids = [r[0] for r in fts_results]

    chunk_map = {}
    for r in fts_results:
        chunk_map[r[0]] = {
            "chunk_id": r[0],
            "text": r[1],
            "kind": r[2],
            "source_id": r[3],
            "word_count": r[4],
        }

    results = []
    for cid in ordered_ids:
        if cid not in chunk_map:
            continue
        chunk = chunk_map[cid]

        source = conn.execute(
            "SELECT source_id, canonical_uri, license_verdict, liveness, "
            "fetched_utc, upstream_mtime, kind, content_sha256 "
            "FROM sources WHERE source_id = ?",
            (chunk["source_id"],),
        ).fetchone()

        if not source:
            continue

        source_dict = {
            "source_id": source[0],
            "uri": source[1],
            "license_verdict": source[2],
            "liveness": source[3],
            "fetched_utc": source[4],
            "upstream_mtime": source[5],
            "kind": source[6],
            "content_sha256": source[7],
        }

        staleness = _staleness(source_dict, chunk, db_path=db_path)

        if max_age_days is not None and staleness["age_days"] is not None:
            if staleness["age_days"] > max_age_days:
                continue

        citations = _get_citations(conn, cid)
        contradictions = _get_contradictions(conn, cid)
        artifacts = _get_artifacts(conn, cid)

        if implemented_only:
            if not any(a["implemented"] for a in artifacts):
                continue

        trust = _trust_for_source(source_dict)

        record = {
            "chunk_id": cid,
            "text": chunk["text"][:500],
            "kind": chunk["kind"],
            "source": {
                "uri": source_dict["uri"],
                "license_verdict": source_dict["license_verdict"],
                "liveness": source_dict["liveness"],
                "fetched_utc": source_dict["fetched_utc"],
                "upstream_mtime": source_dict["upstream_mtime"],
            },
            "citations": citations,
            "contradicted_by": contradictions,
            "artifacts": artifacts,
            "staleness": staleness,
            "trust": trust,
            "reranked": reranked,
        }
        results.append(record)

        if len(results) >= top_k:
            break

    return results


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        def add_source(sid, uri, verdict="vendor", liveness="live",
                       mtime=None, kind="local_md"):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes) "
                "VALUES (?, ?, ?, 'Test', 'MIT', ?, 'test', ?, ?, ?, ?, 100)",
                (sid, uri, kind, verdict, now, liveness,
                 mtime or now, _sha256(sid)),
            )

        def add_chunk(cid, sid, text, kind="prose", status="accepted"):
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', ?, ?, ?, ?, ?, 0, ?, ?)",
                (cid, sid, kind, text, text, len(text.split()),
                 _sha256(text), status, now),
            )

        add_source("s1", "/test/s1", mtime="2026-08-01T00:00:00Z")
        add_source("s2", "/test/s2", verdict="index_only",
                   mtime="2024-01-01T00:00:00Z")
        add_source("s3", "/test/s3", mtime="2026-08-15T00:00:00Z")

        add_chunk("c1", "s1", "numpy provides fast matrix multiplication")
        add_chunk("c2", "s2", "polars handles dataframe operations efficiently")
        add_chunk("c3", "s3", "duckdb enables fast SQL analytics on files")
        conn.commit()

        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES (?, ?, ?, ?, ?, 1)",
            ("cit1", "c1", "https://numpy.org", "ref", "docs"),
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES (?, ?, ?, 'contradicts', 'test', 0.8, ?)",
            ("e1", "c1", "c3", now),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES (?, ?, 'library', 'numpy', 'matrix ops', 1, '/usr/lib/numpy')",
            ("a1", "c1"),
        )
        conn.commit()

        # Test 1: basic query returns results
        results = query(conn, "numpy matrix", db_path=db_path)
        if not results:
            failures.append("query returned no results for 'numpy matrix'")

        # Test 2: result has full record shape
        if results:
            r = results[0]
            required_keys = {
                "chunk_id", "text", "kind", "source", "citations",
                "contradicted_by", "artifacts", "staleness", "trust",
            }
            missing = required_keys - set(r.keys())
            if missing:
                failures.append(f"result missing keys: {missing}")

        # Test 3: citations attached
        if results:
            numpy_results = [r for r in results if r["chunk_id"] == "c1"]
            if numpy_results and not numpy_results[0]["citations"]:
                failures.append("c1 should have citations")

        # Test 4: contradictions attached
        if results:
            numpy_results = [r for r in results if r["chunk_id"] == "c1"]
            if numpy_results and not numpy_results[0]["contradicted_by"]:
                failures.append("c1 should have contradictions")

        # Test 5: artifacts attached
        if results:
            numpy_results = [r for r in results if r["chunk_id"] == "c1"]
            if numpy_results and not numpy_results[0]["artifacts"]:
                failures.append("c1 should have artifacts")

        # Test 6: trust is trusted for vendor source
        if results:
            numpy_results = [r for r in results if r["chunk_id"] == "c1"]
            if numpy_results and numpy_results[0]["trust"] != "trusted":
                failures.append(
                    f"vendor source trust is {numpy_results[0]['trust']}, "
                    f"expected trusted"
                )

        # Test 7: trust is untrusted for index_only source
        polars_results = query(conn, "polars dataframe", db_path=db_path)
        if polars_results:
            pr = polars_results[0]
            if pr["trust"] != "untrusted":
                failures.append(
                    f"index_only trust is {pr['trust']}, expected untrusted"
                )

        # Test 8: staleness verdict computed
        if results:
            r = results[0]
            if "verdict" not in r["staleness"]:
                failures.append("staleness missing verdict field")

        # Test 9: empty query returns empty list
        empty = query(conn, "", db_path=db_path)
        if empty:
            failures.append("empty query should return empty list")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print("PASS retrieve selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_query = sub.add_parser("query", help="Query the corpus")
    p_query.add_argument("text", nargs="+")
    p_query.add_argument("--kind", default=None)
    p_query.add_argument("--implemented", action="store_true")
    p_query.add_argument("--max-age", type=int, default=None, dest="max_age")
    p_query.add_argument("--k", type=int, default=10)
    p_query.add_argument("--db", default=None)
    p_query.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "query":
        db = getattr(args, "db", None)
        conn = connect(db)
        query_text = " ".join(args.text)
        results = query(
            conn, query_text,
            kind=args.kind,
            implemented_only=args.implemented,
            max_age_days=args.max_age,
            top_k=args.k,
            db_path=db,
        )
        if args.as_json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  no results")
            else:
                for i, r in enumerate(results, 1):
                    trust_tag = f"[{r['trust']}]"
                    stale_tag = r["staleness"]["verdict"]
                    print(f"  {i:2d}. {trust_tag} {r['kind']:8s} "
                          f"{r['chunk_id'][:16]} ({stale_tag})")
                    print(f"      {r['text'][:100]}")
                    if r["citations"]:
                        print(f"      citations: {len(r['citations'])}")
                    if r["contradicted_by"]:
                        print(f"      contradictions: "
                              f"{len(r['contradicted_by'])}")
                    if r["artifacts"]:
                        names = [a["name"] for a in r["artifacts"]]
                        print(f"      artifacts: {', '.join(names)}")
                    print()
            print(f"  {len(results)} result(s)"
                  f"{', reranked' if results and results[0].get('reranked') else ''}")
        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
