#!/usr/bin/env python3
"""Corpus chunk reclassification: detect and fix misclassified chunk kinds.

Scans chunks for kind mismatches based on content heuristics (code patterns,
table markers, URL density, config syntax) and reports or applies corrections.
Useful for improving corpus quality after bulk ingestion.

Usage:
    python tools/corpus/reclassify.py scan [--db PATH] [--status STATUS]
        [--source SOURCE_ID] [--json]
    python tools/corpus/reclassify.py apply [--db PATH] [--dry-run]
    python tools/corpus/reclassify.py stats [--db PATH] [--json]
    python tools/corpus/reclassify.py selftest
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

CODE_PATTERNS = [
    re.compile(r"^(import |from \S+ import |def |class |function |const |let |var )", re.MULTILINE),
    re.compile(r"^(if \(|for \(|while \(|return |try:|except |catch \()", re.MULTILINE),
    re.compile(r"[{}\[\]];?\s*$", re.MULTILINE),
    re.compile(r"^\s*(#include|using |package |require\(|module )", re.MULTILINE),
]

TABLE_PATTERNS = [
    re.compile(r"^\|.*\|.*\|", re.MULTILINE),
    re.compile(r"^\|[\s\-:]+\|", re.MULTILINE),
]

CONFIG_PATTERNS = [
    re.compile(r"^\[[\w.-]+\]", re.MULTILINE),
    re.compile(r"^\w[\w.-]*\s*[=:]\s*\S", re.MULTILINE),
    re.compile(r"^(apiVersion:|kind:|metadata:|spec:)", re.MULTILINE),
]

LINK_PATTERN = re.compile(r"https?://\S+")


def _detect_kind(text: str) -> str:
    lines = text.strip().split("\n")
    if not lines:
        return "prose"

    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return "prose"

    code_hits = sum(
        1 for p in CODE_PATTERNS
        for _ in p.finditer(text)
    )
    code_line_ratio = code_hits / max(len(non_empty), 1)

    if code_line_ratio > 0.3:
        return "code"

    table_hits = sum(1 for p in TABLE_PATTERNS for _ in p.finditer(text))
    if table_hits >= 2:
        return "table"

    link_hits = len(LINK_PATTERN.findall(text))
    link_ratio = link_hits / max(len(non_empty), 1)
    if link_ratio > 0.5 and len(non_empty) >= 2:
        return "link"

    config_hits = sum(1 for p in CONFIG_PATTERNS for _ in p.finditer(text))
    config_line_ratio = config_hits / max(len(non_empty), 1)
    if config_line_ratio > 0.4:
        return "config"

    assertion_words = ["must", "should", "always", "never", "requires",
                       "ensures", "guarantees", "asserts", "proves"]
    text_lower = text.lower()
    claim_hits = sum(1 for w in assertion_words if w in text_lower)
    if claim_hits >= 2:
        return "claim"

    return "prose"


def scan_mismatches(conn, status: str | None = None,
                    source_id: str | None = None) -> list[dict]:
    where_parts: list[str] = []
    params: list = []

    if status:
        where_parts.append("c.status = ?")
        params.append(status)
    if source_id:
        where_parts.append("c.source_id = ?")
        params.append(source_id)

    where = " AND ".join(where_parts) if where_parts else "1=1"

    rows = conn.execute(
        "SELECT c.chunk_id, c.source_id, c.kind, c.norm_text, "
        "       c.word_count, c.status, s.title "
        "FROM chunks c "
        "JOIN sources s ON c.source_id = s.source_id "
        f"WHERE {where}",
        params,
    ).fetchall()

    mismatches = []
    for row in rows:
        current_kind = row[2]
        detected = _detect_kind(row[3])

        if detected != current_kind:
            mismatches.append({
                "chunk_id": row[0],
                "source_id": row[1],
                "current_kind": current_kind,
                "detected_kind": detected,
                "word_count": row[4],
                "status": row[5],
                "source_title": row[6],
            })

    return mismatches


def apply_reclassifications(conn, dry_run: bool = True) -> list[dict]:
    mismatches = scan_mismatches(conn)
    applied = []

    for m in mismatches:
        if not dry_run:
            conn.execute(
                "UPDATE chunks SET kind = ? WHERE chunk_id = ?",
                (m["detected_kind"], m["chunk_id"]),
            )
        applied.append({
            "chunk_id": m["chunk_id"],
            "from": m["current_kind"],
            "to": m["detected_kind"],
            "applied": not dry_run,
        })

    if not dry_run:
        conn.commit()

    return applied


def kind_stats(conn) -> dict:
    current = conn.execute(
        "SELECT kind, COUNT(*) FROM chunks GROUP BY kind"
    ).fetchall()

    all_chunks = conn.execute(
        "SELECT chunk_id, norm_text FROM chunks"
    ).fetchall()

    detected_counts: dict[str, int] = {}
    for row in all_chunks:
        d = _detect_kind(row[1])
        detected_counts[d] = detected_counts.get(d, 0) + 1

    mismatches = scan_mismatches(conn)
    mismatch_matrix: dict[str, dict[str, int]] = {}
    for m in mismatches:
        curr = m["current_kind"]
        det = m["detected_kind"]
        mismatch_matrix.setdefault(curr, {})
        mismatch_matrix[curr][det] = mismatch_matrix[curr].get(det, 0) + 1

    return {
        "current_distribution": {r[0]: r[1] for r in current},
        "detected_distribution": detected_counts,
        "total_mismatches": len(mismatches),
        "mismatch_rate": round(len(mismatches) / len(all_chunks), 3) if all_chunks else 0,
        "mismatch_matrix": mismatch_matrix,
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
            ("src1", "file:///a.md", "local_md", "Test Source",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "Intro", "prose", None,
             "import numpy as np\nimport pandas as pd\n\n"
             "def process_data(df):\n    return df.groupby('key').sum()\n\n"
             "class DataProcessor:\n    def __init__(self):\n        pass\n",
             "raw", 20, _sha256("c1"), 0, 0, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "Data", "prose", None,
             "| Name | Value | Status |\n"
             "|------|-------|--------|\n"
             "| foo  | 42    | active |\n"
             "| bar  | 99    | done   |\n",
             "raw", 15, _sha256("c2"), 0, 0, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "Rules", "prose", None,
             "This is plain prose text describing a concept. "
             "It contains no code, no tables, and no special formatting. "
             "The text discusses ideas in natural language.",
             "raw", 25, _sha256("c3"), 0, 0, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c4", "src1", 3, "Claims", "code", None,
             "The system must always validate input before processing. "
             "It should never accept unverified data. "
             "This ensures data integrity and guarantees correctness. "
             "The validator requires all fields to be present.",
             "raw", 30, _sha256("c4"), 0, 0, "quarantined", None, now),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c5", "src1", 4, "Links", "prose", None,
             "https://example.com/resource1\n"
             "https://example.com/resource2\n"
             "https://example.com/resource3\n"
             "https://example.com/resource4\n",
             "raw", 8, _sha256("c5"), 0, 0, "accepted", None, now),
        )

        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c6", "src1", 5, "Correct", "claim", None,
             "The implementation must ensure that all inputs are validated. "
             "It should never allow unverified data through the pipeline. "
             "This guarantees that the system always produces correct results.",
             "raw", 28, _sha256("c6"), 0, 0, "accepted", None, now),
        )
        conn.commit()

        # Check 1: _detect_kind identifies code
        assert _detect_kind("import os\ndef foo():\n    return 1\nclass Bar:\n    pass") == "code"
        checks += 1

        # Check 2: _detect_kind identifies tables
        assert _detect_kind("| A | B |\n|---|---|\n| 1 | 2 |") == "table"
        checks += 1

        # Check 3: _detect_kind identifies prose
        assert _detect_kind("This is a simple paragraph about nothing in particular.") == "prose"
        checks += 1

        # Check 4: _detect_kind identifies claims
        assert _detect_kind("The system must always validate. It should never fail. "
                            "This ensures correctness.") == "claim"
        checks += 1

        # Check 5: _detect_kind identifies links
        assert _detect_kind("https://a.com/1\nhttps://b.com/2\nhttps://c.com/3") == "link"
        checks += 1

        # Check 6: scan_mismatches finds code labelled as prose
        mismatches = scan_mismatches(conn)
        c1_mm = [m for m in mismatches if m["chunk_id"] == "c1"]
        assert len(c1_mm) == 1
        assert c1_mm[0]["detected_kind"] == "code"
        checks += 1

        # Check 7: scan_mismatches finds table labelled as prose
        c2_mm = [m for m in mismatches if m["chunk_id"] == "c2"]
        assert len(c2_mm) == 1
        assert c2_mm[0]["detected_kind"] == "table"
        checks += 1

        # Check 8: correctly classified prose not in mismatches
        c3_mm = [m for m in mismatches if m["chunk_id"] == "c3"]
        assert len(c3_mm) == 0
        checks += 1

        # Check 9: claim labelled as code detected
        c4_mm = [m for m in mismatches if m["chunk_id"] == "c4"]
        assert len(c4_mm) == 1
        assert c4_mm[0]["detected_kind"] == "claim"
        checks += 1

        # Check 10: correctly classified claim not in mismatches
        c6_mm = [m for m in mismatches if m["chunk_id"] == "c6"]
        assert len(c6_mm) == 0
        checks += 1

        # Check 11: status filter works
        quarantined_mm = scan_mismatches(conn, status="quarantined")
        assert all(m["status"] == "quarantined" for m in quarantined_mm)
        checks += 1

        # Check 12: source filter works
        src1_mm = scan_mismatches(conn, source_id="src1")
        assert all(m["source_id"] == "src1" for m in src1_mm)
        checks += 1

        # Check 13: dry run does not modify DB
        before = conn.execute(
            "SELECT kind FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        apply_reclassifications(conn, dry_run=True)
        after = conn.execute(
            "SELECT kind FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        assert before == after == "prose"
        checks += 1

        # Check 14: kind_stats returns expected structure
        stats = kind_stats(conn)
        assert "current_distribution" in stats
        assert "detected_distribution" in stats
        assert stats["total_mismatches"] > 0
        checks += 1

        # Check 15: JSON serialization works
        j = json.dumps(mismatches, indent=2)
        parsed = json.loads(j)
        assert len(parsed) > 0
        checks += 1

        # Check 16: empty corpus returns empty results
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert scan_mismatches(empty_conn) == []
        empty_stats = kind_stats(empty_conn)
        assert empty_stats["total_mismatches"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS reclassify selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus chunk reclassification")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="Scan for kind mismatches")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--status")
    p_scan.add_argument("--source", dest="source_id")
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Apply reclassifications")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    p_stats = sub.add_parser("stats", help="Kind distribution and mismatch stats")
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
        results = scan_mismatches(conn, status=args.status,
                                  source_id=args.source_id)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  No mismatches found.")
            else:
                print(f"  {len(results)} mismatch(es):")
                for r in results:
                    print(f"    {r['chunk_id'][:12]}  "
                          f"{r['current_kind']:6s} -> {r['detected_kind']:6s}  "
                          f"w={r['word_count']:4d}  {r['source_title'][:40]}")

    elif args.cmd == "apply":
        results = apply_reclassifications(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}: {len(results)} reclassification(s)")
        for r in results:
            print(f"    {r['chunk_id'][:12]}  {r['from']:6s} -> {r['to']:6s}")

    elif args.cmd == "stats":
        stats = kind_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("Current distribution:")
            for k, v in sorted(stats["current_distribution"].items()):
                print(f"  {k:10s}: {v:5d}")
            print("Detected distribution:")
            for k, v in sorted(stats["detected_distribution"].items()):
                print(f"  {k:10s}: {v:5d}")
            print(f"Total mismatches: {stats['total_mismatches']} "
                  f"({stats['mismatch_rate']:.1%})")
            if stats["mismatch_matrix"]:
                print("Mismatch matrix (current -> detected):")
                for curr, dets in sorted(stats["mismatch_matrix"].items()):
                    for det, count in sorted(dets.items()):
                        print(f"  {curr:10s} -> {det:10s}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
