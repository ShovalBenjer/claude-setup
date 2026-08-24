#!/usr/bin/env python3
"""Build a local best-practices corpus for Claude/Gastown routing.

ponytail: SQLite FTS is enough until searches prove it is not.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import sqlite3
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path.home() / ".claude" / "corpus"
SOURCES_PATH = ROOT / "sources.json"
DB_PATH = ROOT / "best_practices.sqlite3"
USER_AGENT = "Shoval-Gastown-Corpus/2026-06-15"


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer"}:
            self._skip += 1
        if tag in {"h1", "h2", "h3", "p", "li", "td", "th", "pre", "code"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer"} and self._skip:
            self._skip -= 1
        if tag in {"h1", "h2", "h3", "p", "li", "tr", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.parts)).strip()


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    license: str
    allowed_use: str
    freshness: str
    url: str | None = None
    path: str | None = None


def load_sources(path: Path) -> list[Source]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Source(**item) for item in raw]


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        content_type = resp.headers.get("content-type", "")
    text = data.decode("utf-8", errors="replace")
    if "html" in content_type or "<html" in text[:1000].lower():
        parser = TextExtractor()
        parser.feed(text)
        return parser.text()
    return text


def read_local_docs(root: Path) -> Iterable[tuple[str, str]]:
    patterns = ("*.md", "*.txt")
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            if path.stat().st_size > 1_500_000:
                continue
            try:
                yield str(path), path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue


def chunks(text: str, size: int = 2200, overlap: int = 250) -> Iterable[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        yield text[start:end].strip()
        if end == len(text):
            break
        start = max(0, end - overlap)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        drop table if exists sources;
        drop table if exists chunks;
        drop table if exists corpus_fts;

        create table sources (
          id text primary key,
          title text not null,
          locator text not null,
          license text not null,
          allowed_use text not null,
          freshness text not null,
          retrieved_at text not null default (datetime('now'))
        );

        create table chunks (
          id text primary key,
          source_id text not null references sources(id),
          locator text not null,
          chunk_index integer not null,
          text text not null,
          sha256 text not null
        );

        create virtual table corpus_fts using fts5(
          chunk_id unindexed,
          title,
          locator,
          text
        );
        """
    )
    return conn


def add_source(conn: sqlite3.Connection, source: Source, locator: str, docs: Iterable[tuple[str, str]]) -> int:
    conn.execute(
        "insert into sources(id, title, locator, license, allowed_use, freshness) values (?, ?, ?, ?, ?, ?)",
        (source.id, source.title, locator, source.license, source.allowed_use, source.freshness),
    )
    count = 0
    for doc_locator, text in docs:
        for idx, chunk in enumerate(chunks(text)):
            digest = hashlib.sha256(f"{source.id}:{doc_locator}:{idx}:{chunk}".encode()).hexdigest()
            chunk_id = digest[:24]
            conn.execute(
                "insert into chunks(id, source_id, locator, chunk_index, text, sha256) values (?, ?, ?, ?, ?, ?)",
                (chunk_id, source.id, doc_locator, idx, chunk, digest),
            )
            conn.execute(
                "insert into corpus_fts(chunk_id, title, locator, text) values (?, ?, ?, ?)",
                (chunk_id, source.title, doc_locator, chunk),
            )
            count += 1
    return count


def build(local_only: bool = False) -> int:
    sources = load_sources(SOURCES_PATH)
    conn = init_db(DB_PATH)
    totals: dict[str, int] = {}
    try:
        for source in sources:
            try:
                if source.url:
                    if local_only:
                        continue
                    text = fetch_url(source.url)
                    totals[source.id] = add_source(conn, source, source.url, [(source.url, text)])
                elif source.path:
                    root = Path(source.path)
                    totals[source.id] = add_source(conn, source, str(root), read_local_docs(root))
            except Exception as exc:  # a dead URL or unreadable dir must not abort the whole build
                print(f"skip {source.id}: {type(exc).__name__}: {exc}", file=sys.stderr)
        conn.commit()
    finally:
        conn.close()
    print(json.dumps({"db": str(DB_PATH), "sources": len(sources), "chunks": totals, "local_only": local_only}, indent=2))
    return 0


def query(term: str, limit: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            select s.id, s.title, c.locator, snippet(corpus_fts, 3, '[', ']', '...', 18)
            from corpus_fts
            join chunks c on c.id = corpus_fts.chunk_id
            join sources s on s.id = c.source_id
            where corpus_fts match ?
            limit ?
            """,
            (term, limit),
        ).fetchall()
    finally:
        conn.close()
    for row in rows:
        print(json.dumps({"source": row[0], "title": row[1], "locator": row[2], "snippet": row[3]}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--local-only", action="store_true",
                   help="index only local path sources (offline, fast, for auto-refresh)")
    q = sub.add_parser("query")
    q.add_argument("term")
    q.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.cmd == "build":
        return build(local_only=args.local_only)
    return query(args.term, args.limit)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
