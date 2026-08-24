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


def extract_pdfs(books_dir: Path) -> tuple[int, int, int]:
    """Write `<name>.pdf.txt` beside every PDF that has none, so the txt-only indexer sees it.

    Measured 2026-08-23: 300 of 335 files in docs/books were indexed and the 35 gaps were
    every PDF, mobi and djvu, because this indexer reads `.txt` only and books-ingest
    extracts epub only. pypdf is imported lazily: without it the PDFs are counted as
    unextracted and reported, never silently skipped. Returns (extracted, skipped, failed).
    """
    pdfs = [p for p in sorted(books_dir.rglob("*.pdf")) if p.is_file()]
    todo = [p for p in pdfs if not p.with_name(p.name + ".txt").exists()]
    if not todo:
        return 0, len(pdfs), 0
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        print(f"pypdf not importable: {len(todo)} PDF(s) stay unextracted "
              "(uv run --with pypdf python build_index.py)")
        return 0, len(pdfs) - len(todo), len(todo)
    done = failed = 0
    for p in todo:
        try:
            reader = PdfReader(str(p))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED extract {p.name}: {exc}")
            failed += 1
            continue
        if not text.strip():
            print(f"EMPTY extract {p.name}: scanned or image-only PDF, no text layer")
            failed += 1
            continue
        p.with_name(p.name + ".txt").write_text(text, encoding="utf-8")
        done += 1
        print(f"extracted {p.name} ({len(reader.pages)} pages)")
    return done, len(pdfs) - len(todo), failed


def run(books_dir: Path, db_path: Path, full: bool) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    ensure_schema(con)

    ex, ex_skipped, ex_failed = extract_pdfs(books_dir)
    print(f"pdf extraction: {ex} new, {ex_skipped} already had text, {ex_failed} failed")

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
