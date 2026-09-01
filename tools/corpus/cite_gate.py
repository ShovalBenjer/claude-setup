#!/usr/bin/env python3
"""Corpus citation gate: enforce that claim chunks carry citations.

Stage 4 of the ingestion pipeline.  A chunk with kind='claim' must have
at least one citation -- either a [S#] reference tag, a bare URL, or an
existing citations table row.  Uncited claims are quarantined with
status_reason='uncited'.

Usage:
    python tools/corpus/cite_gate.py scan [--db PATH] [--json]
    python tools/corpus/cite_gate.py apply [--db PATH] [--dry-run]
    python tools/corpus/cite_gate.py backlog [--db PATH] [--json]
    python tools/corpus/cite_gate.py stats [--db PATH] [--json]
    python tools/corpus/cite_gate.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

REF_TAG = re.compile(r"\[S\d+\]")
BARE_URL = re.compile(
    r"https?://[^\s\]\)\"'<>,;]+",
    re.IGNORECASE,
)
DOI_PATTERN = re.compile(r"\b10\.\d{4,}/\S+")


def _extract_citations(text: str) -> list[dict]:
    found = [
        {"type": "ref_tag", "tag": m.group(), "value": m.group()}
        for m in REF_TAG.finditer(text)
    ]

    for m in DOI_PATTERN.finditer(text):
        uri = "https://doi.org/" + m.group()
        found.append({"type": "doi", "tag": None, "value": uri})

    for m in BARE_URL.finditer(text):
        url = m.group().rstrip(".")
        if any(c["value"] == url for c in found):
            continue
        found.append({"type": "url", "tag": None, "value": url})

    return found


def scan_citations(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.norm_text, c.kind, "
        "       c.status, c.status_reason "
        "FROM chunks c "
        "WHERE c.kind = 'claim' AND c.status = 'accepted'"
    ).fetchall()

    results = []
    for row in rows:
        chunk_id, source_id, text, kind, status, reason = row

        existing = conn.execute(
            "SELECT COUNT(*) FROM citations WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()[0]

        extracted = _extract_citations(text)

        cited = existing > 0 or len(extracted) > 0
        results.append({
            "chunk_id": chunk_id,
            "source_id": source_id,
            "status": status,
            "existing_citations": existing,
            "extracted_citations": extracted,
            "cited": cited,
        })

    results.sort(key=lambda r: r["cited"])
    return results


def apply_gate(conn, dry_run: bool = True) -> dict:
    scan = scan_citations(conn)
    quarantined = []
    citations_created = []

    for item in scan:
        for ext in item["extracted_citations"]:
            cit_id = "cit" + _sha256(
                item["chunk_id"] + ext["value"]
            )[:13]

            existing = conn.execute(
                "SELECT citation_id FROM citations WHERE citation_id = ?",
                (cit_id,),
            ).fetchone()

            if existing:
                continue

            action = {
                "citation_id": cit_id,
                "chunk_id": item["chunk_id"],
                "target_uri": ext["value"],
                "tag": ext["tag"],
                "type": ext["type"],
            }

            if not dry_run:
                conn.execute(
                    "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
                    (cit_id, item["chunk_id"], ext["value"],
                     None, ext["tag"], None, 0, None),
                )

            citations_created.append(action)

        if not item["cited"]:
            action = {
                "chunk_id": item["chunk_id"],
                "source_id": item["source_id"],
                "reason": "uncited",
            }

            if not dry_run:
                conn.execute(
                    "UPDATE chunks SET status = 'quarantined', "
                    "  status_reason = 'uncited' "
                    "WHERE chunk_id = ?",
                    (item["chunk_id"],),
                )

            quarantined.append(action)

    if not dry_run:
        conn.commit()

    return {
        "citations_created": citations_created,
        "quarantined": quarantined,
        "total_claims_scanned": len(scan),
    }


def backlog(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.norm_text, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE c.kind = 'claim' AND c.status = 'quarantined' "
        "  AND c.status_reason = 'uncited'"
    ).fetchall()

    return [
        {
            "chunk_id": r[0],
            "source_id": r[1],
            "text_preview": r[2][:120],
            "source_title": r[3],
        }
        for r in rows
    ]


def cite_stats(conn) -> dict:
    total_claims = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE kind = 'claim'"
    ).fetchone()[0]

    accepted_claims = conn.execute(
        "SELECT COUNT(*) FROM chunks "
        "WHERE kind = 'claim' AND status = 'accepted'"
    ).fetchone()[0]

    quarantined_uncited = conn.execute(
        "SELECT COUNT(*) FROM chunks "
        "WHERE kind = 'claim' AND status = 'quarantined' "
        "  AND status_reason = 'uncited'"
    ).fetchone()[0]

    total_citations = conn.execute(
        "SELECT COUNT(*) FROM citations"
    ).fetchone()[0]

    cited_chunks = conn.execute(
        "SELECT COUNT(DISTINCT chunk_id) FROM citations"
    ).fetchone()[0]

    return {
        "total_claims": total_claims,
        "accepted_claims": accepted_claims,
        "quarantined_uncited": quarantined_uncited,
        "total_citations": total_citations,
        "cited_chunks": cited_chunks,
        "citation_rate": (
            round(cited_chunks / accepted_claims, 3)
            if accepted_claims else 0
        ),
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Research Notes",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Claims", "claim", None,
             "The system uses FTS5 for full-text search [S1]. "
             "This is faster than LIKE queries by 10x.",
             "raw", 18, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Claims", "claim", None,
             "Redis outperforms memcached for most workloads. "
             "No source is provided for this claim.",
             "raw", 14, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Links", "claim", None,
             "According to https://example.com/benchmark results "
             "show a 30% improvement in throughput.",
             "raw", 12, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src1", 3, "Code", "code", None,
             "import sqlite3\ndb = sqlite3.connect('test.db')",
             "raw", 6, _sha256("c4"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 4, "DOI", "claim", None,
             "The study by Smith et al. found significant results "
             "10.1234/test.2026.001 in controlled conditions.",
             "raw", 14, _sha256("c5"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "src1", 5, "Pre-cited", "claim", None,
             "This chunk already has a citation row.",
             "raw", 8, _sha256("c6"), 0, 0, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO citations VALUES (?,?,?,?,?,?,?,?)",
            ("cit_existing", "c6", "https://example.com/ref",
             None, "[S1]", None, 1, now),
        )
        conn.commit()

        # Check 1: _extract_citations finds [S#] tags
        cits = _extract_citations("FTS5 is fast [S1] and reliable [S2].")
        tags = [c["tag"] for c in cits if c["type"] == "ref_tag"]
        assert "[S1]" in tags and "[S2]" in tags
        checks += 1

        # Check 2: _extract_citations finds bare URLs
        cits = _extract_citations("See https://example.com/paper for details.")
        urls = [c["value"] for c in cits if c["type"] == "url"]
        assert any("example.com" in u for u in urls)
        checks += 1

        # Check 3: _extract_citations finds DOIs
        cits = _extract_citations("Published as 10.1234/test.2026.001")
        dois = [c for c in cits if c["type"] == "doi"]
        assert len(dois) > 0
        checks += 1

        # Check 4: _extract_citations returns empty for plain text
        assert _extract_citations("No citations here at all.") == []
        checks += 1

        # Check 5: scan finds cited and uncited claims
        scan = scan_citations(conn)
        assert len(scan) >= 4
        checks += 1

        # Check 6: c1 (has [S1]) is cited
        c1_item = next(s for s in scan if s["chunk_id"] == "c1")
        assert c1_item["cited"] is True
        checks += 1

        # Check 7: c2 (no citation) is not cited
        c2_item = next(s for s in scan if s["chunk_id"] == "c2")
        assert c2_item["cited"] is False
        checks += 1

        # Check 8: c3 (bare URL) is cited
        c3_item = next(s for s in scan if s["chunk_id"] == "c3")
        assert c3_item["cited"] is True
        checks += 1

        # Check 9: code chunk excluded from scan (not kind='claim')
        scan_ids = [s["chunk_id"] for s in scan]
        assert "c4" not in scan_ids
        checks += 1

        # Check 10: c6 (pre-existing citation) is cited
        c6_item = next(s for s in scan if s["chunk_id"] == "c6")
        assert c6_item["cited"] is True
        assert c6_item["existing_citations"] == 1
        checks += 1

        # Check 11: dry run does not modify database
        before_q = conn.execute(
            "SELECT COUNT(*) FROM chunks "
            "WHERE status = 'quarantined'"
        ).fetchone()[0]
        apply_gate(conn, dry_run=True)
        after_q = conn.execute(
            "SELECT COUNT(*) FROM chunks "
            "WHERE status = 'quarantined'"
        ).fetchone()[0]
        assert before_q == after_q
        checks += 1

        # Check 12: apply quarantines uncited claims
        result = apply_gate(conn, dry_run=False)
        assert len(result["quarantined"]) > 0
        assert any(q["chunk_id"] == "c2" for q in result["quarantined"])
        checks += 1

        # Check 13: apply creates citation rows
        assert len(result["citations_created"]) > 0
        checks += 1

        # Check 14: quarantined chunk has correct status
        row = conn.execute(
            "SELECT status, status_reason FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()
        assert row[0] == "quarantined"
        assert row[1] == "uncited"
        checks += 1

        # Check 15: backlog shows quarantined uncited claims
        bl = backlog(conn)
        assert len(bl) > 0
        assert any(b["chunk_id"] == "c2" for b in bl)
        checks += 1

        # Check 16: stats returns expected structure
        stats = cite_stats(conn)
        assert "total_claims" in stats
        assert "quarantined_uncited" in stats
        assert stats["quarantined_uncited"] > 0
        checks += 1

        # Check 17: re-apply is idempotent
        result2 = apply_gate(conn, dry_run=False)
        assert len(result2["quarantined"]) == 0
        checks += 1

        # Check 18: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert scan_citations(empty_conn) == []
        assert backlog(empty_conn) == []
        empty_stats = cite_stats(empty_conn)
        assert empty_stats["total_claims"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS cite_gate selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus citation gate")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan claims for citations")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Quarantine uncited claims")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    p_backlog = sub.add_parser("backlog", help="Show uncited claim backlog")
    p_backlog.add_argument("--db", default=str(DEFAULT_DB))
    p_backlog.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Citation statistics")
    p_stats.add_argument("--db", default=str(DEFAULT_DB))
    p_stats.add_argument("--json", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)

    if args.cmd == "scan":
        results = scan_citations(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            cited = sum(1 for r in results if r["cited"])
            uncited = sum(1 for r in results if not r["cited"])
            print(f"  {len(results)} claim chunk(s): {cited} cited, "
                  f"{uncited} uncited")
            for r in results[:50]:
                mark = "OK" if r["cited"] else "UNCITED"
                print(f"    {r['chunk_id'][:12]}  {mark}")

    elif args.cmd == "apply":
        result = apply_gate(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}:")
        print(f"    Citations created:  {len(result['citations_created'])}")
        print(f"    Claims quarantined: {len(result['quarantined'])}")

    elif args.cmd == "backlog":
        bl = backlog(conn)
        if args.json:
            print(json.dumps(bl, indent=2))
        else:
            if not bl:
                print("  No uncited claims in backlog.")
            else:
                print(f"  {len(bl)} uncited claim(s):")
                for b in bl[:50]:
                    print(f"    {b['chunk_id'][:12]}  {b['source_title']}")
                    print(f"      {b['text_preview']}")

    elif args.cmd == "stats":
        stats = cite_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total claims:        {stats['total_claims']}")
            print(f"  Accepted claims:     {stats['accepted_claims']}")
            print(f"  Quarantined uncited: {stats['quarantined_uncited']}")
            print(f"  Total citations:     {stats['total_citations']}")
            print(f"  Cited chunks:        {stats['cited_chunks']}")
            print(f"  Citation rate:       {stats['citation_rate']:.1%}")

    conn.close()


if __name__ == "__main__":
    main()
