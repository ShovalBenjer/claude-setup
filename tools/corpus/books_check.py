#!/usr/bin/env python3
"""Coverage oracle for the books corpus: is every book on disk searchable?

WHY THIS EXISTS. `docs/books` is gitignored (475 MB, 335 files on 2026-08-23) and indexed
by the books-index skill into `~/.claude/corpus/books.sqlite3`. Nothing measured whether
the index matched the directory. Measured on 2026-08-23: 300 of 335 files indexed, and
every gap was a PDF, mobi or djvu, because the indexer read `.txt` only and books-ingest
extracted epub only. The operator's books (Wigderson, Grohs and Kutyniok, Carlsson TDA,
the MARL book, Lurie) were on disk and invisible to every search. A corpus nobody can
query is a download, not a corpus.

WHAT IT CHECKS, exit 1 on any of the first three:
  1. a `.txt` on disk that the index does not know (not indexed);
  2. a `.txt` whose mtime or size moved since it was indexed (stale);
  3. a `.pdf` or `.epub` with no extracted text beside it (extractable, not extracted);
  4. reported only, never failing: `.mobi`, `.djvu`, extensionless, partial downloads.
     Those need tools this machine does not have (calibre, djvulibre); the count stays
     visible so it cannot be mistaken for coverage.

Text-sibling convention, shared with the skill: epub -> `<stem>.txt` (books-ingest),
pdf -> `<name>.pdf.txt` (build_index.py extract_pdfs).

Usage:
  python tools/corpus/books_check.py [--books-dir DIR] [--db PATH]   # report, exit 1 on drift
  python tools/corpus/books_check.py selftest
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path.home() / ".claude" / "corpus" / "books.sqlite3"
EXTRACTABLE = {".pdf", ".epub"}
UNEXTRACTABLE = {".mobi", ".djvu", ".azw3", ".crdownload", ""}
SKIP_SUFFIXES = (":Zone.Identifier",)


def default_books_dir() -> Path:
    """The main checkout's docs/books, since a worktree has no copy of a gitignored tree."""
    here = REPO_ROOT / "docs" / "books"
    if here.is_dir():
        return here
    main = Path.home() / "work" / "repos" / "claude-setup" / "docs" / "books"
    return main if main.is_dir() else here


def text_sibling(path: Path) -> Path:
    if path.suffix.lower() == ".pdf":
        return path.with_name(path.name + ".txt")
    return path.with_suffix(".txt")


def indexed_files(db: Path) -> dict[str, tuple[float, int]]:
    if not db.exists():
        return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {r[0]: (r[1], r[2]) for r in con.execute("SELECT path, mtime, size FROM files")}
    except sqlite3.Error:
        return {}
    finally:
        con.close()


def measure(books_dir: Path, db: Path) -> dict[str, object]:
    known = indexed_files(db)
    on_disk = [p for p in sorted(books_dir.rglob("*")) if p.is_file()
               and not any(str(p).endswith(s) for s in SKIP_SUFFIXES)]
    not_indexed: list[str] = []
    stale: list[str] = []
    unextracted: list[str] = []
    unextractable: list[str] = []
    by_ext: dict[str, int] = {}
    for p in on_disk:
        ext = p.suffix.lower()
        by_ext[ext or "(none)"] = by_ext.get(ext or "(none)", 0) + 1
        rel = str(p.relative_to(books_dir))
        if ext == ".txt":
            if rel not in known:
                not_indexed.append(rel)
            else:
                st = p.stat()
                if known[rel] != (st.st_mtime, st.st_size):
                    stale.append(rel)
        elif ext in EXTRACTABLE:
            if not text_sibling(p).exists():
                unextracted.append(rel)
        elif ext in UNEXTRACTABLE:
            unextractable.append(rel)
    return {
        "books_dir": str(books_dir), "db": str(db), "db_exists": db.exists(),
        "files_on_disk": len(on_disk), "by_ext": by_ext, "indexed": len(known),
        "not_indexed": not_indexed, "stale": stale,
        "unextracted": unextracted, "unextractable": unextractable,
    }


