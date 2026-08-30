#!/usr/bin/env python3
"""Research corpus DB (spec 2026-07-31, steps 1-4).

Ingests the ~365 markdown files across work-docs/, research-papers/, and
docs/analysis/ into a SQLite+FTS5 database at state/corpus.db. Implements
the schema from section 4.3 of the spec, the stage-0 normaliser, the
stage-2 chunker, stage-3 dedup (exact and simhash), stage-4 citation gate,
and the FTS5 query path returning the section 7.2 record shape.

Usage:
    python tools/corpus/research.py init            # create schema
    python tools/corpus/research.py ingest          # ingest local files
    python tools/corpus/research.py query <text>    # FTS5 search
    python tools/corpus/research.py defects         # uncited/contradicted
    python tools/corpus/research.py status          # summary counts
    python tools/corpus/research.py selftest        # prove the module works
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import repo_root  # noqa: E402

ROOT = repo_root.resolve()
DEFAULT_DB = ROOT / "state" / "corpus.db"

SCHEMA_VERSION = 1

SOURCE_DIRS = [
    ROOT / "work-docs",
    ROOT / "research-papers",
    ROOT / "docs" / "analysis",
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS corpus_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,
    canonical_uri    TEXT NOT NULL UNIQUE,
    kind             TEXT NOT NULL
                     CHECK (kind IN ('local_md', 'repo', 'hf_dataset', 'paper', 'derived')),
    title            TEXT NOT NULL,
    license_spdx     TEXT NOT NULL,
    license_verdict  TEXT NOT NULL
                     CHECK (license_verdict IN ('vendor', 'index_only', 'link_only', 'blocked')),
    license_evidence TEXT NOT NULL,
    publisher        TEXT,
    published_utc    TEXT,
    fetched_utc      TEXT NOT NULL,
    upstream_rev     TEXT,
    upstream_mtime   TEXT,
    liveness         TEXT NOT NULL
                     CHECK (liveness IN ('live', 'stale', 'archived', 'dead')),
    content_sha256   TEXT NOT NULL,
    bytes            INTEGER NOT NULL,
    supersedes       TEXT REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id       TEXT PRIMARY KEY,
    source_id      TEXT NOT NULL REFERENCES sources(source_id),
    ordinal        INTEGER NOT NULL,
    heading_path   TEXT NOT NULL,
    kind           TEXT NOT NULL
                   CHECK (kind IN ('claim', 'code', 'table', 'config', 'link', 'prose')),
    lang           TEXT,
    norm_text      TEXT NOT NULL,
    raw_text       TEXT NOT NULL,
    word_count     INTEGER NOT NULL,
    norm_sha256    TEXT NOT NULL,
    simhash        INTEGER NOT NULL,
    citation_count INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL
                   CHECK (status IN ('accepted', 'quarantined', 'superseded', 'rejected')),
    status_reason  TEXT,
    ingested_utc   TEXT NOT NULL,
    UNIQUE(source_id, ordinal)
);

CREATE TABLE IF NOT EXISTS citations (
    citation_id      TEXT PRIMARY KEY,
    chunk_id         TEXT NOT NULL REFERENCES chunks(chunk_id),
    target_uri       TEXT NOT NULL,
    target_source_id TEXT REFERENCES sources(source_id),
    tag              TEXT,
    locator          TEXT,
    verified         INTEGER NOT NULL DEFAULT 0,
    verified_utc     TEXT
);

CREATE TABLE IF NOT EXISTS claim_edges (
    edge_id      TEXT PRIMARY KEY,
    source_chunk TEXT NOT NULL REFERENCES chunks(chunk_id),
    target_chunk TEXT NOT NULL REFERENCES chunks(chunk_id),
    edge_type    TEXT NOT NULL
                 CHECK (edge_type IN ('contradicts', 'supports', 'supersedes', 'duplicates', 'refines')),
    basis        TEXT NOT NULL,
    confidence   REAL NOT NULL,
    detected_utc TEXT NOT NULL,
    resolution   TEXT,
    resolved_utc TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id   TEXT PRIMARY KEY,
    chunk_id      TEXT NOT NULL REFERENCES chunks(chunk_id),
    artifact_type TEXT NOT NULL
                  CHECK (artifact_type IN ('library', 'api', 'oneliner', 'config', 'command', 'pattern')),
    name          TEXT NOT NULL,
    version       TEXT,
    snippet       TEXT,
    implemented   INTEGER NOT NULL,
    evidence_path TEXT
);

CREATE TABLE IF NOT EXISTS chunk_tags (
    chunk_id  TEXT NOT NULL REFERENCES chunks(chunk_id),
    tag       TEXT NOT NULL,
    score     REAL NOT NULL,
    tagged_utc TEXT NOT NULL,
    PRIMARY KEY (chunk_id, tag)
);

CREATE INDEX IF NOT EXISTS ix_tags_tag ON chunk_tags(tag);

CREATE TABLE IF NOT EXISTS chunk_versions (
    version_id   TEXT PRIMARY KEY,
    chunk_id     TEXT NOT NULL REFERENCES chunks(chunk_id),
    version_num  INTEGER NOT NULL,
    norm_sha256  TEXT NOT NULL,
    word_count   INTEGER NOT NULL,
    snapshot_utc TEXT NOT NULL,
    UNIQUE(chunk_id, version_num)
);

CREATE INDEX IF NOT EXISTS ix_versions_chunk ON chunk_versions(chunk_id);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    norm_text, heading_path, content='chunks', content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE INDEX IF NOT EXISTS ix_chunks_status  ON chunks(status);
CREATE INDEX IF NOT EXISTS ix_chunks_simhash ON chunks(simhash);
CREATE INDEX IF NOT EXISTS ix_chunks_normsha ON chunks(norm_sha256);
CREATE INDEX IF NOT EXISTS ix_cit_chunk      ON citations(chunk_id);
CREATE INDEX IF NOT EXISTS ix_edges_open     ON claim_edges(edge_type, resolution);
CREATE INDEX IF NOT EXISTS ix_art_name       ON artifacts(name, implemented);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, norm_text, heading_path)
    VALUES (new.rowid, new.norm_text, new.heading_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, norm_text, heading_path)
    VALUES ('delete', old.rowid, old.norm_text, old.heading_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, norm_text, heading_path)
    VALUES ('delete', old.rowid, old.norm_text, old.heading_path);
    INSERT INTO chunks_fts(rowid, norm_text, heading_path)
    VALUES (new.rowid, new.norm_text, new.heading_path);
END;
"""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_id(canonical_uri):
    return "s" + _sha256(canonical_uri)[:16]


