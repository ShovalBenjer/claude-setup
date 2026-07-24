"""Tests for `intent retrieve`, the ~/docs-to-contract retrieval surface."""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from intent_control_plane import cli


def _corpus(db) -> None:
    conn = sqlite3.connect(db)
    conn.execute("create table chunks (id integer primary key, source_id text, locator text, text text)")
    conn.execute("create virtual table corpus_fts using fts5(chunk_id unindexed, title, locator, text)")
    rows = [
        (1, "local-shoval-docs", "/home/shovalbe/docs/Harness.md",
         "Harness engineering wraps the agent with sensors and verification."),
        (2, "other-source", "/x/Other.md", "harness content the source_id filter must exclude."),
    ]
    for rid, src, loc, txt in rows:
        conn.execute("insert into chunks values (?, ?, ?, ?)", (rid, src, loc, txt))
        conn.execute("insert into corpus_fts values (?, ?, ?, ?)", (rid, loc.split("/")[-1], loc, txt))
    conn.commit()
    conn.close()


def test_retrieve_returns_path_and_content(tmp_path):
    db = tmp_path / "corpus.sqlite3"
    _corpus(db)
    out = cli.retrieve(SimpleNamespace(query="harness verification", k=3, db=str(db)))
    assert out["count"] == 1  # Other.md excluded by source_id
    hit = out["hits"][0]
    assert hit["name"] == "Harness.md"
    assert hit["path"] == "/home/shovalbe/docs/Harness.md"
    assert "harness" in hit["snippet"].lower()


def test_retrieve_fails_closed_on_missing_db(tmp_path):
    out = cli.retrieve(SimpleNamespace(query="anything", k=3, db=str(tmp_path / "nope.sqlite3")))
    assert out == {"query": "anything", "count": 0, "hits": []}
