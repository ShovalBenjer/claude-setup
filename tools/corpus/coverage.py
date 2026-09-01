#!/usr/bin/env python3
"""Corpus coverage analysis: what is indexed vs what is on disk.

Walks the source directories that the corpus ingests from, compares
against the sources table, and reports indexed, missing, and orphaned
files.  Optionally checks books index coverage when the books database
is available.

Usage:
    python tools/corpus/coverage.py report [--db PATH] [--books-db PATH]
        [--json] [--missing-only]
    python tools/corpus/coverage.py selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, SOURCE_DIRS, _sha256, connect, init_schema  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import repo_root  # noqa: E402

ROOT = repo_root.resolve()
BOOKS_DIR = ROOT / "docs" / "books"
BOOKS_DB = Path.home() / ".claude" / "corpus" / "books.sqlite3"


def _disk_files(dirs: list[Path]) -> dict[str, Path]:
    """Map canonical_uri (relative to ROOT) to absolute path for all .md files."""
    result: dict[str, Path] = {}
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.rglob("*.md")):
            if f.is_file():
                rel = str(f.relative_to(ROOT))
                result[rel] = f
    return result


def _indexed_uris(conn: sqlite3.Connection) -> dict[str, dict]:
    """Map canonical_uri to source metadata for all local_md sources."""
    rows = conn.execute(
        "SELECT canonical_uri, source_id, liveness, title, "
        "       content_sha256, bytes "
        "FROM sources WHERE kind = 'local_md'"
    ).fetchall()
    result: dict[str, dict] = {}
    for r in rows:
        uri = r[0]
        if uri.startswith("/"):
            try:
                uri = str(Path(uri).relative_to(ROOT))
            except ValueError:
                pass
        result[uri] = {
            "source_id": r[1],
            "liveness": r[2],
            "title": r[3],
            "content_sha256": r[4],
            "bytes": r[5],
        }
    return result


def _chunk_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Count chunks per source_id."""
    rows = conn.execute(
        "SELECT source_id, COUNT(*) FROM chunks GROUP BY source_id"
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _books_coverage(books_db_path: Path | None = None) -> dict | None:
    path = books_db_path or BOOKS_DB
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path))
        indexed_files = conn.execute(
            "SELECT path FROM files"
        ).fetchall()
        indexed_set = {r[0] for r in indexed_files}
        total_chunks = conn.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]
        conn.close()
    except Exception:
        return None

    disk_files: set[str] = set()
    if BOOKS_DIR.exists():
        for f in sorted(BOOKS_DIR.iterdir()):
            if f.is_file() and f.suffix in (".txt", ".epub", ".pdf", ".mobi", ".djvu"):
                disk_files.add(f.name)

    return {
        "indexed_count": len(indexed_set),
        "disk_count": len(disk_files),
        "total_chunks": total_chunks,
        "missing_from_index": sorted(disk_files - indexed_set),
        "orphaned_in_index": sorted(indexed_set - disk_files),
    }


