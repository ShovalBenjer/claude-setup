#!/usr/bin/env python3
"""Paper rule: stage 7 of the ingestion pipeline.

Enforces the operator's 2026-only paper rule: for kind='paper' sources,
admit only those with published_utc in 2026, require a publisher value
from the paper record, and quarantine chunks from failing sources.

Usage:
    python tools/corpus/paper_rule.py scan [--db PATH] [--json]
    python tools/corpus/paper_rule.py apply [--db PATH] [--dry-run]
    python tools/corpus/paper_rule.py stats [--db PATH] [--json]
    python tools/corpus/paper_rule.py selftest
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

REQUIRED_YEAR = 2026

YEAR_RE = re.compile(r"^(\d{4})")


def _extract_year(published_utc: str | None) -> int | None:
    if not published_utc:
        return None
    m = YEAR_RE.match(published_utc.strip())
    if m:
        return int(m.group(1))
    return None


def _check_source(source: dict) -> dict:
    source_id = source["source_id"]
    kind = source["kind"]
    published_utc = source["published_utc"]
    publisher = source["publisher"]

    if kind != "paper":
        return {"source_id": source_id, "status": "skip", "reason": "not a paper"}

    year = _extract_year(published_utc)
    violations = []

    if year is None:
        violations.append("missing_date")
    elif year != REQUIRED_YEAR:
        violations.append(f"wrong_year:{year}")

    if not publisher or not publisher.strip():
        violations.append("missing_publisher")

    if violations:
        return {
            "source_id": source_id,
            "status": "fail",
            "reason": ", ".join(violations),
            "year": year,
            "publisher": publisher,
        }

    return {
        "source_id": source_id,
        "status": "pass",
        "reason": None,
        "year": year,
        "publisher": publisher,
    }


def scan_papers(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT source_id, kind, published_utc, publisher "
        "FROM sources WHERE kind = 'paper'"
    ).fetchall()

    results = []
    for row in rows:
        source = {
            "source_id": row[0],
            "kind": row[1],
            "published_utc": row[2],
            "publisher": row[3],
        }
        check = _check_source(source)
        results.append(check)

    return results


def apply_rule(conn, dry_run: bool = True) -> dict:
    scan = scan_papers(conn)
    quarantined = []
    passed = []

    for result in scan:
        if result["status"] == "fail":
            if not dry_run:
                reason = f"paper_rule: {result['reason']}"
                conn.execute(
                    "UPDATE chunks SET status = 'quarantined', "
                    "status_reason = ? WHERE source_id = ? "
                    "AND status = 'accepted'",
                    (reason, result["source_id"]),
                )
            quarantined.append(result)
        elif result["status"] == "pass":
            passed.append(result)

    if not dry_run:
        conn.commit()

    return {
        "total_papers": len(scan),
        "passed": len(passed),
        "quarantined": quarantined,
        "dry_run": dry_run,
    }


def paper_stats(conn) -> dict:
    total_papers = conn.execute(
        "SELECT COUNT(*) FROM sources WHERE kind = 'paper'"
    ).fetchone()[0]

    by_year = conn.execute(
        "SELECT SUBSTR(published_utc, 1, 4) AS yr, COUNT(*) "
        "FROM sources WHERE kind = 'paper' "
        "GROUP BY yr ORDER BY yr DESC"
    ).fetchall()

    missing_publisher = conn.execute(
        "SELECT COUNT(*) FROM sources "
        "WHERE kind = 'paper' AND (publisher IS NULL OR publisher = '')"
    ).fetchone()[0]

    missing_date = conn.execute(
        "SELECT COUNT(*) FROM sources "
        "WHERE kind = 'paper' AND published_utc IS NULL"
    ).fetchone()[0]

    quarantined_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE s.kind = 'paper' AND c.status = 'quarantined' "
        "AND c.status_reason LIKE 'paper_rule%'"
    ).fetchone()[0]

    return {
        "total_papers": total_papers,
        "by_year": dict(by_year),
        "missing_publisher": missing_publisher,
        "missing_date": missing_date,
        "quarantined_chunks": quarantined_chunks,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    # Check 1: non-paper source is skipped
    result = _check_source({
        "source_id": "s1", "kind": "local_md",
        "published_utc": "2025-01-01", "publisher": "Test",
    })
    assert result["status"] == "skip"
    checks += 1

    # Check 2: 2026 paper with publisher passes
    result = _check_source({
        "source_id": "s2", "kind": "paper",
        "published_utc": "2026-03-15T00:00:00Z", "publisher": "ACM",
    })
    assert result["status"] == "pass"
    checks += 1

    # Check 3: 2025 paper fails with wrong_year
    result = _check_source({
        "source_id": "s3", "kind": "paper",
        "published_utc": "2025-06-01", "publisher": "IEEE",
    })
    assert result["status"] == "fail"
    assert "wrong_year:2025" in result["reason"]
    checks += 1

    # Check 4: missing date fails
    result = _check_source({
        "source_id": "s4", "kind": "paper",
        "published_utc": None, "publisher": "Springer",
    })
    assert result["status"] == "fail"
    assert "missing_date" in result["reason"]
    checks += 1

    # Check 5: missing publisher fails
    result = _check_source({
        "source_id": "s5", "kind": "paper",
        "published_utc": "2026-01-01", "publisher": None,
    })
    assert result["status"] == "fail"
    assert "missing_publisher" in result["reason"]
    checks += 1

    # Check 6: empty publisher fails
    result = _check_source({
        "source_id": "s6", "kind": "paper",
        "published_utc": "2026-07-01", "publisher": "  ",
    })
    assert result["status"] == "fail"
    assert "missing_publisher" in result["reason"]
    checks += 1

    # Check 7: both missing date and publisher
    result = _check_source({
        "source_id": "s7", "kind": "paper",
        "published_utc": None, "publisher": "",
    })
    assert result["status"] == "fail"
    assert "missing_date" in result["reason"]
    assert "missing_publisher" in result["reason"]
    checks += 1

    # Check 8: year extraction from ISO timestamp
    assert _extract_year("2026-03-15T10:30:00Z") == 2026
    checks += 1

    # Check 9: year extraction from date-only
    assert _extract_year("2025-12-31") == 2025
    checks += 1

    # Check 10: year extraction from None
    assert _extract_year(None) is None
    checks += 1

    # Check 11: year extraction from empty string
    assert _extract_year("") is None
    checks += 1

    # Check 12: scan with database
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("p1", "https://arxiv.org/abs/2026.1234", "paper", "Good Paper",
             "CC-BY-4.0", "vendor", "LICENSE", "ACM", "2026-03-15",
             now, None, None, "live", _sha256("p1"), 5000, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("p2", "https://arxiv.org/abs/2025.5678", "paper", "Old Paper",
             "CC-BY-4.0", "vendor", "LICENSE", "IEEE", "2025-11-01",
             now, None, None, "live", _sha256("p2"), 3000, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("p3", "https://arxiv.org/abs/2026.9999", "paper", "No Publisher",
             "CC-BY-4.0", "vendor", "LICENSE", None, "2026-01-01",
             now, None, None, "live", _sha256("p3"), 2000, None),
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("m1", "file:///local.md", "local_md", "Not Paper",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("m1"), 100, None),
        )
        conn.commit()

        scan = scan_papers(conn)
        assert len(scan) == 3
        statuses = {r["source_id"]: r["status"] for r in scan}
        assert statuses["p1"] == "pass"
        assert statuses["p2"] == "fail"
        assert statuses["p3"] == "fail"
        checks += 1

        # Check 13: apply in dry-run mode
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "p1", 0, "Abstract", "prose", None,
             "Good paper content about ML in 2026",
             "raw", 7, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "p2", 0, "Abstract", "prose", None,
             "Old paper content from 2025",
             "raw", 5, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "p3", 0, "Methods", "prose", None,
             "Paper without publisher attribution",
             "raw", 4, _sha256("c3"), 0, 0, "accepted", None, now),
        )
        conn.commit()

        result = apply_rule(conn, dry_run=True)
        assert result["dry_run"] is True
        assert len(result["quarantined"]) == 2

        status_c2 = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert status_c2 == "accepted"
        checks += 1

        # Check 14: apply for real quarantines chunks
        result = apply_rule(conn, dry_run=False)
        assert result["passed"] == 1
        assert len(result["quarantined"]) == 2

        status_c1 = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        assert status_c1 == "accepted"

        status_c2 = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert status_c2 == "quarantined"

        status_c3 = conn.execute(
            "SELECT status FROM chunks WHERE chunk_id = 'c3'"
        ).fetchone()[0]
        assert status_c3 == "quarantined"
        checks += 1

        # Check 15: status_reason is set
        reason_c2 = conn.execute(
            "SELECT status_reason FROM chunks WHERE chunk_id = 'c2'"
        ).fetchone()[0]
        assert reason_c2.startswith("paper_rule:")
        assert "wrong_year:2025" in reason_c2
        checks += 1

        # Check 16: re-apply is idempotent
        result2 = apply_rule(conn, dry_run=False)
        assert len(result2["quarantined"]) == 2
        count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE status = 'quarantined'"
        ).fetchone()[0]
        assert count == 2
        checks += 1

        # Check 17: stats work
        stats = paper_stats(conn)
        assert stats["total_papers"] == 3
        assert stats["quarantined_chunks"] == 2
        assert stats["missing_publisher"] == 1
        checks += 1

        # Check 18: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert scan_papers(empty_conn) == []
        r = apply_rule(empty_conn, dry_run=False)
        assert r["total_papers"] == 0
        es = paper_stats(empty_conn)
        assert es["total_papers"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS paper_rule selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Paper rule (stage 7)")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan paper sources for rule compliance")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Apply paper rule, quarantine failing chunks")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    p_stats = sub.add_parser("stats", help="Paper source statistics")
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

    if args.cmd == "scan":
        conn = connect(args.db)
        results = scan_papers(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            passing = [r for r in results if r["status"] == "pass"]
            failing = [r for r in results if r["status"] == "fail"]
            print(f"  {len(results)} paper source(s): "
                  f"{len(passing)} pass, {len(failing)} fail")
            for r in failing[:30]:
                print(f"    {r['source_id'][:16]:16s}  {r['reason']}")
        conn.close()

    elif args.cmd == "apply":
        conn = connect(args.db)
        result = apply_rule(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}: {result['total_papers']} paper(s), "
              f"{result['passed']} passed, "
              f"{len(result['quarantined'])} quarantined")
        for q in result["quarantined"][:20]:
            print(f"    {q['source_id'][:16]:16s}  {q['reason']}")
        conn.close()

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = paper_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total papers:         {stats['total_papers']}")
            print(f"  Missing publisher:    {stats['missing_publisher']}")
            print(f"  Missing date:         {stats['missing_date']}")
            print(f"  Quarantined chunks:   {stats['quarantined_chunks']}")
            print("  By year:")
            for yr, cnt in stats["by_year"].items():
                marker = " *" if yr and yr != str(REQUIRED_YEAR) else ""
                print(f"    {yr or 'NULL':6s}: {cnt:5d}{marker}")
        conn.close()


if __name__ == "__main__":
    main()
