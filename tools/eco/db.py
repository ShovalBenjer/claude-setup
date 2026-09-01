# -*- coding: utf-8 -*-
"""Ecosystem state DB (ADR-0011, AUTO-06).

ONE SQLite file as the system-of-record for operational state: sessions,
proposals, runs, lessons, reputation, post_queue, repo_registry. JSONL files
remain as append-only ingest logs that MIGRATE into the DB. Secrets and PII
never enter it (redaction gateway pattern from intent-control-plane).

Usage:
    python tools/eco/db.py init              # create/migrate schema
    python tools/eco/db.py migrate-jsonl     # ingest JSONL into tables
    python tools/eco/db.py claim <id> <lane> # claim a proposal for a lane
    python tools/eco/db.py log-run <kind> <repo> <outcome> [--pr <url>]
    python tools/eco/db.py status            # summary counts per table
    python tools/eco/db.py selftest          # prove the module works
"""
import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import repo_root  # noqa: E402

ROOT = repo_root.resolve()
DEFAULT_DB = ROOT / "state" / "ecosystem.db"

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version   INTEGER PRIMARY KEY,
    applied   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    lane       TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_seen  TEXT,
    charter    TEXT
);

CREATE TABLE IF NOT EXISTS proposals (
    id       TEXT PRIMARY KEY,
    source   TEXT,
    repo     TEXT,
    title    TEXT NOT NULL,
    kind     TEXT,
    risk     TEXT DEFAULT 'low',
    score    REAL DEFAULT 0,
    status   TEXT NOT NULL DEFAULT 'open'
             CHECK (status IN ('open', 'claimed', 'done', 'rejected')),
    lane     TEXT,
    evidence TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id       TEXT PRIMARY KEY,
    kind     TEXT NOT NULL
             CHECK (kind IN ('nightly', 'weekly', 'social', 'digest', 'gate', 'selftest')),
    repo     TEXT,
    started  TEXT NOT NULL,
    finished TEXT,
    outcome  TEXT,
    pr_url   TEXT
);

CREATE TABLE IF NOT EXISTS lessons (
    id          TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    incident    TEXT NOT NULL,
    lesson      TEXT NOT NULL,
    enforcement TEXT,
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'closed'))
);

CREATE TABLE IF NOT EXISTS reputation (
    actor   TEXT NOT NULL,
    kind    TEXT NOT NULL
            CHECK (kind IN ('persona', 'model', 'repo')),
    wins    INTEGER NOT NULL DEFAULT 0,
    losses  INTEGER NOT NULL DEFAULT 0,
    updated TEXT,
    PRIMARY KEY (actor, kind)
);

CREATE TABLE IF NOT EXISTS post_queue (
    id          TEXT PRIMARY KEY,
    channel     TEXT NOT NULL,
    draft       TEXT,
    taste_refs  TEXT,
    drafted_at  TEXT,
    approved_at TEXT,
    posted_at   TEXT,
    post_url    TEXT
);

