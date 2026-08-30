#!/usr/bin/env python3
"""Corpus chunk promotion: review and promote quarantined chunks.

Quarantined chunks are uncited prose that was held back during ingestion.
This tool lists them for review and promotes (or rejects) them individually
or in bulk by source.

Usage:
    python tools/corpus/promote.py list [--db PATH] [--source SOURCE_ID]
        [--limit N] [--json]
    python tools/corpus/promote.py promote CHUNK_ID [CHUNK_ID ...]
        [--db PATH] [--reason TEXT]
    python tools/corpus/promote.py reject CHUNK_ID [CHUNK_ID ...]
        [--db PATH] [--reason TEXT]
    python tools/corpus/promote.py promote-source SOURCE_ID [--db PATH]
        [--reason TEXT]
    python tools/corpus/promote.py stats [--db PATH] [--json]
    python tools/corpus/promote.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def list_quarantined(conn, source_id: str | None = None,
                     limit: int = 50) -> list[dict]:
    params: list = []
    where = "c.status = 'quarantined'"
    if source_id:
        where += " AND c.source_id = ?"
        params.append(source_id)
    params.append(limit)

    rows = conn.execute(
        f"SELECT c.chunk_id, c.source_id, c.kind, c.word_count, "
        f"       c.status_reason, c.norm_text, s.title, s.canonical_uri "
        f"FROM chunks c "
        f"JOIN sources s ON c.source_id = s.source_id "
        f"WHERE {where} "
        f"ORDER BY s.title, c.ordinal "
        f"LIMIT ?",
        params,
    ).fetchall()

    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "kind": r[2],
            "word_count": r[3],
            "status_reason": r[4],
            "snippet": (r[5] or "")[:200],
            "source_title": r[6],
            "source_uri": r[7],
        }
        for r in rows
    ]


def promote_chunks(conn, chunk_ids: list[str],
                   reason: str = "operator_promoted") -> dict:
    promoted = 0
    skipped = 0
    for cid in chunk_ids:
        row = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = ?", (cid,)
        ).fetchone()
        if not row:
            skipped += 1
            continue
        if row[0] != "quarantined":
            skipped += 1
            continue
        conn.execute(
            "UPDATE chunks SET status = 'accepted', status_reason = ? "
            "WHERE chunk_id = ?",
            (reason, cid),
        )
        promoted += 1
    conn.commit()
    return {"promoted": promoted, "skipped": skipped}


def reject_chunks(conn, chunk_ids: list[str],
                  reason: str = "operator_rejected") -> dict:
    rejected = 0
    skipped = 0
    for cid in chunk_ids:
        row = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = ?", (cid,)
        ).fetchone()
        if not row:
            skipped += 1
            continue
        if row[0] != "quarantined":
            skipped += 1
            continue
        conn.execute(
            "UPDATE chunks SET status = 'rejected', status_reason = ? "
            "WHERE chunk_id = ?",
            (reason, cid),
        )
        rejected += 1
    conn.commit()
    return {"rejected": rejected, "skipped": skipped}


def promote_source(conn, source_id: str,
                   reason: str = "source_promoted") -> dict:
    rows = conn.execute(
        "SELECT chunk_id FROM chunks "
        "WHERE source_id = ? AND status = 'quarantined'",
        (source_id,),
    ).fetchall()
    ids = [r[0] for r in rows]
    if not ids:
        return {"promoted": 0, "skipped": 0, "source_id": source_id}
    result = promote_chunks(conn, ids, reason)
    result["source_id"] = source_id
    return result


def stats(conn) -> dict:
    total = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE status = 'quarantined'"
    ).fetchone()[0]

    by_source = conn.execute(
        "SELECT s.title, c.source_id, COUNT(*) as cnt "
        "FROM chunks c JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.status = 'quarantined' "
        "GROUP BY c.source_id ORDER BY cnt DESC"
    ).fetchall()

    by_reason = conn.execute(
        "SELECT status_reason, COUNT(*) "
        "FROM chunks WHERE status = 'quarantined' "
        "GROUP BY status_reason"
    ).fetchall()

    by_kind = conn.execute(
        "SELECT kind, COUNT(*) "
        "FROM chunks WHERE status = 'quarantined' "
        "GROUP BY kind"
    ).fetchall()

    return {
        "total_quarantined": total,
        "by_source": [
            {"title": r[0], "source_id": r[1], "count": r[2]}
            for r in by_source
        ],
        "by_reason": {r[0] or "unknown": r[1] for r in by_reason},
        "by_kind": {r[0]: r[1] for r in by_kind},
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " upstream_mtime, content_sha256, bytes, supersedes) "
            "VALUES ('s1', '/test/doc1.md', 'local_md', 'Design Doc', 'MIT', "
            " 'vendor', 'test', ?, 'live', ?, ?, 200, NULL)",
            (now, now, _sha256("s1")),
        )
        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " upstream_mtime, content_sha256, bytes, supersedes) "
            "VALUES ('s2', '/test/doc2.md', 'local_md', 'Notes', 'MIT', "
            " 'vendor', 'test', ?, 'live', ?, ?, 150, NULL)",
            (now, now, _sha256("s2")),
        )

        for cid, sid, text, status, ordinal in [
            ("c1", "s1", "quarantined prose chunk one", "quarantined", 0),
            ("c2", "s1", "quarantined prose chunk two", "quarantined", 1),
            ("c3", "s1", "accepted chunk already good", "accepted", 2),
            ("c4", "s2", "another quarantined chunk here", "quarantined", 0),
            ("c5", "s2", "second quarantined in doc two", "quarantined", 1),
        ]:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, status_reason, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', 'prose', ?, ?, ?, ?, 0, ?, 'uncited', ?)",
                (cid, sid, ordinal, text, text, len(text.split()),
                 _sha256(text), status, now),
            )
        conn.commit()

        # 1: list returns quarantined chunks
        q = list_quarantined(conn)
        checks += 1
        if len(q) != 4:
            failures.append(f"list returned {len(q)}, expected 4")

        # 2: list with source filter
        q = list_quarantined(conn, source_id="s1")
        checks += 1
        if len(q) != 2:
            failures.append(f"list s1 returned {len(q)}, expected 2")

        # 3: list respects limit
        q = list_quarantined(conn, limit=2)
        checks += 1
        if len(q) != 2:
            failures.append(f"limit=2 returned {len(q)}")

        # 4: result shape has required fields
        q = list_quarantined(conn, limit=1)
        checks += 1
        if q:
            required = {"chunk_id", "source_id", "kind", "word_count",
                        "snippet", "source_title"}
            missing = required - set(q[0].keys())
            if missing:
                failures.append(f"result missing fields: {missing}")

        # 5: promote changes status to accepted
        r = promote_chunks(conn, ["c1"])
        checks += 1
        if r["promoted"] != 1:
            failures.append(f"promoted = {r['promoted']}, expected 1")
        row = conn.execute(
            "SELECT status, status_reason FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()
        if row[0] != "accepted":
            failures.append(f"c1 status = {row[0]}, expected accepted")

        # 6: promote skips non-quarantined
        r = promote_chunks(conn, ["c3"])
        checks += 1
        if r["skipped"] != 1:
            failures.append(f"skip accepted = {r['skipped']}, expected 1")

        # 7: promote skips unknown chunk_id
        r = promote_chunks(conn, ["nonexistent"])
        checks += 1
        if r["skipped"] != 1:
            failures.append(f"skip unknown = {r['skipped']}, expected 1")

        # 8: reject changes status to rejected
        r = reject_chunks(conn, ["c2"])
        checks += 1
        if r["rejected"] != 1:
            failures.append(f"rejected = {r['rejected']}, expected 1")
        row = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()
        if row[0] != "rejected":
            failures.append(f"c2 status = {row[0]}, expected rejected")

        # 9: promote-source promotes all quarantined in a source
        r = promote_source(conn, "s2")
        checks += 1
        if r["promoted"] != 2:
            failures.append(f"source promoted = {r['promoted']}, expected 2")

        # 10: after source promote, no quarantined remain for s2
        q = list_quarantined(conn, source_id="s2")
        checks += 1
        if len(q) != 0:
            failures.append(f"s2 still has {len(q)} quarantined")

        # 11: stats returns correct total
        # reset some chunks for stats testing
        conn.execute(
            "UPDATE chunks SET status = 'quarantined', "
            "status_reason = 'uncited' WHERE chunk_id IN ('c4', 'c5')"
        )
        conn.commit()
        s = stats(conn)
        checks += 1
        if s["total_quarantined"] != 2:
            failures.append(
                f"stats total = {s['total_quarantined']}, expected 2"
            )

        # 12: stats by_source has entries
        checks += 1
        if not s["by_source"]:
            failures.append("stats by_source is empty")

        # 13: stats by_reason has entries
        checks += 1
        if not s["by_reason"]:
            failures.append("stats by_reason is empty")

        # 14: stats by_kind has entries
        checks += 1
        if not s["by_kind"]:
            failures.append("stats by_kind is empty")

        # 15: custom reason is stored
        conn.execute(
            "UPDATE chunks SET status = 'quarantined' WHERE chunk_id = 'c1'"
        )
        conn.commit()
        promote_chunks(conn, ["c1"], reason="reviewed_good")
        row = conn.execute(
            "SELECT status_reason FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()
        checks += 1
        if row[0] != "reviewed_good":
            failures.append(f"custom reason = {row[0]!r}")

        # 16: JSON serializable
        checks += 1
        try:
            json.dumps(s)
            json.dumps(list_quarantined(conn))
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS promote selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List quarantined chunks")
    p_list.add_argument("--db", default=None)
    p_list.add_argument("--source", default=None)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--json", action="store_true", dest="as_json")

    p_prom = sub.add_parser("promote", help="Promote chunks to accepted")
    p_prom.add_argument("chunk_ids", nargs="+")
    p_prom.add_argument("--db", default=None)
    p_prom.add_argument("--reason", default="operator_promoted")

    p_rej = sub.add_parser("reject", help="Reject quarantined chunks")
    p_rej.add_argument("chunk_ids", nargs="+")
    p_rej.add_argument("--db", default=None)
    p_rej.add_argument("--reason", default="operator_rejected")

    p_ps = sub.add_parser("promote-source",
                          help="Promote all quarantined in a source")
    p_ps.add_argument("source_id")
    p_ps.add_argument("--db", default=None)
    p_ps.add_argument("--reason", default="source_promoted")

    p_st = sub.add_parser("stats", help="Quarantine statistics")
    p_st.add_argument("--db", default=None)
    p_st.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    conn = connect(args.db)

    if args.command == "list":
        results = list_quarantined(conn, args.source, args.limit)
        if args.as_json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  no quarantined chunks")
            else:
                for r in results:
                    print(f"  {r['chunk_id'][:16]} [{r['kind']}] "
                          f"({r['word_count']} words)")
                    print(f"    source: {r['source_title']}")
                    print(f"    reason: {r['status_reason']}")
                    print(f"    {r['snippet'][:100]}")
                    print()
                print(f"  {len(results)} quarantined chunk(s)")
        conn.close()
        return 0

    if args.command == "promote":
        r = promote_chunks(conn, args.chunk_ids, args.reason)
        print(f"  promoted: {r['promoted']}, skipped: {r['skipped']}")
        conn.close()
        return 0

    if args.command == "reject":
        r = reject_chunks(conn, args.chunk_ids, args.reason)
        print(f"  rejected: {r['rejected']}, skipped: {r['skipped']}")
        conn.close()
        return 0

    if args.command == "promote-source":
        r = promote_source(conn, args.source_id, args.reason)
        print(f"  source {r['source_id']}: "
              f"promoted {r['promoted']}, skipped {r['skipped']}")
        conn.close()
        return 0

    if args.command == "stats":
        s = stats(conn)
        if args.as_json:
            print(json.dumps(s, indent=2))
        else:
            print(f"  Total quarantined: {s['total_quarantined']}")
            print()
            if s["by_reason"]:
                print("  By reason:")
                for reason, count in s["by_reason"].items():
                    print(f"    {reason}: {count}")
                print()
            if s["by_kind"]:
                print("  By kind:")
                for kind, count in s["by_kind"].items():
                    print(f"    {kind}: {count}")
                print()
            if s["by_source"]:
                print("  Top sources:")
                for entry in s["by_source"][:15]:
                    print(f"    {entry['count']:4d}  {entry['title']}")
        conn.close()
        return 0

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
