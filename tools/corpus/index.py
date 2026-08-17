#!/usr/bin/env python
"""Searchable index over every session transcript: full JSON turns, FTS5 recall.

Purpose. tools/corpus/extract.py flattens transcripts into deduped text for
embedding elsewhere; this keeps every turn WITH its provenance and its entire
source event JSON, in one sqlite database with an FTS5 index, so a session (or
the operator) can retrieve "what did we say about X, where, and when" without
re-walking 800MB of JSONL. It is the retrieval half of the memory system; the
capture half is tools/intent (prompt tickets) and the cleaning rules live in
extract.py and are imported, not copied.

Contracts. The database lives OUTSIDE the repo by default (~/.claude/rag/) and
must never be committed: turns carry prompts, tool decisions, and PII. Ingest
is incremental per file keyed on (mtime, size); a changed file is re-read whole
because transcripts are append-only and cheap to re-parse relative to being
wrong about offsets. Tool results and attachments are excluded, same grounds as
extract.py: they are file contents and cloud scans, not conversation.

Typical usage:
  python tools/corpus/index.py build
  python tools/corpus/index.py build --root /mnt/c/Users/shova/.claude/projects
  python tools/corpus/index.py search "gate fingerprint" --limit 5
  python tools/corpus/index.py search "kitty" --role user --json
  python tools/corpus/index.py stats
  python tools/corpus/index.py selftest
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import DEFAULT_ROOT, admits, iter_events, text_of, turn_text  # noqa: E402

DEFAULT_DB = Path.home() / ".claude" / "rag" / "corpus.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, mtime REAL NOT NULL, size INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS turns(
    id INTEGER PRIMARY KEY, path TEXT NOT NULL, project TEXT NOT NULL,
    session TEXT NOT NULL, ts TEXT NOT NULL, role TEXT NOT NULL,
    text TEXT NOT NULL, event TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS turns_path ON turns(path);
CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
    text, content='turns', content_rowid='id');
"""