CREATE TABLE IF NOT EXISTS repo_registry (
    repo        TEXT PRIMARY KEY,
    tier        INTEGER,
    autonomy    TEXT NOT NULL DEFAULT 'paused'
                CHECK (autonomy IN ('on', 'paused')),
    open_prs    INTEGER DEFAULT 0,
    last_nightly TEXT
);
"""


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None or row[0] < SCHEMA_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied) VALUES (?, ?)",
            (SCHEMA_VERSION, _now()),
        )
        conn.commit()
    return SCHEMA_VERSION


# ----------------------------------------------------------------- migration

def _read_jsonl(path):
    rows = []
    if not Path(path).exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _stable_id(row, *keys):
    seed = "|".join(str(row.get(k, "")) for k in keys)
    return hashlib.sha256(seed.encode()).hexdigest()[:10]


def migrate_proposals(conn, path=None):
    path = path or ROOT / "tools" / "selfimprove" / "proposals.jsonl"
    rows = _read_jsonl(path)
    count = 0
    for r in rows:
        pid = r.get("id") or _stable_id(r, "title")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO proposals (id, source, repo, title, kind, risk, score, status, evidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, "selfimprove", r.get("repo", "claude-setup"),
                 r.get("title", ""), r.get("kind"), r.get("risk", "low"),
                 r.get("score", 0), "open", r.get("evidence")),
            )
            count += conn.total_changes
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return count


def migrate_lessons(conn, path=None):
    path = path or ROOT / "state" / "lessons.jsonl"
    rows = _read_jsonl(path)
    count = 0
    for r in rows:
        lid = r.get("id") or _stable_id(r, "date", "incident")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO lessons (id, date, incident, lesson, enforcement, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (lid, r.get("date", ""), r.get("incident", ""),
                 r.get("lesson", ""), r.get("enforcement"),
                 r.get("status", "open")),
            )
            count += conn.total_changes
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return count


def migrate_claims(conn, path=None):
    path = path or ROOT / "state" / "claims.jsonl"
    rows = _read_jsonl(path)
    count = 0
    for r in rows:
        pid = r.get("proposal_id", "")
        if pid == "_seed":
            continue
        sid = _stable_id(r, "proposal_id", "ts")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, lane, started_at, charter) "
                "VALUES (?, ?, ?, ?)",
                (sid, r.get("lane", ""), r.get("ts", ""), r.get("note")),
            )
            count += conn.total_changes
        except sqlite3.IntegrityError:
            pass
        conn.execute(
            "UPDATE proposals SET status='claimed', lane=? WHERE id=? AND status='open'",
            (r.get("lane", ""), pid),
        )
    conn.commit()
    return count


def migrate_all(conn):
    totals = {}
    totals["proposals"] = migrate_proposals(conn)
    totals["lessons"] = migrate_lessons(conn)
    totals["claims"] = migrate_claims(conn)
    return totals


# ----------------------------------------------------------------- commands

def claim(conn, proposal_id, lane):
    row = conn.execute("SELECT status FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if row is None:
        raise ValueError(f"proposal {proposal_id!r} not found")
    if row["status"] == "claimed":
        raise ValueError(f"proposal {proposal_id!r} already claimed")
    conn.execute(
        "UPDATE proposals SET status='claimed', lane=? WHERE id=?",
        (lane, proposal_id),
    )
    conn.commit()


def log_run(conn, kind, repo, outcome, pr_url=None):
    rid = uuid.uuid4().hex[:12]
    now = _now()
    conn.execute(
        "INSERT INTO runs (id, kind, repo, started, finished, outcome, pr_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rid, kind, repo, now, now, outcome, pr_url),
    )
    conn.commit()
    return rid


def approve(conn, post_id):
    row = conn.execute("SELECT id FROM post_queue WHERE id=?", (post_id,)).fetchone()
    if row is None:
        raise ValueError(f"post {post_id!r} not found in queue")
    conn.execute(
        "UPDATE post_queue SET approved_at=? WHERE id=?", (_now(), post_id)
    )
    conn.commit()


_TABLES = ("sessions", "proposals", "runs", "lessons", "reputation",
           "post_queue", "repo_registry")

_COUNT_QUERIES = {
    "sessions":      "SELECT count(*) FROM sessions",
    "proposals":     "SELECT count(*) FROM proposals",
    "runs":          "SELECT count(*) FROM runs",
    "lessons":       "SELECT count(*) FROM lessons",
    "reputation":    "SELECT count(*) FROM reputation",
    "post_queue":    "SELECT count(*) FROM post_queue",
    "repo_registry": "SELECT count(*) FROM repo_registry",
}


def status(conn):
    out = {}
    for t in _TABLES:
        out[t] = conn.execute(_COUNT_QUERIES[t]).fetchone()[0]
    v = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    out["schema_version"] = v[0] if v else 0
    return out


# ----------------------------------------------------------------- selftest

def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = connect(db_path)
        v = init_schema(conn)
        assert v == SCHEMA_VERSION, f"schema version {v}"

        # proposals
        pf = Path(tmp) / "proposals.jsonl"
        pf.write_text(json.dumps({
            "id": "test1", "title": "Test proposal", "kind": "gap",
            "risk": "low", "score": 8, "evidence": "file.py"
        }) + "\n", encoding="utf-8")
        migrate_proposals(conn, pf)
        row = conn.execute("SELECT * FROM proposals WHERE id='test1'").fetchone()
        assert row is not None, "proposal not migrated"
        assert row["title"] == "Test proposal"

        # idempotent re-migration
        migrate_proposals(conn, pf)
        ct = conn.execute("SELECT count(*) FROM proposals").fetchone()[0]
        assert ct == 1, f"duplicate inserted: {ct}"

        # claim
        claim(conn, "test1", "A")
        row = conn.execute("SELECT status, lane FROM proposals WHERE id='test1'").fetchone()
        assert row["status"] == "claimed"
        assert row["lane"] == "A"
        try:
            claim(conn, "test1", "B")
            assert False, "double-claim should raise"
        except ValueError:
            pass

        # lessons
        lf = Path(tmp) / "lessons.jsonl"
        lf.write_text(json.dumps({
            "id": "L999", "date": "2026-01-01", "incident": "test",
            "lesson": "test lesson", "enforcement": "none", "status": "closed"
        }) + "\n", encoding="utf-8")
        migrate_lessons(conn, lf)
        row = conn.execute("SELECT * FROM lessons WHERE id='L999'").fetchone()
        assert row is not None
        assert row["lesson"] == "test lesson"

        # claims migration
        cf = Path(tmp) / "claims.jsonl"
        cf.write_text(json.dumps({
            "proposal_id": "test1", "lane": "A", "ts": "2026-01-01", "note": "test claim"
        }) + "\n", encoding="utf-8")
        migrate_claims(conn, cf)
        sess = conn.execute("SELECT * FROM sessions").fetchone()
        assert sess is not None

        # log-run
        rid = log_run(conn, "nightly", "claude-setup", "PASS")
        row = conn.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        assert row is not None
        assert row["outcome"] == "PASS"

        # approve (post_queue)
        conn.execute(
            "INSERT INTO post_queue (id, channel, draft) VALUES ('p1', 'linkedin', 'hello')"
        )
        conn.commit()
        approve(conn, "p1")
        row = conn.execute("SELECT approved_at FROM post_queue WHERE id='p1'").fetchone()
        assert row["approved_at"] is not None

        # status
        s = status(conn)
        assert s["proposals"] == 1
        assert s["lessons"] == 1
        assert s["runs"] == 1
        assert s["schema_version"] == SCHEMA_VERSION

        conn.close()
        print("selftest: PASS (7 tables, migrate, claim, log-run, approve, status)")
        return True


# ----------------------------------------------------------------- CLI

def main():
    parser = argparse.ArgumentParser(
        description="Ecosystem state DB (ADR-0011)")
    parser.add_argument("--db", default=None,
                        help="DB path (default: state/ecosystem.db)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init", help="create/migrate schema")
    sub.add_parser("migrate-jsonl", help="ingest JSONL into tables")
    sub.add_parser("status", help="summary counts per table")
    sub.add_parser("selftest", help="run self-tests")

    p_claim = sub.add_parser("claim", help="claim a proposal for a lane")
    p_claim.add_argument("proposal_id")
    p_claim.add_argument("lane")

    p_run = sub.add_parser("log-run", help="log an autonomous run")
    p_run.add_argument("kind", choices=["nightly", "weekly", "social", "digest", "gate", "selftest"])
    p_run.add_argument("repo")
    p_run.add_argument("outcome")
    p_run.add_argument("--pr", default=None, help="PR URL")

    p_approve = sub.add_parser("approve", help="approve a post_queue item")
    p_approve.add_argument("post_id")

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

    elif args.cmd == "migrate-jsonl":
        totals = migrate_all(conn)
        for table, n in totals.items():
            print(f"  {table}: {n} rows ingested")

    elif args.cmd == "status":
        s = status(conn)
        for k, v in s.items():
            print(f"  {k}: {v}")

    elif args.cmd == "claim":
        claim(conn, args.proposal_id, args.lane)
        print(f"claimed {args.proposal_id} for lane {args.lane}")

    elif args.cmd == "log-run":
        rid = log_run(conn, args.kind, args.repo, args.outcome, args.pr)
        print(f"logged run {rid}")

    elif args.cmd == "approve":
        approve(conn, args.post_id)
        print(f"approved {args.post_id}")

    conn.close()


if __name__ == "__main__":
    main()
