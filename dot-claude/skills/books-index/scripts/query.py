"""Query the local docs/books FTS5 index. Local-only, read-only.

Usage: uv run python query.py "search terms" [--limit N] [--db PATH]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--db", type=Path,
                     default=Path.home() / ".claude/corpus/books.sqlite3")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"no index at {args.db}, run build_index.py first", file=sys.stderr)
        return 2

    con = sqlite3.connect(args.db)
    rows = con.execute(
        "SELECT path, chunk_index, snippet(chunks, 2, '[', ']', '...', 12), "
        "bm25(chunks) AS rank "
        "FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
        (args.query, args.limit),
    ).fetchall()

    if not rows:
        print("(0 hits)")
        return 0

    for path, chunk_idx, snippet, rank in rows:
        print(f"{path} #{chunk_idx}  {snippet}")
    print(f"\n{len(rows)} hit(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
