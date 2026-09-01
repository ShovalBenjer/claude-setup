#!/usr/bin/env python3
"""Corpus structural validation: referential integrity and data consistency.

Checks that all foreign key references are valid, no orphaned records exist,
text fields are non-empty, and invariants hold across tables. Complements
health.py (which checks defect counts) with structural soundness checks.

Usage:
    python tools/corpus/validate.py check [--db PATH] [--json]
    python tools/corpus/validate.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402


def validate(conn) -> dict:
    issues: list[dict] = []

    # 1: chunks referencing nonexistent sources
    orphan_chunks = conn.execute(
        "SELECT c.chunk_id, c.source_id FROM chunks c "
        "LEFT JOIN sources s ON c.source_id = s.source_id "
        "WHERE s.source_id IS NULL"
    ).fetchall()
    if orphan_chunks:
        issues.append({
            "check": "orphan_chunks",
            "severity": "error",
            "count": len(orphan_chunks),
            "details": [{"chunk_id": r[0], "source_id": r[1]}
                        for r in orphan_chunks[:10]],
        })

    # 2: citations referencing nonexistent chunks
    orphan_cites = conn.execute(
        "SELECT ci.citation_id, ci.chunk_id FROM citations ci "
        "LEFT JOIN chunks c ON ci.chunk_id = c.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchall()
    if orphan_cites:
        issues.append({
            "check": "orphan_citations",
            "severity": "error",
            "count": len(orphan_cites),
            "details": [{"citation_id": r[0], "chunk_id": r[1]}
                        for r in orphan_cites[:10]],
        })

    # 3: claim_edges referencing nonexistent chunks
    orphan_edges_src = conn.execute(
        "SELECT ce.edge_id, ce.source_chunk FROM claim_edges ce "
        "LEFT JOIN chunks c ON ce.source_chunk = c.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchall()
    orphan_edges_tgt = conn.execute(
        "SELECT ce.edge_id, ce.target_chunk FROM claim_edges ce "
        "LEFT JOIN chunks c ON ce.target_chunk = c.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchall()
    orphan_edges = orphan_edges_src + orphan_edges_tgt
    if orphan_edges:
        issues.append({
            "check": "orphan_claim_edges",
            "severity": "error",
            "count": len(orphan_edges),
            "details": [{"edge_id": r[0], "ref": r[1]}
                        for r in orphan_edges[:10]],
        })

    # 4: artifacts referencing nonexistent chunks
    orphan_arts = conn.execute(
        "SELECT a.artifact_id, a.chunk_id FROM artifacts a "
        "LEFT JOIN chunks c ON a.chunk_id = c.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchall()
    if orphan_arts:
        issues.append({
            "check": "orphan_artifacts",
            "severity": "error",
            "count": len(orphan_arts),
            "details": [{"artifact_id": r[0], "chunk_id": r[1]}
                        for r in orphan_arts[:10]],
        })

    # 5: chunks with empty norm_text
    empty_text = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE norm_text IS NULL OR norm_text = ''"
    ).fetchone()[0]
    if empty_text:
        issues.append({
            "check": "empty_chunk_text",
            "severity": "warning",
            "count": empty_text,
        })

    # 6: sources with empty canonical_uri
    empty_uri = conn.execute(
        "SELECT COUNT(*) FROM sources "
        "WHERE canonical_uri IS NULL OR canonical_uri = ''"
    ).fetchone()[0]
    if empty_uri:
        issues.append({
            "check": "empty_source_uri",
            "severity": "error",
            "count": empty_uri,
        })

    # 7: duplicate chunk_id (should be impossible with PK but check anyway)
    dup_chunks = conn.execute(
        "SELECT chunk_id, COUNT(*) as cnt FROM chunks "
        "GROUP BY chunk_id HAVING cnt > 1"
    ).fetchall()
    if dup_chunks:
        issues.append({
            "check": "duplicate_chunk_ids",
            "severity": "error",
            "count": len(dup_chunks),
        })

    # 8: chunks with negative word_count
    neg_wc = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE word_count < 0"
    ).fetchone()[0]
    if neg_wc:
        issues.append({
            "check": "negative_word_count",
            "severity": "warning",
            "count": neg_wc,
        })

    # 9: sources with zero or negative bytes
    bad_bytes = conn.execute(
        "SELECT COUNT(*) FROM sources WHERE bytes <= 0"
    ).fetchone()[0]
    if bad_bytes:
        issues.append({
            "check": "invalid_source_bytes",
            "severity": "warning",
            "count": bad_bytes,
        })

    # 10: supersedes referencing nonexistent source
    bad_supersedes = conn.execute(
        "SELECT s1.source_id, s1.supersedes FROM sources s1 "
        "LEFT JOIN sources s2 ON s1.supersedes = s2.source_id "
        "WHERE s1.supersedes IS NOT NULL AND s2.source_id IS NULL"
    ).fetchall()
    if bad_supersedes:
        issues.append({
            "check": "orphan_supersedes",
            "severity": "error",
            "count": len(bad_supersedes),
            "details": [{"source_id": r[0], "supersedes": r[1]}
                        for r in bad_supersedes[:10]],
        })

    # counts
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    total_citations = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
    total_edges = conn.execute("SELECT COUNT(*) FROM claim_edges").fetchone()[0]
    total_artifacts = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    verdict = "VALID" if not errors else "INVALID"

    return {
        "verdict": verdict,
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": issues,
        "counts": {
            "sources": total_sources,
            "chunks": total_chunks,
            "citations": total_citations,
            "claim_edges": total_edges,
            "artifacts": total_artifacts,
        },
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        def add_source(sid, uri):
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Test', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (sid, uri, now, now, _sha256(sid)),
            )

        def add_chunk(cid, sid, text, ordinal=0):
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', 'prose', ?, ?, ?, ?, 0, "
                " 'accepted', ?)",
                (cid, sid, ordinal, text, text, len(text.split()),
                 _sha256(text), now),
            )

        # valid corpus
        add_source("s1", "/test/doc1.md")
        add_source("s2", "/test/doc2.md")
        add_chunk("c1", "s1", "valid chunk text here")
        add_chunk("c2", "s2", "another valid chunk")
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES ('cit1', 'c1', 'http://x', "
            "'ref', 'p1', 0)"
        )
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES ('e1', 'c1', 'c2', 'contradicts', 'test', 0.8, ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES ('a1', 'c1', 'library', 'lib', 'code', 0, NULL)"
        )
        conn.commit()

        # 1: valid corpus passes
        r = validate(conn)
        checks += 1
        if r["verdict"] != "VALID":
            failures.append(f"valid corpus verdict = {r['verdict']}")

        # 2: no errors on valid corpus
        checks += 1
        if r["errors"] != 0:
            failures.append(f"valid corpus errors = {r['errors']}")

        # 3: counts are correct
        checks += 1
        if r["counts"]["sources"] != 2:
            failures.append(f"sources = {r['counts']['sources']}")
        if r["counts"]["chunks"] != 2:
            failures.append(f"chunks = {r['counts']['chunks']}")

        # 4: orphan chunk detection
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES ('c_orphan', 's_gone', 0, 'Test', 'prose', "
            " 'orphan text', 'orphan text', 2, ?, 0, 'accepted', ?)",
            (_sha256("orphan"), now),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        r = validate(conn)
        checks += 1
        orphan_issue = [i for i in r["issues"] if i["check"] == "orphan_chunks"]
        if not orphan_issue:
            failures.append("orphan_chunks not detected")

        # 5: verdict is INVALID with orphan chunks
        checks += 1
        if r["verdict"] != "INVALID":
            failures.append(f"orphan corpus verdict = {r['verdict']}")

        # clean up orphan
        conn.execute("DELETE FROM chunks WHERE chunk_id = 'c_orphan'")
        conn.commit()

        # 6: orphan citation detection
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO citations (citation_id, chunk_id, target_uri, "
            "tag, locator, verified) VALUES ('cit_orphan', 'c_gone', "
            "'http://x', 'ref', 'p1', 0)"
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        r = validate(conn)
        checks += 1
        orphan_cit = [i for i in r["issues"] if i["check"] == "orphan_citations"]
        if not orphan_cit:
            failures.append("orphan_citations not detected")
        conn.execute("DELETE FROM citations WHERE citation_id = 'cit_orphan'")
        conn.commit()

        # 7: orphan claim_edge detection
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO claim_edges (edge_id, source_chunk, target_chunk, "
            "edge_type, basis, confidence, detected_utc) "
            "VALUES ('e_orphan', 'c_gone', 'c1', 'contradicts', 'test', "
            "0.5, ?)",
            (now,),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        r = validate(conn)
        checks += 1
        orphan_edge = [i for i in r["issues"]
                       if i["check"] == "orphan_claim_edges"]
        if not orphan_edge:
            failures.append("orphan_claim_edges not detected")
        conn.execute("DELETE FROM claim_edges WHERE edge_id = 'e_orphan'")
        conn.commit()

        # 8: orphan artifact detection
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO artifacts (artifact_id, chunk_id, artifact_type, "
            "name, snippet, implemented, evidence_path) "
            "VALUES ('a_orphan', 'c_gone', 'library', 'x', 'y', 0, NULL)"
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        r = validate(conn)
        checks += 1
        orphan_art = [i for i in r["issues"]
                      if i["check"] == "orphan_artifacts"]
        if not orphan_art:
            failures.append("orphan_artifacts not detected")
        conn.execute("DELETE FROM artifacts WHERE artifact_id = 'a_orphan'")
        conn.commit()

        # 9: empty text detection
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES ('c_empty', 's1', 99, 'Test', 'prose', '', '', 0, "
            " ?, 0, 'accepted', ?)",
            (_sha256(""), now),
        )
        conn.commit()
        r = validate(conn)
        checks += 1
        empty_issue = [i for i in r["issues"]
                       if i["check"] == "empty_chunk_text"]
        if not empty_issue:
            failures.append("empty_chunk_text not detected")
        conn.execute("DELETE FROM chunks WHERE chunk_id = 'c_empty'")
        conn.commit()

        # 10: orphan supersedes detection
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "UPDATE sources SET supersedes = 's_nonexistent' "
            "WHERE source_id = 's1'"
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        r = validate(conn)
        checks += 1
        orphan_sup = [i for i in r["issues"]
                      if i["check"] == "orphan_supersedes"]
        if not orphan_sup:
            failures.append("orphan_supersedes not detected")
        conn.execute(
            "UPDATE sources SET supersedes = NULL WHERE source_id = 's1'"
        )
        conn.commit()

        # 11: clean corpus after fixes
        r = validate(conn)
        checks += 1
        if r["verdict"] != "VALID":
            failures.append(
                f"cleaned corpus verdict = {r['verdict']}, "
                f"issues = {r['issues']}"
            )

        # 12: JSON serializable
        checks += 1
        try:
            json.dumps(r)
        except (TypeError, ValueError) as e:
            failures.append(f"not JSON-serializable: {e}")

        # 13: issue has severity field
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES ('c_neg', 's1', 98, 'Test', 'prose', 'text', 'text', "
            " -1, ?, 0, 'accepted', ?)",
            (_sha256("neg"), now),
        )
        conn.commit()
        r = validate(conn)
        checks += 1
        neg_issue = [i for i in r["issues"]
                     if i["check"] == "negative_word_count"]
        if not neg_issue:
            failures.append("negative_word_count not detected")
        elif neg_issue[0]["severity"] != "warning":
            failures.append(
                f"negative_word_count severity = {neg_issue[0]['severity']}"
            )
        conn.execute("DELETE FROM chunks WHERE chunk_id = 'c_neg'")
        conn.commit()

        # 14: warnings don't make verdict INVALID
        checks += 1
        if neg_issue and r["verdict"] == "INVALID" and r["errors"] == 0:
            failures.append("warnings alone should not make INVALID")

        conn.close()

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS validate selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_c = sub.add_parser("check", help="Validate corpus integrity")
    p_c.add_argument("--db", default=None)
    p_c.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    dp = Path(args.db) if args.db else DEFAULT_DB
    conn = connect(dp)
    r = validate(conn)
    conn.close()

    if args.as_json:
        print(json.dumps(r, indent=2))
    else:
        print(f"  Verdict: {r['verdict']}")
        print(f"  Errors: {r['errors']}, Warnings: {r['warnings']}")
        print()
        c = r["counts"]
        print(f"  Sources: {c['sources']}, Chunks: {c['chunks']}, "
              f"Citations: {c['citations']}")
        print(f"  Edges: {c['claim_edges']}, Artifacts: {c['artifacts']}")
        print()
        if r["issues"]:
            print("  Issues:")
            for issue in r["issues"]:
                sev = issue["severity"].upper()
                print(f"    [{sev}] {issue['check']}: {issue['count']}")
        else:
            print("  No issues found")

    return 1 if r["verdict"] == "INVALID" else 0


if __name__ == "__main__":
    sys.exit(main())