def report(db_path: Path | str | None = None,
           books_db_path: Path | str | None = None) -> dict:
    dp = Path(db_path) if db_path else DEFAULT_DB
    if not dp.exists():
        return {"error": "corpus database not found", "corpus": None, "books": None}

    conn = connect(dp)
    disk = _disk_files(SOURCE_DIRS)
    indexed = _indexed_uris(conn)
    chunks = _chunk_counts(conn)
    conn.close()

    disk_set = set(disk.keys())
    indexed_set = set(indexed.keys())

    missing = sorted(disk_set - indexed_set)
    orphaned = sorted(indexed_set - disk_set)
    covered = sorted(disk_set & indexed_set)

    per_dir: dict[str, dict] = {}
    for d in SOURCE_DIRS:
        if not d.exists():
            continue
        dname = str(d.relative_to(ROOT))
        dir_disk = {k for k in disk_set if k.startswith(dname + "/")}
        dir_indexed = {k for k in indexed_set if k.startswith(dname + "/")}
        per_dir[dname] = {
            "on_disk": len(dir_disk),
            "indexed": len(dir_indexed & dir_disk),
            "missing": len(dir_disk - dir_indexed),
            "rate": round(len(dir_indexed & dir_disk) / len(dir_disk), 3) if dir_disk else 1.0,
        }

    total_chunks_indexed = sum(
        chunks.get(indexed[uri]["source_id"], 0)
        for uri in covered
        if uri in indexed
    )

    bp = Path(books_db_path) if books_db_path else BOOKS_DB
    books = _books_coverage(bp)

    return {
        "corpus": {
            "on_disk": len(disk_set),
            "indexed": len(covered),
            "missing": len(missing),
            "orphaned": len(orphaned),
            "coverage_rate": round(len(covered) / len(disk_set), 3) if disk_set else 1.0,
            "total_chunks": total_chunks_indexed,
            "per_directory": per_dir,
            "missing_files": missing,
            "orphaned_uris": orphaned,
        },
        "books": books,
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        # create fake source directories
        wd = tmpdir / "work-docs"
        rp = tmpdir / "research-papers"
        da = tmpdir / "docs" / "analysis"
        wd.mkdir(parents=True)
        rp.mkdir(parents=True)
        da.mkdir(parents=True)

        (wd / "design.md").write_text("# Design\nPattern overview")
        (wd / "notes.md").write_text("# Notes\nQuick notes here")
        (rp / "paper1.md").write_text("# Paper 1\nAbstract goes here")
        (da / "analysis1.md").write_text("# Analysis\nSome analysis")

        # create corpus DB with only some of these indexed
        db_path = tmpdir / "corpus.db"
        conn = connect(db_path)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        for sid, uri in [
            ("s1", str(wd / "design.md")),
            ("s2", str(rp / "paper1.md")),
        ]:
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES (?, ?, 'local_md', 'Test', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (sid, uri, now, now, _sha256(sid)),
            )
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES ('c1', 's1', 0, 'Test', 'prose', 'text', 'text', "
            " 1, ?, 0, 'accepted', ?)",
            (_sha256("text"), now),
        )
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES ('c2', 's2', 0, 'Test', 'prose', 'paper', 'paper', "
            " 1, ?, 0, 'accepted', ?)",
            (_sha256("paper"), now),
        )
        conn.commit()
        conn.close()

        # monkey-patch module globals for testing
        mod = sys.modules[__name__]
        orig_dirs = mod.SOURCE_DIRS
        orig_root = mod.ROOT
        mod.SOURCE_DIRS = [wd, rp, da]
        mod.ROOT = tmpdir

        try:
            # 1: report returns corpus section
            r = report(db_path=db_path, books_db_path=tmpdir / "no.db")
            checks += 1
            if r["corpus"] is None:
                failures.append("corpus section is None")

            # 2: on_disk counts all .md files
            checks += 1
            if r["corpus"]["on_disk"] != 4:
                failures.append(
                    f"on_disk = {r['corpus']['on_disk']}, expected 4"
                )

            # 3: indexed counts matched files
            checks += 1
            if r["corpus"]["indexed"] != 2:
                failures.append(
                    f"indexed = {r['corpus']['indexed']}, expected 2"
                )

            # 4: missing counts unindexed files
            checks += 1
            if r["corpus"]["missing"] != 2:
                failures.append(
                    f"missing = {r['corpus']['missing']}, expected 2"
                )

            # 5: coverage_rate is correct
            checks += 1
            if r["corpus"]["coverage_rate"] != 0.5:
                failures.append(
                    f"coverage_rate = {r['corpus']['coverage_rate']}, "
                    f"expected 0.5"
                )

            # 6: per_directory has entries for each dir
            checks += 1
            if len(r["corpus"]["per_directory"]) != 3:
                failures.append(
                    f"per_directory has {len(r['corpus']['per_directory'])} "
                    f"entries, expected 3"
                )

            # 7: missing_files lists unindexed paths
            checks += 1
            mf = r["corpus"]["missing_files"]
            if len(mf) != 2:
                failures.append(
                    f"missing_files has {len(mf)} entries, expected 2"
                )

            # 8: work-docs coverage rate is 0.5 (1 of 2)
            checks += 1
            wd_stats = r["corpus"]["per_directory"].get("work-docs", {})
            if wd_stats.get("rate") != 0.5:
                failures.append(
                    f"work-docs rate = {wd_stats.get('rate')}, expected 0.5"
                )

            # 9: research-papers is fully covered
            checks += 1
            rp_stats = r["corpus"]["per_directory"].get("research-papers", {})
            if rp_stats.get("rate") != 1.0:
                failures.append(
                    f"research-papers rate = {rp_stats.get('rate')}, "
                    f"expected 1.0"
                )

            # 10: total_chunks counts chunks for indexed sources
            checks += 1
            if r["corpus"]["total_chunks"] != 2:
                failures.append(
                    f"total_chunks = {r['corpus']['total_chunks']}, "
                    f"expected 2"
                )

            # 11: books is None when DB missing
            checks += 1
            if r["books"] is not None:
                failures.append("books should be None when DB missing")

            # 12: books coverage with a real books DB
            bdb = tmpdir / "books.db"
            bconn = sqlite3.connect(str(bdb))
            bconn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    size INTEGER NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                    path, chunk_index UNINDEXED, content
                );
            """)
            bconn.execute(
                "INSERT INTO files (path, mtime, size) "
                "VALUES ('book1.txt', 1.0, 5000)"
            )
            bconn.execute(
                "INSERT INTO chunks (path, chunk_index, content) "
                "VALUES ('book1.txt', 0, 'some content')"
            )
            bconn.commit()
            bconn.close()

            r = report(db_path=db_path, books_db_path=bdb)
            checks += 1
            if r["books"] is None:
                failures.append("books section should not be None")
            elif r["books"]["indexed_count"] != 1:
                failures.append(
                    f"books indexed_count = {r['books']['indexed_count']}, "
                    f"expected 1"
                )

            # 13: books total_chunks correct
            checks += 1
            if r["books"] and r["books"]["total_chunks"] != 1:
                failures.append(
                    f"books total_chunks = {r['books']['total_chunks']}, "
                    f"expected 1"
                )

            # 14: orphaned detection
            conn = connect(db_path)
            conn.execute(
                "INSERT INTO sources "
                "(source_id, canonical_uri, kind, title, license_spdx, "
                " license_verdict, license_evidence, fetched_utc, liveness, "
                " upstream_mtime, content_sha256, bytes, supersedes) "
                "VALUES ('s_gone', ?, 'local_md', 'Gone', 'MIT', 'vendor', "
                " 'test', ?, 'live', ?, ?, 100, NULL)",
                (str(tmpdir / "gone" / "deleted.md"), now, now, _sha256("gone")),
            )
            conn.commit()
            conn.close()

            r = report(db_path=db_path, books_db_path=tmpdir / "no.db")
            checks += 1
            if r["corpus"]["orphaned"] < 1:
                failures.append(
                    f"orphaned = {r['corpus']['orphaned']}, expected >= 1"
                )

            # 15: missing corpus DB returns error
            r = report(db_path=tmpdir / "nope.db",
                       books_db_path=tmpdir / "no.db")
            checks += 1
            if "error" not in r:
                failures.append("missing DB should return error")

            # 16: JSON output is serializable
            r = report(db_path=db_path, books_db_path=bdb)
            checks += 1
            try:
                json.dumps(r)
            except (TypeError, ValueError) as e:
                failures.append(f"result not JSON-serializable: {e}")

        finally:
            mod.SOURCE_DIRS = orig_dirs
            mod.ROOT = orig_root

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS coverage selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_r = sub.add_parser("report", help="Report corpus coverage")
    p_r.add_argument("--db", default=None)
    p_r.add_argument("--books-db", default=None, dest="books_db")
    p_r.add_argument("--json", action="store_true", dest="as_json")
    p_r.add_argument("--missing-only", action="store_true", dest="missing_only")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    r = report(db_path=args.db, books_db_path=args.books_db)

    if args.as_json:
        print(json.dumps(r, indent=2))
        return 0

    if "error" in r:
        print(f"  error: {r['error']}")
        return 1

    c = r["corpus"]
    print("  Corpus coverage")
    print(f"    on disk:   {c['on_disk']} files")
    print(f"    indexed:   {c['indexed']} files")
    print(f"    missing:   {c['missing']} files")
    print(f"    orphaned:  {c['orphaned']} URIs")
    print(f"    rate:      {c['coverage_rate']:.1%}")
    print(f"    chunks:    {c['total_chunks']}")
    print()

    for dname, stats in c["per_directory"].items():
        print(f"    {dname}: {stats['indexed']}/{stats['on_disk']} "
              f"({stats['rate']:.0%})")
    print()

    if args.missing_only or c["missing"]:
        if c["missing_files"]:
            print("  Missing files:")
            for f in c["missing_files"]:
                print(f"    - {f}")
            print()

    if c["orphaned_uris"]:
        print("  Orphaned URIs (indexed but not on disk):")
        for u in c["orphaned_uris"]:
            print(f"    - {u}")
        print()

    b = r["books"]
    if b is not None:
        print("  Books coverage")
        print(f"    indexed:   {b['indexed_count']} files")
        print(f"    on disk:   {b['disk_count']} files")
        print(f"    chunks:    {b['total_chunks']}")
        if b["missing_from_index"]:
            print(f"    unindexed: {len(b['missing_from_index'])} files")
    else:
        print("  Books: database not available")

    return 0


if __name__ == "__main__":
    sys.exit(main())