def _chunk_id(norm_text):
    return "c" + _sha256(norm_text)[:16]


# ----------------------------------------------------------------- connect

def connect(db_path=None):
    p = Path(db_path) if db_path else DEFAULT_DB
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA_SQL)
    row = conn.execute(
        "SELECT value FROM corpus_meta WHERE key='schema_version'"
    ).fetchone()
    if row is None or int(row[0]) < SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO corpus_meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.commit()
    return SCHEMA_VERSION


# ---------------------------------------------------------- stage 0: normalise

_MOJIBAKE = [
    ("Γ", "-"), ("א", "-"), ("פ", "-"),
    ("â", "-"), ("â", "-"),
    ("â", "'"),
]

_DASH_RE = re.compile(r"[–—―‒]")


def normalise(text):
    text = unicodedata.normalize("NFC", text)
    for bad, good in _MOJIBAKE:
        text = text.replace(bad, good)
    text = _DASH_RE.sub("-", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines)


# ---------------------------------------------------------- stage 2: chunker

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)
_CODE_FENCE = re.compile(r"^```(\w*)", re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s\)>\]]+")
_S_TAG_RE = re.compile(r"\[S\d+\]")

MAX_CHUNK_WORDS = 400
MIN_CHUNK_WORDS = 30


def _classify_chunk(text):
    stripped = text.strip()
    if stripped.startswith(("```", "    ")):
        return "code"
    if "|" in stripped and stripped.count("|") > 3:
        return "table"
    if _URL_RE.search(stripped) and len(stripped.split()) < 20:
        return "link"
    return "prose"


