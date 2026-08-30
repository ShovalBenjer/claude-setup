#!/usr/bin/env python3
"""Unified search across research corpus and books index.

Queries both state/corpus.db (FTS5 on accepted chunks) and the books
index (~/.claude/corpus/books.sqlite3) when available, merging results
with provenance tags so the caller knows which database each hit came
from.  Gracefully degrades when either database is absent.

Usage:
    python tools/corpus/search.py query TEXT [--k N] [--json]
        [--corpus-only | --books-only] [--snippet N] [--kind KIND]
        [--db PATH] [--books-db PATH]
    python tools/corpus/search.py selftest
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research import DEFAULT_DB, _sha256, connect, init_schema  # noqa: E402

BOOKS_DB = Path.home() / ".claude" / "corpus" / "books.sqlite3"
SNIPPET_LEN = 300


def _connect_books(db_path: Path | None = None) -> sqlite3.Connection | None:
    path = db_path or BOOKS_DB
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT 1 FROM chunks LIMIT 1")
        return conn
    except Exception:
        return None


def _fts_query(words: list[str]) -> str:
    return " OR ".join(words)


def search_corpus(conn: sqlite3.Connection, words: list[str],
                  top_k: int = 20, kind: str | None = None,
                  snippet_len: int = SNIPPET_LEN) -> list[dict]:
    fts = _fts_query(words)
    kind_clause = ""
    params: list = [fts]
    if kind:
        kinds = [k.strip() for k in kind.split(",")]
        placeholders = ",".join("?" * len(kinds))
        kind_clause = f" AND c.kind IN ({placeholders})"
        params.extend(kinds)
    params.append(top_k)

    sql = (
        "SELECT c.chunk_id, c.norm_text, c.kind, c.source_id, c.word_count, "
        "       s.canonical_uri, s.title "
        "FROM chunks_fts f "
        "JOIN chunks c ON f.rowid = c.rowid "
        "JOIN sources s ON c.source_id = s.source_id "
        "WHERE f.norm_text MATCH ? AND c.status = 'accepted'"
        f"{kind_clause} "
        "LIMIT ?"
    )
    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        text = r[1] or ""
        results.append({
            "source_db": "corpus",
            "id": r[0],
            "snippet": text[:snippet_len],
            "kind": r[2],
            "source_id": r[3],
            "word_count": r[4],
            "uri": r[5],
            "title": r[6],
        })
    return results


def search_books(conn: sqlite3.Connection, words: list[str],
                 top_k: int = 20,
                 snippet_len: int = SNIPPET_LEN) -> list[dict]:
    fts = _fts_query(words)
    sql = (
        "SELECT path, chunk_index, snippet(chunks, 2, '', '', '...', 40) "
        "FROM chunks WHERE content MATCH ? LIMIT ?"
    )
    rows = conn.execute(sql, [fts, top_k]).fetchall()
    results = []
    for r in rows:
        snip = r[2] or ""
        results.append({
            "source_db": "books",
            "id": f"{r[0]}:{r[1]}",
            "snippet": snip[:snippet_len],
            "kind": "book",
            "source_id": None,
            "word_count": None,
            "uri": r[0],
            "title": Path(r[0]).stem.replace("_", " ").replace("-", " "),
        })
    return results


def search(query_text: str, *, top_k: int = 20,
           corpus_only: bool = False, books_only: bool = False,
           kind: str | None = None, snippet_len: int = SNIPPET_LEN,
           db_path: Path | str | None = None,
           books_db_path: Path | str | None = None) -> dict:
    words = query_text.lower().split()
    if not words:
        return {"query": query_text, "results": [], "databases": []}

    corpus_results: list[dict] = []
    books_results: list[dict] = []
    databases: list[str] = []

    if not books_only:
        dp = Path(db_path) if db_path else DEFAULT_DB
        if dp.exists():
            conn = connect(dp)
            corpus_results = search_corpus(conn, words, top_k, kind, snippet_len)
            conn.close()
            databases.append("corpus")

    if not corpus_only:
        bp = Path(books_db_path) if books_db_path else BOOKS_DB
        bconn = _connect_books(bp)
        if bconn is not None:
            books_results = search_books(bconn, words, top_k, snippet_len)
            bconn.close()
            databases.append("books")

    merged = corpus_results + books_results
    merged = merged[:top_k]

    return {
        "query": query_text,
        "results": merged,
        "databases": databases,
        "total": len(merged),
    }


def selftest() -> int:
    failures: list[str] = []
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        # --- corpus DB ---
        corpus_db = tmpdir / "corpus.db"
        conn = connect(corpus_db)
        init_schema(conn)
        now = "2026-08-30T00:00:00Z"

        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " upstream_mtime, content_sha256, bytes, supersedes) "
            "VALUES (?, ?, 'local_md', 'Design Patterns', 'MIT', 'vendor', "
            " 'test', ?, 'live', ?, ?, 200, NULL)",
            ("s1", "/test/patterns.md", now, now, _sha256("s1")),
        )
        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " upstream_mtime, content_sha256, bytes, supersedes) "
            "VALUES (?, ?, 'local_md', 'Algorithms', 'MIT', 'vendor', "
            " 'test', ?, 'live', ?, ?, 150, NULL)",
            ("s2", "/test/algorithms.md", now, now, _sha256("s2")),
        )
        for cid, sid, text, kind_val, ordinal in [
            ("c1", "s1", "the observer pattern decouples event producers from consumers", "prose", 0),
            ("c2", "s1", "factory method creates objects without specifying concrete class", "prose", 1),
            ("c3", "s2", "quicksort partitions the array around a pivot element", "prose", 0),
            ("c4", "s2", "binary search halves the search space logarithmically", "code", 1),
        ]:
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " status, ingested_utc) "
                "VALUES (?, ?, ?, 'Test', ?, ?, ?, ?, ?, 0, 'accepted', ?)",
                (cid, sid, ordinal, kind_val, text, text,
                 len(text.split()), _sha256(text), now),
            )
        conn.commit()
        conn.close()

        # --- books DB ---
        books_db = tmpdir / "books.db"
        bconn = sqlite3.connect(str(books_db))
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
            "INSERT INTO files (path, mtime, size) VALUES (?, 1.0, 5000)",
            ("clean-code.txt",),
        )
        bconn.execute(
            "INSERT INTO chunks (path, chunk_index, content) VALUES (?, 0, ?)",
            ("clean-code.txt",
             "meaningful names make code self-documenting and reduce cognitive load"),
        )
        bconn.execute(
            "INSERT INTO files (path, mtime, size) VALUES (?, 1.0, 8000)",
            ("refactoring.txt",),
        )
        bconn.execute(
            "INSERT INTO chunks (path, chunk_index, content) VALUES (?, 0, ?)",
            ("refactoring.txt",
             "extract method reduces duplication and improves readability"),
        )
        bconn.commit()
        bconn.close()

        # 1: corpus-only search returns corpus results
        r = search("observer pattern", corpus_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if not r["results"]:
            failures.append("corpus-only search returned no results")
        elif r["results"][0]["source_db"] != "corpus":
            failures.append("corpus-only result has wrong source_db")

        # 2: books-only search returns books results
        r = search("meaningful names", books_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if not r["results"]:
            failures.append("books-only search returned no results")
        elif r["results"][0]["source_db"] != "books":
            failures.append("books-only result has wrong source_db")

        # 3: unified search returns results from both
        r = search("method", db_path=corpus_db, books_db_path=books_db)
        checks += 1
        dbs = {hit["source_db"] for hit in r["results"]}
        if dbs != {"corpus", "books"}:
            failures.append(f"unified search dbs = {dbs}, expected both")

        # 4: databases field lists which DBs were queried
        checks += 1
        if sorted(r["databases"]) != ["books", "corpus"]:
            failures.append(f"databases = {r['databases']}, expected both")

        # 5: kind filter restricts corpus results
        r = search("search binary quicksort", kind="code",
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        corpus_hits = [h for h in r["results"] if h["source_db"] == "corpus"]
        if corpus_hits and any(h["kind"] != "code" for h in corpus_hits):
            failures.append("kind filter did not restrict corpus results")

        # 6: empty query returns empty results
        r = search("", db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if r["results"]:
            failures.append("empty query should return empty results")

        # 7: top_k limits total results
        r = search("the", top_k=2,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if len(r["results"]) > 2:
            failures.append(f"top_k=2 but got {len(r['results'])} results")

        # 8: snippet length is respected
        r = search("observer", snippet_len=20,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        for hit in r["results"]:
            if hit["source_db"] == "corpus" and len(hit["snippet"]) > 20:
                failures.append(f"snippet len {len(hit['snippet'])} > 20")
                break

        # 9: result shape has required fields
        r = search("quicksort", db_path=corpus_db, books_db_path=books_db)
        checks += 1
        required = {"source_db", "id", "snippet", "kind", "uri", "title"}
        for hit in r["results"]:
            missing = required - set(hit.keys())
            if missing:
                failures.append(f"result missing fields: {missing}")
                break

        # 10: graceful when corpus DB missing
        r = search("observer", db_path=tmpdir / "no.db",
                    books_db_path=books_db)
        checks += 1
        if "books" not in r["databases"]:
            failures.append("missing corpus DB should still search books")

        # 11: graceful when books DB missing
        r = search("quicksort", db_path=corpus_db,
                    books_db_path=tmpdir / "no.db")
        checks += 1
        if "corpus" not in r["databases"]:
            failures.append("missing books DB should still search corpus")

        # 12: graceful when both DBs missing
        r = search("anything", db_path=tmpdir / "no.db",
                    books_db_path=tmpdir / "no2.db")
        checks += 1
        if r["results"]:
            failures.append("both DBs missing should return empty results")

        # 13: books result has title derived from filename
        r = search("meaningful names", books_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if r["results"] and r["results"][0]["title"] != "clean code":
            failures.append(
                f"books title = {r['results'][0]['title']!r}, "
                f"expected 'clean code'"
            )

        # 14: corpus result has source title from DB
        r = search("observer pattern", corpus_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if r["results"] and r["results"][0]["title"] != "Design Patterns":
            failures.append(
                f"corpus title = {r['results'][0]['title']!r}, "
                f"expected 'Design Patterns'"
            )

        # 15: total field matches result count
        r = search("quicksort", db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if r["total"] != len(r["results"]):
            failures.append(
                f"total={r['total']} != len(results)={len(r['results'])}"
            )

        # 16: corpus_only excludes books
        r = search("names code", corpus_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if any(h["source_db"] == "books" for h in r["results"]):
            failures.append("corpus_only should exclude books results")

        # 17: books_only excludes corpus
        r = search("observer quicksort", books_only=True,
                    db_path=corpus_db, books_db_path=books_db)
        checks += 1
        if any(h["source_db"] == "corpus" for h in r["results"]):
            failures.append("books_only should exclude corpus results")

        # 18: JSON output is valid
        r = search("factory", db_path=corpus_db, books_db_path=books_db)
        checks += 1
        try:
            json.dumps(r)
        except (TypeError, ValueError) as e:
            failures.append(f"result not JSON-serializable: {e}")

    for f in failures:
        print(f"FAIL {f}")
    if not failures:
        print(f"PASS search selftest ({checks} checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")

    p_q = sub.add_parser("query", help="Search across corpus and books")
    p_q.add_argument("text", nargs="+")
    p_q.add_argument("--k", type=int, default=20)
    p_q.add_argument("--json", action="store_true", dest="as_json")
    p_q.add_argument("--corpus-only", action="store_true")
    p_q.add_argument("--books-only", action="store_true")
    p_q.add_argument("--snippet", type=int, default=SNIPPET_LEN)
    p_q.add_argument("--kind", default=None)
    p_q.add_argument("--db", default=None)
    p_q.add_argument("--books-db", default=None, dest="books_db")

    sub.add_parser("selftest", help="Run self-tests")

    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()

    if args.command is None:
        parser.print_help()
        return 1

    query_text = " ".join(args.text)
    result = search(
        query_text,
        top_k=args.k,
        corpus_only=args.corpus_only,
        books_only=args.books_only,
        kind=args.kind,
        snippet_len=args.snippet,
        db_path=args.db,
        books_db_path=args.books_db,
    )

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        if not result["results"]:
            print("  no results")
        else:
            for i, hit in enumerate(result["results"], 1):
                db_tag = f"[{hit['source_db']}]"
                kind_tag = hit["kind"]
                print(f"  {i:2d}. {db_tag:8s} {kind_tag:8s} {hit['title']}")
                print(f"      {hit['snippet'][:100]}")
                print()
        dbs = ", ".join(result["databases"]) or "none"
        print(f"  {result['total']} result(s) from: {dbs}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
