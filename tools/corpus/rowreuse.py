#!/usr/bin/env python3
"""Row-reuse write-back for the research corpus (spec step 9, section 5.1).

A retrieval that answers a question from stored corpus rows writes the
synthesized answer back as a derived source+chunk with citation edges to
every row it consumed. The cache both serves and grows.

Guard: kind='derived' rows are capped at one hop of provenance depth.
A derived row may never be the sole citation for another derived row.

Usage:
    python tools/corpus/rowreuse.py write --query TEXT --answer TEXT --sources ID,ID,...
    python tools/corpus/rowreuse.py check [--db PATH]
    python tools/corpus/rowreuse.py selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import (  # noqa: E402
    DEFAULT_DB,
    SCHEMA_SQL,
    _sha256,
    _simhash,
    _to_signed64,
    connect,
    init_schema,
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provenance_depth(conn, chunk_id, cache=None):
    """How many hops of derived provenance lead to this chunk."""
    if cache is None:
        cache = {}
    if chunk_id in cache:
        return cache[chunk_id]

    row = conn.execute(
        "SELECT s.kind FROM chunks c JOIN sources s USING(source_id) "
        "WHERE c.chunk_id = ?", (chunk_id,)
    ).fetchone()

    if not row or row[0] != "derived":
        cache[chunk_id] = 0
        return 0

    citations = conn.execute(
        "SELECT target_source_id FROM citations WHERE chunk_id = ?",
        (chunk_id,)
    ).fetchall()

    if not citations:
        cache[chunk_id] = 1
        return 1

    cited_chunks = []
    for cit in citations:
        if cit[0]:
            rows = conn.execute(
                "SELECT chunk_id FROM chunks WHERE source_id = ?",
                (cit[0],)
            ).fetchall()
            cited_chunks.extend(r[0] for r in rows)

    if not cited_chunks:
        cache[chunk_id] = 1
        return 1

    max_depth = max(_provenance_depth(conn, cid, cache) for cid in cited_chunks)
    depth = 1 + max_depth
    cache[chunk_id] = depth
    return depth


def validate_sources(conn, source_chunk_ids):
    """Check that a derived row built from these sources respects the one-hop cap.

    Returns (ok, reason). A derived row may not have ALL of its citations
    pointing to other derived rows (sole-citation rule).
    """
    if not source_chunk_ids:
        return False, "no source chunks provided"

    non_derived = 0
    for cid in source_chunk_ids:
        row = conn.execute(
            "SELECT s.kind FROM chunks c JOIN sources s USING(source_id) "
            "WHERE c.chunk_id = ?", (cid,)
        ).fetchone()
        if not row:
            return False, f"chunk {cid} not found"
        if row[0] != "derived":
            non_derived += 1

    if non_derived == 0:
        return False, "all source chunks are derived (violates one-hop provenance cap)"

    return True, "ok"


def write_derived(conn, query_text, answer_text, source_chunk_ids):
    """Write a derived source+chunk+citations from a synthesis.

    Returns the new chunk_id, or raises ValueError on constraint violation.
    """
    ok, reason = validate_sources(conn, source_chunk_ids)
    if not ok:
        raise ValueError(reason)

    now = _now()
    content_hash = _sha256(answer_text)

    existing = conn.execute(
        "SELECT c.chunk_id FROM chunks c JOIN sources s USING(source_id) "
        "WHERE c.norm_sha256 = ? AND s.kind = 'derived'",
        (content_hash,)
    ).fetchone()
    if existing:
        return existing[0]

    source_id = "s_derived_" + _sha256(query_text + content_hash)[:12]
    chunk_id = "c_derived_" + content_hash[:12]

    uri = f"derived://{_sha256(query_text)[:16]}"

    conn.execute(
        "INSERT OR IGNORE INTO sources "
        "(source_id, canonical_uri, kind, title, license_spdx, "
        " license_verdict, license_evidence, fetched_utc, liveness, "
        " content_sha256, bytes) "
        "VALUES (?, ?, 'derived', ?, 'proprietary', 'vendor', "
        " 'synthesized', ?, 'live', ?, ?)",
        (source_id, uri, f"synthesis: {query_text[:100]}",
         now, content_hash, len(answer_text.encode())),
    )

    simhash = _simhash(answer_text)
    conn.execute(
        "INSERT OR IGNORE INTO chunks "
        "(chunk_id, source_id, ordinal, heading_path, kind, "
        " norm_text, raw_text, word_count, norm_sha256, simhash, "
        " status, ingested_utc) "
        "VALUES (?, ?, 0, ?, 'claim', ?, ?, ?, ?, ?, 'accepted', ?)",
        (chunk_id, source_id, f"Q: {query_text[:80]}",
         answer_text, answer_text, len(answer_text.split()),
         content_hash, _to_signed64(simhash), now),
    )

    for src_cid in source_chunk_ids:
        src_row = conn.execute(
            "SELECT source_id FROM chunks WHERE chunk_id = ?", (src_cid,)
        ).fetchone()
        if not src_row:
            continue
        src_source_id = src_row[0]

        src_uri = conn.execute(
            "SELECT canonical_uri FROM sources WHERE source_id = ?",
            (src_source_id,)
        ).fetchone()
        target_uri = src_uri[0] if src_uri else f"chunk://{src_cid}"

        citation_id = "cit_" + _sha256(chunk_id + src_cid)[:14]
        conn.execute(
            "INSERT OR IGNORE INTO citations "
            "(citation_id, chunk_id, target_uri, target_source_id, "
            " tag, locator, verified) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (citation_id, chunk_id, target_uri, src_source_id,
             "derived", f"Q: {query_text[:60]}"),
        )

    conn.commit()
    return chunk_id


def check_provenance(conn):
    """Check all derived chunks for provenance violations."""
    derived = conn.execute(
        "SELECT c.chunk_id FROM chunks c JOIN sources s USING(source_id) "
        "WHERE s.kind = 'derived'"
    ).fetchall()

    violations = []
    for row in derived:
        cid = row[0]
        citations = conn.execute(
            "SELECT target_source_id FROM citations WHERE chunk_id = ?",
            (cid,)
        ).fetchall()

        if not citations:
            violations.append(f"{cid}: derived chunk with no citations")
            continue

        all_derived = True
        for cit in citations:
            if cit[0]:
                src = conn.execute(
                    "SELECT kind FROM sources WHERE source_id = ?",
                    (cit[0],)
                ).fetchone()
                if src and src[0] != "derived":
                    all_derived = False
                    break

        if all_derived:
            violations.append(f"{cid}: all citations are derived (one-hop violation)")

    return violations


def selftest():
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = _now()

        def add_chunk(cid, sid, text, kind="local_md"):
            conn.execute(
                "INSERT OR IGNORE INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " content_sha256, bytes) "
                "VALUES (?, ?, ?, 'Test', 'proprietary', "
                " 'vendor', 'local', ?, 'live', ?, 100)",
                (sid, f"/test/{sid}", kind, now, _sha256(text)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, 0, 'Test', 'prose', ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, text, text, len(text.split()), _sha256(text), now),
            )
            conn.commit()

        add_chunk("c_base1", "s_base1", "numpy 2.2.6 is installed on this machine")
        add_chunk("c_base2", "s_base2", "duckdb 1.1.1 provides fast analytics")
        add_chunk("c_base3", "s_base3", "polars 1.9.0 handles dataframes")

        # Test 1: write_derived creates a derived chunk
        new_cid = write_derived(
            conn,
            "what analytics tools are available",
            "numpy 2.2.6, duckdb 1.1.1, and polars 1.9.0 are installed",
            ["c_base1", "c_base2", "c_base3"],
        )
        if not new_cid:
            failures.append("write_derived returned None")

        # Test 2: derived source has kind='derived'
        src = conn.execute(
            "SELECT s.kind FROM chunks c JOIN sources s USING(source_id) "
            "WHERE c.chunk_id = ?", (new_cid,)
        ).fetchone()
        if not src or src[0] != "derived":
            failures.append("derived source kind is not 'derived'")

        # Test 3: citations are created
        cit_count = conn.execute(
            "SELECT count(*) FROM citations WHERE chunk_id = ?", (new_cid,)
        ).fetchone()[0]
        if cit_count != 3:
            failures.append(f"expected 3 citations, got {cit_count}")

        # Test 4: idempotent re-write returns same chunk_id
        same_cid = write_derived(
            conn,
            "what analytics tools are available",
            "numpy 2.2.6, duckdb 1.1.1, and polars 1.9.0 are installed",
            ["c_base1", "c_base2", "c_base3"],
        )
        if same_cid != new_cid:
            failures.append(f"re-write returned different cid: {same_cid} vs {new_cid}")

        # Test 5: one-hop cap rejects all-derived sources
        add_chunk("c_derived_only", "s_derived_only",
                  "another derived synthesis", kind="derived")
        conn.execute(
            "INSERT OR IGNORE INTO citations "
            "(citation_id, chunk_id, target_uri, target_source_id, "
            " tag, locator, verified) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            ("cit_test_derived", "c_derived_only",
             "/test/s_base1", "s_base1",
             "derived", "test"),
        )
        conn.commit()
        try:
            write_derived(
                conn,
                "re-synthesize",
                "this should fail because all sources are derived",
                [new_cid, "c_derived_only"],
            )
            failures.append("all-derived sources should have been rejected")
        except ValueError:
            pass

        # Test 6: mixed sources (some derived, some primary) are allowed
        mixed_cid = write_derived(
            conn,
            "mixed provenance query",
            "synthesis from both primary and derived sources",
            [new_cid, "c_base1"],
        )
        if not mixed_cid:
            failures.append("mixed sources (derived + primary) rejected")

        # Test 7: check_provenance finds no violations in valid data
        violations = check_provenance(conn)
        if violations:
            failures.append(f"check_provenance found violations: {violations}")

        # Test 8: validate_sources rejects empty list
        ok, _ = validate_sources(conn, [])
        if ok:
            failures.append("empty source list was accepted")

        # Test 9: validate_sources rejects nonexistent chunk
        ok, reason = validate_sources(conn, ["nonexistent_chunk"])
        if ok:
            failures.append("nonexistent chunk was accepted")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS rowreuse selftest (9 checks)")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_write = sub.add_parser("write", help="Write a derived row")
    p_write.add_argument("--query", required=True)
    p_write.add_argument("--answer", required=True)
    p_write.add_argument("--sources", required=True,
                         help="Comma-separated chunk IDs")
    p_write.add_argument("--db", default=None)

    p_check = sub.add_parser("check", help="Check provenance constraints")
    p_check.add_argument("--db", default=None)

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    db = getattr(args, "db", None)
    conn = connect(db)
    init_schema(conn)

    if args.command == "write":
        source_ids = [s.strip() for s in args.sources.split(",") if s.strip()]
        try:
            chunk_id = write_derived(conn, args.query, args.answer, source_ids)
            print(f"  derived chunk: {chunk_id}")
            print(f"  citations: {len(source_ids)}")
        except ValueError as e:
            print(f"  rejected: {e}")
            conn.close()
            return 1
        conn.close()
        return 0

    if args.command == "check":
        violations = check_provenance(conn)
        if violations:
            for v in violations:
                print(f"  VIOLATION: {v}")
            print(f"\n{len(violations)} provenance violation(s)")
            conn.close()
            return 1
        derived_count = conn.execute(
            "SELECT count(*) FROM chunks c JOIN sources s USING(source_id) "
            "WHERE s.kind = 'derived'"
        ).fetchone()[0]
        print(f"  derived chunks: {derived_count}")
        print(f"  provenance: clean (0 violations)")
        conn.close()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