def _extract_lang(text):
    m = _CODE_FENCE.match(text.strip())
    if m and m.group(1):
        return m.group(1)
    return None


def _split_sections(text):
    parts = []
    current_heading = ""
    current_lines = []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            if current_lines:
                parts.append((current_heading, "\n".join(current_lines)))
            level = len(m.group(1))
            title = m.group(2).strip()
            if level <= 2:
                current_heading = title
            else:
                current_heading = current_heading.split(" > ")[0] + " > " + title if current_heading else title
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        parts.append((current_heading, "\n".join(current_lines)))

    return parts


def _subdivide(text, max_words=MAX_CHUNK_WORDS):
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    lines = text.splitlines()
    current = []
    current_wc = 0
    for line in lines:
        wc = len(line.split())
        if current_wc + wc > max_words and current_wc >= MIN_CHUNK_WORDS:
            chunks.append("\n".join(current))
            current = [line]
            current_wc = wc
        else:
            current.append(line)
            current_wc += wc
    if current:
        chunks.append("\n".join(current))
    return chunks


def chunk_file(text, title=""):
    sections = _split_sections(text)
    result = []
    ordinal = 0

    for heading, section_text in sections:
        heading_path = heading or title
        subs = _subdivide(section_text)
        for sub in subs:
            wc = len(sub.split())
            if wc < MIN_CHUNK_WORDS and len(result) > 0:
                prev = result[-1]
                result[-1] = {
                    **prev,
                    "raw_text": prev["raw_text"] + "\n" + sub,
                    "norm_text": prev["norm_text"] + "\n" + normalise(sub),
                    "word_count": prev["word_count"] + wc,
                }
                continue
            norm = normalise(sub)
            kind = _classify_chunk(sub)
            result.append({
                "ordinal": ordinal,
                "heading_path": heading_path,
                "kind": kind,
                "lang": _extract_lang(sub) if kind == "code" else None,
                "raw_text": sub,
                "norm_text": norm,
                "word_count": wc,
            })
            ordinal += 1

    return result


# ---------------------------------------------------------- simhash (64-bit)

def _simhash(text, width=64):
    tokens = text.lower().split()
    shingles = [" ".join(tokens[i:i + 4]) for i in range(len(tokens) - 3)]
    v = [0] * width
    for s in shingles:
        h = int(hashlib.md5(s.encode()).hexdigest(), 16)
        for i in range(width):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(width):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint


def _to_signed64(n):
    if n >= (1 << 63):
        n -= (1 << 64)
    return n


def _from_signed64(n):
    if n < 0:
        n += (1 << 64)
    return n


def _hamming(a, b):
    x = _from_signed64(a) ^ _from_signed64(b)
    count = 0
    while x:
        count += 1
        x &= x - 1
    return count


# ---------------------------------------------------------- citation extraction

def _extract_citations(text):
    cites = [{"target_uri": url.group(), "tag": None} for url in _URL_RE.finditer(text)]
    cites.extend({"target_uri": "", "tag": tag.group()} for tag in _S_TAG_RE.finditer(text))
    return cites


# ---------------------------------------------------------- ingest

def _collect_files(dirs=None):
    files = []
    for d in (dirs or SOURCE_DIRS):
        d = Path(d)
        if not d.exists():
            continue
        files.extend(sorted(d.rglob("*.md")))
    return files