def report(m: dict[str, object]) -> int:
    print(f"books: {m['files_on_disk']} files in {m['books_dir']}; index {m['db']} "
          f"{'present' if m['db_exists'] else 'MISSING'} with {m['indexed']} files")
    print("  by extension: " + ", ".join(f"{k} {v}" for k, v in sorted(m["by_ext"].items())))  # type: ignore[union-attr]
    problems = 0
    for key, label in (("not_indexed", "txt not indexed"), ("stale", "txt changed since indexed"),
                       ("unextracted", "pdf/epub without extracted text")):
        items = m[key]  # type: ignore[index]
        if items:
            problems += len(items)  # type: ignore[arg-type]
            print(f"  DRIFT {label}: {len(items)}")  # type: ignore[arg-type]
            for rel in items[:10]:  # type: ignore[index]
                print(f"    {rel}")
    if m["unextractable"]:
        print(f"  unextractable, reported only: {len(m['unextractable'])} "  # type: ignore[arg-type]
              f"({', '.join(Path(r).suffix or '(none)' for r in m['unextractable'])})")  # type: ignore[union-attr]
    if problems:
        print(f"books_check: {problems} drift item(s). Run the books-index skill: "
              "python ~/.claude/skills/books-index/scripts/build_index.py")
        return 1
    print("books_check clean: every txt indexed and current, every pdf/epub extracted")
    return 0


def selftest() -> int:
    failures: list[str] = []

    def check(name: str, got: object, want: object) -> None:
        if got != want:
            failures.append(f"{name}: got {got!r} want {want!r}")

    with tempfile.TemporaryDirectory() as td:
        books = Path(td) / "books"
        books.mkdir()
        db = Path(td) / "books.sqlite3"
        (books / "a.txt").write_text("alpha")
        (books / "b.pdf").write_bytes(b"%PDF-1.4")
        (books / "c.epub").write_bytes(b"PK")
        (books / "c.txt").write_text("extracted c")
        (books / "d.mobi").write_bytes(b"x")
        m = measure(books, db)
        check("no db: every txt unindexed", m["not_indexed"], ["a.txt", "c.txt"])
        check("pdf without sibling is unextracted", m["unextracted"], ["b.pdf"])
        check("epub with sibling is fine", "c.epub" in m["unextracted"], False)  # type: ignore[operator]
        check("mobi is reported not failed", m["unextractable"], ["d.mobi"])
        check("drift exits 1", report(m), 1)

        con = sqlite3.connect(db)
        con.execute("CREATE TABLE files (path TEXT PRIMARY KEY, mtime REAL, size INTEGER)")
        for name in ("a.txt", "c.txt"):
            st = (books / name).stat()
            con.execute("INSERT INTO files VALUES (?,?,?)", (name, st.st_mtime, st.st_size))
        con.commit()
        con.close()
        (books / "b.pdf.txt").write_text("extracted b")
        m = measure(books, db)
        # b.pdf.txt itself is a new txt the index has not seen, which is the honest answer
        check("new extracted txt is not yet indexed", m["not_indexed"], ["b.pdf.txt"])
        st = (books / "b.pdf.txt").stat()
        con = sqlite3.connect(db)
        con.execute("INSERT INTO files VALUES (?,?,?)", ("b.pdf.txt", st.st_mtime, st.st_size))
        con.commit()
        con.close()
        m = measure(books, db)
        check("clean exits 0", report(m), 0)
        (books / "a.txt").write_text("alpha changed, longer")
        m = measure(books, db)
        check("a changed txt is stale", m["stale"], ["a.txt"])

    for f in failures:
        print("FAIL", f)
    print(f"books_check selftest: {len(failures)} checks failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", default="check", choices=["check", "selftest"])
    ap.add_argument("--books-dir", type=Path, default=None)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args(argv)
    if args.command == "selftest":
        return selftest()
    books_dir = args.books_dir or default_books_dir()
    if not books_dir.is_dir():
        print(f"books dir not found: {books_dir}")
        return 2
    return report(measure(books_dir, args.db))


if __name__ == "__main__":
    sys.exit(main())
