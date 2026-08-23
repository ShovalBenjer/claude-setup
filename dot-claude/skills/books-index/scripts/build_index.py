"""Incremental full-text index over docs/books. stdlib sqlite3 + FTS5 only.
Local-only: reads files already on disk, writes only to the local sqlite db.

Usage: uv run python build_index.py [--full] [--books-dir DIR] [--db PATH]
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

CHUNK_WORDS = 800
SUPPORTED_EXTS = {".txt"}  # epub is pre-extracted to .txt by books-ingest
SKIP_SUFFIXES = (":Zone.Identifier",)


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            size INTEGER NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            path, chunk_index UNINDEXED, content
        );
    """)


def chunk_text(text: str, words_per_chunk: int = CHUNK_WORDS) -> list[str]:
    words = text.split()
    return [
        " ".join(words[i:i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ] or [""]


def index_file(con: sqlite3.Connection, path: Path, rel: str) -> int:
    con.execute("DELETE FROM chunks WHERE path = ?", (rel,))
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        con.execute("INSERT INTO chunks (path, chunk_index, content) VALUES (?,?,?)",
                    (rel, i, chunk))
    st = path.stat()
    con.execute(
        "INSERT INTO files (path, mtime, size) VALUES (?,?,?) "
        "ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, size=excluded.size",
        (rel, st.st_mtime, st.st_size),
    )
    return len(chunks)


def run(books_dir: Path, db_path: Path, full: bool) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    ensure_schema(con)

    known: dict[str, tuple[float, int]] = {}
    if not full:
        for row in con.execute("SELECT path, mtime, size FROM files"):
            known[row[0]] = (row[1], row[2])

    seen: set[str] = set()
    indexed = skipped = failed = 0
    for path in sorted(books_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        if any(str(path).endswith(s) for s in SKIP_SUFFIXES):
            continue
        rel = str(path.relative_to(books_dir))
        seen.add(rel)
        st = path.stat()
        if not full and known.get(rel) == (st.st_mtime, st.st_size):
            skipped += 1
            continue
        try:
            n = index_file(con, path, rel)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED {rel}: {exc}")
            failed += 1
            continue
        indexed += 1
        print(f"indexed {rel} ({n} chunks)")

    # drop entries for files removed from docs/books
    stale = set(known) - seen
    for rel in stale:
        con.execute("DELETE FROM chunks WHERE path = ?", (rel,))
        con.execute("DELETE FROM files WHERE path = ?", (rel,))

    con.commit()
    total = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    print(f"\nindexed {indexed}, skipped {skipped} (unchanged), "
          f"failed {failed}, removed {len(stale)} stale, {total} files total in index")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--books-dir", type=Path,
                     default=Path.home() / "work/repos/claude-setup/docs/books")
    ap.add_argument("--db", type=Path,
                     default=Path.home() / ".claude/corpus/books.sqlite3")
    args = ap.parse_args()
    if not args.books_dir.is_dir():
        print(f"books dir not found: {args.books_dir}")
        return 2
    run(args.books_dir, args.db, args.full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