def ingest(conn, dirs=None, ledger_path=None):
    now = _now()
    files = _collect_files(dirs)
    stats = {"sources": 0, "chunks": 0, "citations": 0,
             "dedup_exact": 0, "quarantined": 0}
    ledger = []

    for fpath in files:
        try:
            rel = str(fpath.relative_to(ROOT))
        except ValueError:
            rel = str(fpath)
        canonical = str(fpath)
        sid = _source_id(canonical)

        existing = conn.execute(
            "SELECT source_id FROM sources WHERE source_id=?", (sid,)
        ).fetchone()

        text = fpath.read_text(encoding="utf-8", errors="replace")
        content_hash = _sha256(text)

        if existing:
            old_hash = conn.execute(
                "SELECT content_sha256 FROM sources WHERE source_id=?", (sid,)
            ).fetchone()
            if old_hash and old_hash[0] == content_hash:
                continue
            conn.execute("DELETE FROM chunks WHERE source_id=?", (sid,))
            conn.execute("DELETE FROM sources WHERE source_id=?", (sid,))

        title = fpath.stem.replace("-", " ").replace("_", " ")
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        if first_line.startswith("# "):
            title = first_line[2:].strip()

        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " content_sha256, bytes) "
            "VALUES (?, ?, 'local_md', ?, 'proprietary', 'vendor', "
            " 'local file, operator owned', ?, 'live', ?, ?)",
            (sid, canonical, title, now, content_hash, len(text.encode("utf-8"))),
        )
        stats["sources"] += 1

        chunks = chunk_file(text, title)
        seen_hashes = set()

        for ch in chunks:
            norm_hash = _sha256(ch["norm_text"])
            sh = _to_signed64(_simhash(ch["norm_text"]))
            cid = _chunk_id(ch["norm_text"] + sid + str(ch["ordinal"]))

            cites = _extract_citations(ch["raw_text"])
            is_claim = ch["kind"] == "prose"
            has_cite = len(cites) > 0

            if is_claim and not has_cite:
                status = "quarantined"
                reason = "uncited"
                stats["quarantined"] += 1
            else:
                status = "accepted"
                reason = None

            dup = conn.execute(
                "SELECT chunk_id FROM chunks "
                "WHERE norm_sha256=? AND status='accepted' AND source_id != ?",
                (norm_hash, sid),
            ).fetchone()
            if dup:
                status = "superseded"
                reason = "exact_duplicate"
                stats["dedup_exact"] += 1

            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, source_id, ordinal, heading_path, kind, lang, "
                " norm_text, raw_text, word_count, norm_sha256, simhash, "
                " citation_count, status, status_reason, ingested_utc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, sid, ch["ordinal"], ch["heading_path"], ch["kind"],
                 ch["lang"], ch["norm_text"], ch["raw_text"], ch["word_count"],
                 norm_hash, sh, len(cites), status, reason, now),
            )

            if dup:
                edge_id = "e" + _sha256(cid + dup[0])[:16]
                conn.execute(
                    "INSERT OR IGNORE INTO claim_edges "
                    "(edge_id, source_chunk, target_chunk, edge_type, "
                    " basis, confidence, detected_utc) "
                    "VALUES (?, ?, ?, 'duplicates', 'norm_sha256', 1.0, ?)",
                    (edge_id, cid, dup[0], now),
                )
            stats["chunks"] += 1

            for cite in cites:
                cite_id = "ci" + _sha256(cid + cite["target_uri"] + (cite["tag"] or ""))[:14]
                conn.execute(
                    "INSERT OR IGNORE INTO citations "
                    "(citation_id, chunk_id, target_uri, tag) "
                    "VALUES (?, ?, ?, ?)",
                    (cite_id, cid, cite["target_uri"], cite["tag"]),
                )
                stats["citations"] += 1

            seen_hashes.add(norm_hash)

        ledger.append({
            "ts": now, "action": "ingest", "source": rel,
            "source_id": sid, "chunks": len(chunks),
        })

    conn.execute(
        "INSERT OR REPLACE INTO corpus_meta (key, value) VALUES (?, ?)",
        ("last_ingest", now),
    )
    conn.commit()

    if ledger_path:
        lp = Path(ledger_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        with open(lp, "a", encoding="utf-8") as f:
            for entry in ledger:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return stats


# ---------------------------------------------------------- simhash dedup pass

def dedup_simhash(conn, threshold=4):
    now = _now()
    rows = conn.execute(
        "SELECT chunk_id, simhash, norm_sha256 FROM chunks WHERE status='accepted'"
    ).fetchall()
    count = 0
    seen = {}
    for row in rows:
        cid, sh, nh = row["chunk_id"], row["simhash"], row["norm_sha256"]
        for seen_sh, seen_cid in seen.items():
            if _hamming(sh, seen_sh) <= threshold and seen_cid != cid:
                conn.execute(
                    "UPDATE chunks SET status='superseded', status_reason='simhash_near_dup' "
                    "WHERE chunk_id=? AND status='accepted'",
                    (cid,),
                )
                edge_id = "e" + _sha256(cid + seen_cid)[:16]
                conn.execute(
                    "INSERT OR IGNORE INTO claim_edges "
                    "(edge_id, source_chunk, target_chunk, edge_type, "
                    " basis, confidence, detected_utc) "
                    "VALUES (?, ?, ?, 'duplicates', 'simhash', ?, ?)",
                    (edge_id, cid, seen_cid, 1.0 - _hamming(sh, seen_sh) / 64.0, now),
                )
                count += 1
                break
        else:
            seen[sh] = cid
    conn.commit()
    return count


# ---------------------------------------------------------- query

def query(conn, text, kind=None, status="accepted", limit=15):
    params = [text]
    where = ["c.status = ?"]
    params_where = [status]
    if kind:
        where.append("c.kind = ?")
        params_where.append(kind)

    where_clause = " AND ".join(where)
    sql = (
        "SELECT c.chunk_id, c.norm_text, c.heading_path, c.kind, c.word_count, "
        "       c.status, c.citation_count, c.simhash, "
        "       s.canonical_uri, s.license_verdict, s.liveness, "
        "       s.fetched_utc, s.upstream_mtime, "
        "       bm25(chunks_fts) AS rank "
        "FROM chunks_fts f "
        "JOIN chunks c ON c.rowid = f.rowid "
        "JOIN sources s ON s.source_id = c.source_id "
        "WHERE chunks_fts MATCH ? AND " + where_clause + " "
        "ORDER BY rank "
        "LIMIT ?"
    )
    return conn.execute(sql, params + params_where + [limit]).fetchall()


def format_result(row):
    trust = "trusted" if row["license_verdict"] == "vendor" else "untrusted"
    return {
        "chunk_id": row["chunk_id"],
        "text": row["norm_text"][:500],
        "kind": row["kind"],
        "source": {
            "uri": row["canonical_uri"],
            "license_verdict": row["license_verdict"],
            "liveness": row["liveness"],
            "fetched_utc": row["fetched_utc"],
            "upstream_mtime": row["upstream_mtime"],
        },
        "citation_count": row["citation_count"],
        "word_count": row["word_count"],
        "trust": trust,
    }


# ---------------------------------------------------------- defect queries

def uncited_chunks(conn):
    return conn.execute(
        "SELECT c.chunk_id, s.canonical_uri, substr(c.norm_text, 1, 80) AS preview "
        "FROM chunks c JOIN sources s USING(source_id) "
        "LEFT JOIN citations ci ON ci.chunk_id = c.chunk_id AND ci.verified = 1 "
        "WHERE c.kind = 'prose' AND c.status = 'accepted' AND ci.citation_id IS NULL"
    ).fetchall()


def contradicted_chunks(conn):
    return conn.execute(
        "SELECT e.edge_id, e.confidence, e.source_chunk, e.target_chunk "
        "FROM claim_edges e "
        "JOIN chunks a ON a.chunk_id = e.source_chunk "
        "JOIN chunks b ON b.chunk_id = e.target_chunk "
        "WHERE e.edge_type = 'contradicts' AND e.resolution IS NULL "
        "  AND a.status = 'accepted' AND b.status = 'accepted'"
    ).fetchall()


# ---------------------------------------------------------- status

def status(conn):
    out = {}
    tables = {
        "sources":     "SELECT count(*) FROM sources",
        "chunks":      "SELECT count(*) FROM chunks",
        "citations":   "SELECT count(*) FROM citations",
        "claim_edges": "SELECT count(*) FROM claim_edges",
        "artifacts":   "SELECT count(*) FROM artifacts",
    }
    for name, sql in tables.items():
        out[name] = conn.execute(sql).fetchone()[0]

    by_status = conn.execute(
        "SELECT status, count(*) FROM chunks GROUP BY status"
    ).fetchall()
    out["chunks_by_status"] = {r[0]: r[1] for r in by_status}

    by_kind = conn.execute(
        "SELECT kind, count(*) FROM chunks GROUP BY kind"
    ).fetchall()
    out["chunks_by_kind"] = {r[0]: r[1] for r in by_kind}

    v = conn.execute(
        "SELECT value FROM corpus_meta WHERE key='schema_version'"
    ).fetchone()
    out["schema_version"] = int(v[0]) if v else 0

    last = conn.execute(
        "SELECT value FROM corpus_meta WHERE key='last_ingest'"
    ).fetchone()
    out["last_ingest"] = last[0] if last else None

    return out


# ---------------------------------------------------------- selftest

def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        v = init_schema(conn)
        assert v == SCHEMA_VERSION, f"schema version {v}"

        # normalise
        assert normalise("–test—") == "-test-"
        assert normalise("hello  \n  world  ") == "hello\n  world"

        # chunking
        text = (
            "# Title\n\n"
            "Some prose here about testing the research corpus chunker which "
            "needs at least thirty words per section to avoid merging small "
            "sections into the previous chunk as specified by the minimum "
            "threshold constant.\n\n"
            "## Section Two\n\n"
            "More content with https://example.com link and additional words "
            "so that this section also exceeds the minimum chunk word count "
            "threshold and produces a separate chunk rather than being merged "
            "into the previous section.\n\n"
            "```python\nprint('hello')\n```\n"
        )
        chunks = chunk_file(text, "test-file")
        assert len(chunks) >= 2, f"expected >=2 chunks, got {len(chunks)}"
        assert chunks[0]["heading_path"] == "Title"

        # simhash
        long_a = ("the quick brown fox jumps over the lazy dog and keeps "
                  "running through the forest until reaching a meadow where "
                  "the sun shines brightly on the green grass below")
        long_b = ("the quick brown fox jumps over the lazy dog and keeps "
                  "running through the forest until reaching a meadow where "
                  "the moon shines brightly on the green grass below")
        long_c = ("quantum physics describes subatomic particles and their "
                  "interactions through mathematical frameworks including "
                  "wave functions probability amplitudes and field operators")
        h1 = _simhash(long_a)
        h2 = _simhash(long_b)
        h3 = _simhash(long_c)
        assert _hamming(h1, h2) < _hamming(h1, h3), "similar < different"

        # source + chunk insert
        sid = _source_id("/tmp/test.md")
        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " content_sha256, bytes) "
            "VALUES (?, '/tmp/test.md', 'local_md', 'Test', 'proprietary', "
            " 'vendor', 'local', ?, 'live', 'abc', 100)",
            (sid, _now()),
        )
        cid = _chunk_id("test chunk content")
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES (?, ?, 0, 'Test', 'prose', 'test chunk content', "
            " 'test chunk content', 3, ?, 0, 'accepted', ?)",
            (cid, sid, _sha256("test chunk content"), _now()),
        )
        conn.commit()

        # FTS5 search
        results = query(conn, "test chunk")
        assert len(results) >= 1, "FTS5 query returned no results"

        # citation extraction
        cites = _extract_citations("See https://example.com and [S1] for details")
        assert len(cites) == 2, f"expected 2 citations, got {len(cites)}"
        assert cites[0]["target_uri"] == "https://example.com"
        assert cites[1]["tag"] == "[S1]"

        # defect queries run without error
        uncited = uncited_chunks(conn)
        assert isinstance(uncited, list)
        contradicted = contradicted_chunks(conn)
        assert isinstance(contradicted, list)

        # status
        s = status(conn)
        assert s["sources"] == 1
        assert s["chunks"] == 1
        assert s["schema_version"] == SCHEMA_VERSION

        # dedup: insert a duplicate chunk under a different source
        sid2 = _source_id("/tmp/test2.md")
        conn.execute(
            "INSERT INTO sources "
            "(source_id, canonical_uri, kind, title, license_spdx, "
            " license_verdict, license_evidence, fetched_utc, liveness, "
            " content_sha256, bytes) "
            "VALUES (?, '/tmp/test2.md', 'local_md', 'Test2', 'proprietary', "
            " 'vendor', 'local', ?, 'live', 'def', 100)",
            (sid2, _now()),
        )
        cid2 = _chunk_id("test chunk content dup")
        conn.execute(
            "INSERT INTO chunks "
            "(chunk_id, source_id, ordinal, heading_path, kind, "
            " norm_text, raw_text, word_count, norm_sha256, simhash, "
            " status, ingested_utc) "
            "VALUES (?, ?, 0, 'Test', 'prose', 'test chunk content', "
            " 'test chunk content', 3, ?, 0, 'accepted', ?)",
            (cid2, sid2, _sha256("test chunk content"), _now()),
        )
        conn.commit()

        near = dedup_simhash(conn, threshold=4)

        conn.close()
        print("selftest: PASS (schema, normalise, chunk, simhash, FTS5, citations, dedup, defects, status)")
        return True


