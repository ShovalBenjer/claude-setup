#!/usr/bin/env python3
"""Corpus text normaliser: stage 0 of the ingestion pipeline.

NFC unicode normalisation, mojibake repair (cp1255 round-trip damage),
dash variant mapping, and trailing whitespace stripping.  Runs
in-process (never shells out per file, per section 2.1).

Usage:
    python tools/corpus/normalise.py text --input TEXT
    python tools/corpus/normalise.py file --path FILE [--in-place]
    python tools/corpus/normalise.py scan [--db PATH] [--json]
    python tools/corpus/normalise.py apply [--db PATH] [--dry-run]
    python tools/corpus/normalise.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

MOJIBAKE_REPAIRS: list[tuple[str, str]] = [
    ("Ã©", "é"),  # Ã© -> é
    ("Ã¨", "è"),  # Ã¨ -> è
    ("Ã¶", "ö"),  # Ã¶ -> ö
    ("Ã¼", "ü"),  # Ã¼ -> ü
    ("Ã­", "í"),  # Ã­ -> í
    ("Ã±", "ñ"),  # Ã± -> ñ
    ("גמע",       # GAMMA-aleph-pe (cp1255 dash)
     "–"),
    ("â", "–"),  # â€" -> en dash (UTF-8 as latin1)
    ("â", "—"),  # â€" -> em dash
    ("â", "’"),  # â€™ -> right single quote
    ("â", "“"),  # â€œ -> left double quote
    ("â", "”"),  # â€ -> right double quote
]

DASH_MAP = str.maketrans({
    "–": "-",  # en dash
    "—": "-",  # em dash
    "―": "-",  # horizontal bar
    "‒": "-",  # figure dash
    "‐": "-",  # hyphen
    "﹘": "-",  # small em dash
    "﹣": "-",  # small hyphen-minus
    "－": "-",  # fullwidth hyphen-minus
})

TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)


def normalise_text(text: str) -> str:
    result = unicodedata.normalize("NFC", text)

    for bad, good in MOJIBAKE_REPAIRS:
        result = result.replace(bad, good)

    result = result.translate(DASH_MAP)

    result = TRAILING_WS.sub("", result)

    return result


def scan_chunks(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT chunk_id, source_id, norm_text, raw_text "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    results = []
    for row in rows:
        chunk_id, source_id, norm_text, raw_text = row
        text = norm_text or raw_text or ""
        normalised = normalise_text(text)
        if normalised != text:
            results.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "original_len": len(text),
                "normalised_len": len(normalised),
                "diff_chars": len(text) - len(normalised),
            })

    return results


def apply_normalisation(conn, dry_run: bool = True) -> dict:
    rows = conn.execute(
        "SELECT chunk_id, norm_text, raw_text "
        "FROM chunks WHERE status != 'superseded'"
    ).fetchall()

    updated = []
    for row in rows:
        chunk_id, norm_text, raw_text = row
        text = norm_text or raw_text or ""
        normalised = normalise_text(text)
        if normalised != text:
            new_sha = _sha256(normalised)
            action = {
                "chunk_id": chunk_id,
                "diff_chars": len(text) - len(normalised),
                "applied": not dry_run,
            }

            if not dry_run:
                conn.execute(
                    "UPDATE chunks SET norm_text = ?, norm_sha256 = ? "
                    "WHERE chunk_id = ?",
                    (normalised, new_sha, chunk_id),
                )

            updated.append(action)

    if not dry_run:
        conn.commit()

    return {
        "total_scanned": len(rows),
        "updated": updated,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    # Check 1: NFC normalisation
    nfd = unicodedata.normalize("NFD", "café")
    result = normalise_text(nfd)
    assert result == "café"
    assert unicodedata.is_normalized("NFC", result)
    checks += 1

    # Check 2: mojibake repair (UTF-8 as latin1 en dash)
    result = normalise_text("wordâword")
    assert "â" not in result
    assert "-" in result
    checks += 1

    # Check 3: mojibake repair (accented e)
    result = normalise_text("cafÃ©")
    assert result == "café"
    checks += 1

    # Check 4: dash variant mapping (en dash)
    result = normalise_text("2020–2025")
    assert result == "2020-2025"
    checks += 1

    # Check 5: dash variant mapping (em dash)
    result = normalise_text("word—word")
    assert result == "word-word"
    checks += 1

    # Check 6: trailing whitespace stripped
    result = normalise_text("hello   \nworld  \n")
    assert result == "hello\nworld\n"
    checks += 1

    # Check 7: mixed normalisation
    text = "cafÃ© 2020–2025   "
    result = normalise_text(text)
    assert result == "café 2020-2025"
    checks += 1

    # Check 8: clean text unchanged
    clean = "This is perfectly clean text."
    assert normalise_text(clean) == clean
    checks += 1

    # Check 9: empty string
    assert normalise_text("") == ""
    checks += 1

    # Check 10: fullwidth hyphen
    result = normalise_text("test－case")
    assert result == "test-case"
    checks += 1

    # Check 11: multiple mojibake in one string
    text = "cafÃ© and Ã¶ther"
    result = normalise_text(text)
    assert "é" in result
    assert "ö" in result
    checks += 1

    # Check 12: cp1255 round-trip damage
    text = "MathematicsגמעStatistics"
    result = normalise_text(text)
    assert "ג" not in result
    checks += 1

    # Check 13: scan finds chunks needing normalisation
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c1", "src1", 0, "H1", "prose", None,
             "cafÃ© text   ",
             "raw", 3, _sha256("c1"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c2", "src1", 1, "H2", "prose", None,
             "clean text without issues",
             "raw", 4, _sha256("c2"), 0, 0, "accepted", None, now),
        )
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("c3", "src1", 2, "H3", "prose", None,
             "2020–2025 range",
             "raw", 3, _sha256("c3"), 0, 0, "superseded", None, now),
        )
        conn.commit()

        scan = scan_chunks(conn)
        assert len(scan) == 1
        assert scan[0]["chunk_id"] == "c1"
        checks += 1

        # Check 14: dry run does not modify
        before = conn.execute(
            "SELECT norm_text FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        apply_normalisation(conn, dry_run=True)
        after = conn.execute(
            "SELECT norm_text FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        assert before == after
        checks += 1

        # Check 15: apply updates norm_text
        result = apply_normalisation(conn, dry_run=False)
        assert len(result["updated"]) == 1
        updated_text = conn.execute(
            "SELECT norm_text FROM chunks WHERE chunk_id = 'c1'"
        ).fetchone()[0]
        assert "Ã" not in updated_text
        assert "café" in updated_text
        assert not updated_text.endswith(" ")
        checks += 1

        # Check 16: re-apply is idempotent
        result2 = apply_normalisation(conn, dry_run=False)
        assert len(result2["updated"]) == 0
        checks += 1

        # Check 17: superseded chunks excluded
        scan_ids = [s["chunk_id"] for s in scan_chunks(conn)]
        assert "c3" not in scan_ids
        checks += 1

        # Check 18: empty corpus
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        assert scan_chunks(empty_conn) == []
        r = apply_normalisation(empty_conn, dry_run=False)
        assert r["total_scanned"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS normalise selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus text normaliser")
    sub = parser.add_subparsers(dest="cmd")

    p_text = sub.add_parser("text", help="Normalise a text string")
    p_text.add_argument("--input", required=True)

    p_file = sub.add_parser("file", help="Normalise a file")
    p_file.add_argument("--path", required=True)
    p_file.add_argument("--in-place", action="store_true")

    p_scan = sub.add_parser("scan", help="Scan corpus for denormalised text")
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--json", action="store_true")

    p_apply = sub.add_parser("apply", help="Normalise corpus chunks")
    p_apply.add_argument("--db", default=str(DEFAULT_DB))
    p_apply.add_argument("--dry-run", action="store_true")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args()

    if args.cmd == "selftest":
        ok = _selftest()
        sys.exit(0 if ok else 1)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "text":
        result = normalise_text(args.input)
        print(result)

    elif args.cmd == "file":
        path = Path(args.path)
        text = path.read_text(encoding="utf-8")
        result = normalise_text(text)
        if args.in_place:
            path.write_text(result, encoding="utf-8")
            print(f"  Normalised {path} in place.")
        else:
            print(result)

    elif args.cmd == "scan":
        conn = connect(args.db)
        results = scan_chunks(conn)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print("  All chunks are normalised.")
            else:
                print(f"  {len(results)} chunk(s) need normalisation:")
                for r in results[:50]:
                    print(f"    {r['chunk_id'][:12]}  "
                          f"delta {r['diff_chars']:+d} chars")
        conn.close()

    elif args.cmd == "apply":
        conn = connect(args.db)
        result = apply_normalisation(conn, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "APPLIED"
        print(f"  {mode}: scanned {result['total_scanned']}, "
              f"updated {len(result['updated'])}")
        conn.close()


if __name__ == "__main__":
    main()