def connect(db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the index database with its schema applied."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def ingest_file(conn: sqlite3.Connection, path: Path, project: str) -> int:
    """(Re)index one transcript file, replacing any rows it wrote before."""
    old = conn.execute("SELECT id FROM turns WHERE path=?", (str(path),)).fetchall()
    if old:
        conn.executemany("INSERT INTO turns_fts(turns_fts, rowid, text) "
                         "SELECT 'delete', id, text FROM turns WHERE id=?", old)
        conn.execute("DELETE FROM turns WHERE path=?", (str(path),))
    tally = {"noise": 0, "empty": 0, "tool_result": 0, "attachment": 0,
             "command_unwrapped": 0}
    n = 0
    for event in iter_events(path):
        if not admits(event, False, tally):
            continue
        text = turn_text(text_of(event.get("message") or {}), tally)
        if not text:
            continue
        cur = conn.execute(
            "INSERT INTO turns(path, project, session, ts, role, text, event) "
            "VALUES(?,?,?,?,?,?,?)",
            (str(path), project, event.get("sessionId", ""),
             (event.get("timestamp") or "")[:19], event.get("type", ""),
             text, json.dumps(event, ensure_ascii=False)))
        conn.execute("INSERT INTO turns_fts(rowid, text) VALUES(?,?)",
                     (cur.lastrowid, text))
        n += 1
    try:
        stat = path.stat()
    except OSError:
        return n  # vanished mid-read; no files row, so the next build re-checks
    conn.execute("INSERT OR REPLACE INTO files(path, mtime, size) VALUES(?,?,?)",
                 (str(path), stat.st_mtime, stat.st_size))
    return n


def build(db_path: Path, roots: list[Path]) -> dict:
    """Incrementally index every top-level transcript under each root."""
    conn = connect(db_path)
    seen = {row[0]: (row[1], row[2])
            for row in conn.execute("SELECT path, mtime, size FROM files")}
    changed = unchanged = turns = 0
    for root in roots:
        for path in sorted(root.glob("*/*.jsonl")):
            try:
                stat = path.stat()
            except OSError:
                continue  # deleted between glob and stat; a live corpus does this
            if seen.get(str(path)) == (stat.st_mtime, stat.st_size):
                unchanged += 1
                continue
            turns += ingest_file(conn, path, path.parent.name)
            changed += 1
    conn.commit()
    total = conn.execute("SELECT count(*) FROM turns").fetchone()[0]
    conn.close()
    return {"files_indexed": changed, "files_unchanged": unchanged,
            "turns_added": turns, "turns_total": total}


def fts_quote(query: str) -> str:
    """Quote each term so operator prose is never parsed as FTS5 syntax."""
    return " ".join('"{}"'.format(t.replace('"', '""')) for t in query.split())


def search(db_path: Path, query: str, role: str | None, project: str | None,
           limit: int) -> list[dict]:
    """Rank matching turns by bm25 and return them with provenance."""
    conn = connect(db_path)
    sql = ("SELECT t.project, t.session, t.ts, t.role, t.text, t.event "
           "FROM turns_fts f JOIN turns t ON t.id = f.rowid "
           "WHERE turns_fts MATCH ?")
    args: list = [fts_quote(query)]
    if role:
        sql += " AND t.role=?"
        args.append(role)
    if project:
        sql += " AND t.project LIKE ?"
        args.append("%" + project + "%")
    sql += " ORDER BY bm25(turns_fts) LIMIT ?"
    args.append(limit)
    rows = [{"project": p, "session": s, "ts": ts, "role": r,
             "text": txt, "event": ev}
            for p, s, ts, r, txt, ev in conn.execute(sql, args)]
    conn.close()
    return rows


def cmd_build(args) -> int:
    roots = [Path(r) for r in (args.root or [str(DEFAULT_ROOT)])]
    report = build(Path(args.db), roots)
    print(json.dumps(report))
    return 0


def cmd_search(args) -> int:
    rows = search(Path(args.db), args.query, args.role, args.project, args.limit)
    for row in rows:
        if args.json:
            print(row["event"])
        else:
            head = row["text"][:200].replace("\n", " ")
            print("{ts}  {role:9s}  {project}\n  {head}\n".format(
                ts=row["ts"], role=row["role"],
                project=row["project"], head=head))
    if not rows:
        print("no matches", file=sys.stderr)
    return 0


def cmd_stats(args) -> int:
    conn = connect(Path(args.db))
    files, turns = (conn.execute("SELECT count(*) FROM files").fetchone()[0],
                    conn.execute("SELECT count(*) FROM turns").fetchone()[0])
    print("db      {}".format(args.db))
    print("files   {}".format(files))
    print("turns   {}".format(turns))
    for proj, n in conn.execute(
            "SELECT project, count(*) FROM turns GROUP BY project "
            "ORDER BY count(*) DESC LIMIT 15"):
        print("  {:6d}  {}".format(n, proj))
    for month, n in conn.execute(
            "SELECT substr(ts,1,7), count(*) FROM turns WHERE ts!='' "
            "GROUP BY 1 ORDER BY 1"):
        print("  {}  {}".format(month, n))
    conn.close()
    return 0


def selftest_checks(tmp: Path) -> list[tuple[str, bool]]:
    """Build a fixture corpus, index it twice, and check every contract."""
    root = tmp / "projects"
    (root / "proj-one").mkdir(parents=True)
    events = [
        {"type": "user", "sessionId": "s1", "timestamp": "2026-08-12T10:00:00Z",
         "message": {"content": "the gate fingerprint invalidates itself"}},
        {"type": "assistant", "sessionId": "s1",
         "timestamp": "2026-08-12T10:00:05Z",
         "message": {"content": [{"type": "text", "text": "an answer about kitty"}]}},
        {"type": "user", "sessionId": "s1",
         "message": {"content": [{"type": "tool_result", "content": "x"}]}},
    ]
    f = root / "proj-one" / "a.jsonl"
    f.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    db = tmp / "corpus.db"
    first = build(db, [root])
    second = build(db, [root])
    f.write_text(f.read_text(encoding="utf-8") + json.dumps(
        {"type": "user", "sessionId": "s1", "timestamp": "2026-08-12T11:00:00Z",
         "message": {"content": "a later gate question"}}) + "\n",
        encoding="utf-8")
    third = build(db, [root])
    hits = search(db, "gate fingerprint", None, None, 10)
    quoted = search(db, 'gate "fingerprint', None, None, 10)
    role_only = search(db, "gate", "assistant", None, 10)
    ev = json.loads(hits[0]["event"]) if hits else {}
    return [
        ("first build indexed both turns", first["turns_added"] == 2),
        ("tool_result excluded", first["turns_total"] == 2),
        ("second build touches nothing",
         second["files_indexed"] == 0 and second["turns_added"] == 0),
        ("appended file re-indexed without duplicates",
         third["turns_total"] == 3),
        ("search finds the turn", len(hits) == 1),
        ("full event JSON round-trips",
         ev.get("message", {}).get("content", "").startswith("the gate")),
        ("provenance carried",
         hits and hits[0]["project"] == "proj-one" and hits[0]["session"] == "s1"),
        ("unbalanced quote does not raise", isinstance(quoted, list)),
        ("role filter narrows", all(r["role"] == "assistant" for r in role_only)
         and len(role_only) == 0),
    ]


def cmd_selftest(_args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        checks = selftest_checks(Path(tmp))
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("{:8s} {}".format("ok" if ok else "FAIL", name))
    print("selftest: {} checks, {} failed".format(len(checks), len(failed)))
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--root", action="append",
                   help="transcript root; repeatable (default ~/.claude/projects)")
    b.set_defaults(fn=cmd_build)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--role", choices=["user", "assistant"])
    s.add_argument("--project")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true",
                   help="print the full source event JSON per hit")
    s.set_defaults(fn=cmd_search)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