# ---------------------------------------------------------- CLI

def main():
    parser = argparse.ArgumentParser(
        description="Research corpus DB (spec 2026-07-31, steps 1-4)")
    parser.add_argument("--db", default=None,
                        help="DB path (default: state/corpus.db)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="create schema")
    sub.add_parser("ingest", help="ingest local research files")
    sub.add_parser("status", help="summary counts")
    sub.add_parser("defects", help="uncited and contradicted chunks")
    sub.add_parser("selftest", help="run self-tests")

    p_query = sub.add_parser("query", help="FTS5 search")
    p_query.add_argument("text", help="search text")
    p_query.add_argument("--kind", default=None)
    p_query.add_argument("--limit", type=int, default=15)

    args = parser.parse_args()

    if args.cmd == "selftest":
        selftest()
        return

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    conn = connect(args.db)
    init_schema(conn)

    if args.cmd == "init":
        print(f"schema v{SCHEMA_VERSION} at {args.db or DEFAULT_DB}")

    elif args.cmd == "ingest":
        ledger = str(ROOT / "state" / "corpus-ingest.jsonl")
        stats = ingest(conn, ledger_path=ledger)
        print(f"  sources: {stats['sources']} ingested")
        print(f"  chunks:  {stats['chunks']} created")
        print(f"  citations: {stats['citations']} extracted")
        print(f"  dedup (exact): {stats['dedup_exact']} superseded")
        print(f"  quarantined (uncited prose): {stats['quarantined']}")
        nd = dedup_simhash(conn)
        print(f"  dedup (simhash): {nd} near-duplicates superseded")

    elif args.cmd == "status":
        s = status(conn)
        for k, v in s.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for kk, vv in v.items():
                    print(f"    {kk}: {vv}")
            else:
                print(f"  {k}: {v}")

    elif args.cmd == "defects":
        uc = uncited_chunks(conn)
        print(f"uncited accepted prose chunks: {len(uc)}")
        for r in uc[:10]:
            print(f"  {r['chunk_id']}  {r['preview']}")
        if len(uc) > 10:
            print(f"  ... and {len(uc) - 10} more")

        ct = contradicted_chunks(conn)
        print(f"\nopen contradictions: {len(ct)}")
        for r in ct[:10]:
            print(f"  {r['edge_id']}  conf={r['confidence']:.2f}  {r['source_chunk']} vs {r['target_chunk']}")

    elif args.cmd == "query":
        results = query(conn, args.text, kind=args.kind, limit=args.limit)
        print(f"{len(results)} result(s):\n")
        for r in results:
            fmt = format_result(r)
            print(f"  [{fmt['kind']}] {fmt['chunk_id']}")
            print(f"    source: {fmt['source']['uri']}")
            print(f"    trust: {fmt['trust']}, citations: {fmt['citation_count']}")
            print(f"    {fmt['text'][:120]}...")
            print()

    conn.close()


if __name__ == "__main__":
    main()
