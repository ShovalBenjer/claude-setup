#!/usr/bin/env python3
"""Corpus chunker: stage 2 of the ingestion pipeline.

Splits markdown documents on h2/h3 headings, subdivides sections above
~350 words, classifies chunk kind, and inserts rows into the chunks
table.  Uses normalise.py for text normalisation and reclassify.py
for kind detection.

Usage:
    python tools/corpus/chunker.py chunk --text TEXT [--source-id SID]
    python tools/corpus/chunker.py ingest --path FILE --source-id SID [--db PATH]
    python tools/corpus/chunker.py scan --dir DIR [--db PATH] [--json]
    python tools/corpus/chunker.py stats [--db PATH] [--json]
    python tools/corpus/chunker.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalise import normalise_text  # noqa: E402
from reclassify import _detect_kind  # noqa: E402
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

MAX_CHUNK_WORDS = 350
MIN_CHUNK_WORDS = 30

HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)


def _split_on_headings(text: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [{"heading_path": "", "text": text.strip()}]

    sections = []

    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append({"heading_path": "", "text": preamble})

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        prefix = f"h{level}:" if level > 2 else ""
        sections.append({
            "heading_path": f"{prefix}{title}",
            "text": body,
        })

    return sections


def _subdivide(text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current: list[str] = []
    current_wc = 0

    for para in paragraphs:
        para_wc = len(para.split())
        if current_wc + para_wc > max_words and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_wc = para_wc
        else:
            current.append(para)
            current_wc += para_wc

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_text(
    text: str,
    source_id: str = "unknown",
) -> list[dict]:
    normalised = normalise_text(text)
    sections = _split_on_headings(normalised)

    chunks = []
    ordinal = 0

    for section in sections:
        parts = _subdivide(section["text"])
        for part in parts:
            stripped = part.strip()
            if not stripped:
                continue

            word_count = len(stripped.split())
            if word_count < MIN_CHUNK_WORDS and len(parts) > 1:
                continue

            kind = _detect_kind(stripped)
            norm_sha = _sha256(stripped)
            chunk_id = "c" + norm_sha[:16]

            chunks.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "ordinal": ordinal,
                "heading_path": section["heading_path"],
                "kind": kind,
                "lang": None,
                "norm_text": stripped,
                "raw_text": stripped,
                "word_count": word_count,
                "norm_sha256": norm_sha,
                "simhash": 0,
                "citation_count": 0,
                "status": "accepted",
                "status_reason": None,
            })
            ordinal += 1

    return chunks


def ingest_file(
    conn,
    file_path: str,
    source_id: str,
    dry_run: bool = False,
) -> list[dict]:
    text = Path(file_path).read_text(encoding="utf-8")
    chunks = chunk_text(text, source_id=source_id)

    if not dry_run:
        now = "2026-08-30T00:00:00Z"
        for ch in chunks:
            try:
                conn.execute(
                    "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ch["chunk_id"], ch["source_id"], ch["ordinal"],
                     ch["heading_path"], ch["kind"], ch["lang"],
                     ch["norm_text"], ch["raw_text"], ch["word_count"],
                     ch["norm_sha256"], ch["simhash"], ch["citation_count"],
                     ch["status"], ch["status_reason"], now),
                )
            except Exception:
                pass
        conn.commit()

    return chunks


def chunk_stats(conn) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    by_kind = conn.execute(
        "SELECT kind, COUNT(*) FROM chunks GROUP BY kind ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_status = conn.execute(
        "SELECT status, COUNT(*) FROM chunks GROUP BY status"
    ).fetchall()
    avg_words = conn.execute(
        "SELECT AVG(word_count) FROM chunks"
    ).fetchone()[0]

    return {
        "total_chunks": total,
        "by_kind": dict(by_kind),
        "by_status": dict(by_status),
        "avg_word_count": round(avg_words, 1) if avg_words else 0,
    }


# -- selftest ----------------------------------------------------------------

def _selftest():
    checks = 0

    # Check 1: simple text produces one chunk
    chunks = chunk_text("This is a simple paragraph of text about testing.")
    assert len(chunks) >= 1
    checks += 1

    # Check 2: heading splits produce multiple chunks
    text = (
        "## Introduction\n\nThis is the intro section with enough words "
        "to make a meaningful chunk for testing purposes here.\n\n"
        "## Methods\n\nThis is the methods section with sufficient content "
        "to be a standalone chunk for the test.\n\n"
        "## Results\n\nThe results section contains findings that are "
        "important for the analysis.\n"
    )
    chunks = chunk_text(text)
    assert len(chunks) >= 3, f"expected >=3 chunks, got {len(chunks)}"
    checks += 1

    # Check 3: heading paths captured
    headings = [c["heading_path"] for c in chunks]
    assert "Introduction" in headings
    assert "Methods" in headings
    checks += 1

    # Check 4: h3 headings also split
    text = (
        "## Main\n\nMain content here.\n\n"
        "### Sub Section\n\nSub content here for the subsection.\n"
    )
    chunks = chunk_text(text)
    sub_chunks = [c for c in chunks if "Sub Section" in c["heading_path"]]
    assert len(sub_chunks) >= 1
    checks += 1

    # Check 5: long section subdivided
    words = " ".join(f"word{i}" for i in range(500))
    text = f"## Long Section\n\n{words[:200]}\n\n{words[200:400]}\n\n{words[400:]}"
    chunks = chunk_text(text)
    assert len(chunks) >= 2, f"expected >=2 chunks for long section, got {len(chunks)}"
    checks += 1

    # Check 6: kind detection works
    code_text = (
        "## Code Example\n\n"
        "```python\nimport os\nimport sys\n"
        "def main():\n    print('hello')\n```\n"
    )
    chunks = chunk_text(code_text)
    assert any(c["kind"] == "code" for c in chunks)
    checks += 1

    # Check 7: chunk IDs are deterministic
    text = "## Test\n\nSome test content for deterministic hashing."
    c1 = chunk_text(text)
    c2 = chunk_text(text)
    assert c1[0]["chunk_id"] == c2[0]["chunk_id"]
    checks += 1

    # Check 8: ordinals are sequential
    text = "## A\n\nContent A.\n\n## B\n\nContent B.\n\n## C\n\nContent C.\n"
    chunks = chunk_text(text)
    ordinals = [c["ordinal"] for c in chunks]
    assert ordinals == list(range(len(chunks)))
    checks += 1

    # Check 9: normalisation applied (dash mapping)
    text = "## Test\n\n2020–2025 range with en dash."
    chunks = chunk_text(text)
    assert "2020-2025" in chunks[0]["norm_text"]
    checks += 1

    # Check 10: source_id propagated
    chunks = chunk_text("## X\n\nContent here.", source_id="src42")
    assert all(c["source_id"] == "src42" for c in chunks)
    checks += 1

    # Check 11: empty text
    chunks = chunk_text("")
    assert chunks == []
    checks += 1

    # Check 12: whitespace-only text
    chunks = chunk_text("   \n\n   ")
    assert chunks == []
    checks += 1

    # Check 13: ingest into database
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        conn = connect(str(db_path))
        init_schema(conn)

        now = "2026-08-30T00:00:00Z"
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src1", "file:///a.md", "local_md", "Test Doc",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("a"), 100, None),
        )
        conn.commit()

        test_file = Path(td) / "test.md"
        test_file.write_text(
            "## Overview\n\nThis document provides an overview of the "
            "system architecture and design decisions.\n\n"
            "## Implementation\n\nThe implementation uses SQLite for "
            "storage and Python for the processing pipeline.\n",
            encoding="utf-8",
        )

        result = ingest_file(conn, str(test_file), "src1")
        assert len(result) >= 2

        db_count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE source_id = 'src1'"
        ).fetchone()[0]
        assert db_count >= 2
        checks += 1

        # Check 14: stats work
        stats = chunk_stats(conn)
        assert stats["total_chunks"] >= 2
        assert "by_kind" in stats
        checks += 1

        # Check 15: duplicate ingest is safe
        result2 = ingest_file(conn, str(test_file), "src1")
        db_count2 = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE source_id = 'src1'"
        ).fetchone()[0]
        assert db_count2 == db_count
        checks += 1

        # Check 16: claim detection
        claim_file = Path(td) / "claims.md"
        claim_file.write_text(
            "## Requirements\n\n"
            "The system must always validate input. It should never "
            "accept unverified data. This ensures and guarantees "
            "data integrity.\n",
            encoding="utf-8",
        )
        conn.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("src2", "file:///b.md", "local_md", "Claims",
             "CC-BY-4.0", "vendor", "LICENSE", "test", now,
             now, None, None, "live", _sha256("b"), 50, None),
        )
        conn.commit()
        claim_chunks = ingest_file(conn, str(claim_file), "src2")
        assert any(c["kind"] == "claim" for c in claim_chunks)
        checks += 1

        # Check 17: empty corpus stats
        empty_conn = connect(str(Path(td) / "empty.db"))
        init_schema(empty_conn)
        es = chunk_stats(empty_conn)
        assert es["total_chunks"] == 0
        empty_conn.close()
        checks += 1

        conn.close()

    print(f"PASS chunker selftest ({checks} checks)")
    return True


# -- CLI ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Corpus chunker")
    sub = parser.add_subparsers(dest="cmd")

    p_chunk = sub.add_parser("chunk", help="Chunk a text string")
    p_chunk.add_argument("--text", required=True)
    p_chunk.add_argument("--source-id", default="cli")
    p_chunk.add_argument("--json", action="store_true")

    p_ingest = sub.add_parser("ingest", help="Ingest a file")
    p_ingest.add_argument("--path", required=True)
    p_ingest.add_argument("--source-id", required=True)
    p_ingest.add_argument("--db", default=str(DEFAULT_DB))
    p_ingest.add_argument("--dry-run", action="store_true")

    p_scan = sub.add_parser("scan", help="Scan a directory for files")
    p_scan.add_argument("--dir", required=True)
    p_scan.add_argument("--db", default=str(DEFAULT_DB))
    p_scan.add_argument("--json", action="store_true")

    p_stats = sub.add_parser("stats", help="Chunk statistics")
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

    if args.cmd == "chunk":
        chunks = chunk_text(args.text, source_id=args.source_id)
        if args.json:
            print(json.dumps(chunks, indent=2))
        else:
            print(f"  {len(chunks)} chunk(s):")
            for c in chunks:
                print(f"    {c['chunk_id'][:12]}  {c['kind']:6s}  "
                      f"{c['word_count']:4d}w  {c['heading_path']}")

    elif args.cmd == "ingest":
        conn = connect(args.db)
        chunks = ingest_file(conn, args.path, args.source_id,
                             dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "INGESTED"
        print(f"  {mode}: {len(chunks)} chunk(s) from {args.path}")
        for c in chunks[:20]:
            print(f"    {c['chunk_id'][:12]}  {c['kind']:6s}  "
                  f"{c['word_count']:4d}w  {c['heading_path']}")
        conn.close()

    elif args.cmd == "scan":
        target = Path(args.dir)
        files = sorted(target.rglob("*.md"))
        print(f"  {len(files)} markdown file(s) in {target}")
        total_chunks = 0
        for f in files[:50]:
            text = f.read_text(encoding="utf-8", errors="replace")
            chunks = chunk_text(text, source_id=str(f))
            total_chunks += len(chunks)
            if args.json:
                continue
            print(f"    {f.name:40s}  {len(chunks):3d} chunk(s)")
        if args.json:
            print(json.dumps({"files": len(files), "chunks": total_chunks}))
        else:
            print(f"  Total: {total_chunks} chunk(s)")

    elif args.cmd == "stats":
        conn = connect(args.db)
        stats = chunk_stats(conn)
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"  Total chunks:     {stats['total_chunks']}")
            print(f"  Avg word count:   {stats['avg_word_count']}")
            print("  By kind:")
            for k, v in stats["by_kind"].items():
                print(f"    {k:10s}: {v:5d}")
            print("  By status:")
            for k, v in stats["by_status"].items():
                print(f"    {k:12s}: {v:5d}")
        conn.close()


if __name__ == "__main__":
    main()
