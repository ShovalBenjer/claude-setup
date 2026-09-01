"""Tests for tools/eco/db.py (ecosystem.db, ADR-0011, AUTO-06)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "eco_db_under_test", ROOT / "tools" / "eco" / "db.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


db = _load()


@pytest.fixture
def fresh_db(tmp_path):
    conn = db.connect(tmp_path / "test.db")
    db.init_schema(conn)
    yield conn
    conn.close()


class TestSchema:
    def test_init_creates_all_tables(self, fresh_db):
        tables = {r[0] for r in fresh_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        expected = {"schema_version", "sessions", "proposals", "runs",
                    "lessons", "reputation", "post_queue", "repo_registry"}
        assert expected <= tables

    def test_version_recorded(self, fresh_db):
        row = fresh_db.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        assert row[0] == db.SCHEMA_VERSION

    def test_init_is_idempotent(self, tmp_path):
        conn = db.connect(tmp_path / "idem.db")
        v1 = db.init_schema(conn)
        v2 = db.init_schema(conn)
        assert v1 == v2
        conn.close()


class TestMigrateProposals:
    def test_ingests_proposals(self, fresh_db, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text(
            json.dumps({"id": "p1", "title": "Test", "kind": "gap", "score": 5}) + "\n"
            + json.dumps({"id": "p2", "title": "Other", "kind": "hygiene"}) + "\n",
            encoding="utf-8",
        )
        db.migrate_proposals(fresh_db, f)
        assert fresh_db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 2

    def test_idempotent(self, fresh_db, tmp_path):
        f = tmp_path / "proposals.jsonl"
        f.write_text(json.dumps({"id": "x", "title": "X"}) + "\n", encoding="utf-8")
        db.migrate_proposals(fresh_db, f)
        db.migrate_proposals(fresh_db, f)
        assert fresh_db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 1

    def test_missing_file_returns_zero(self, fresh_db, tmp_path):
        n = db.migrate_proposals(fresh_db, tmp_path / "nope.jsonl")
        assert fresh_db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0


class TestMigrateLessons:
    def test_ingests_lessons(self, fresh_db, tmp_path):
        f = tmp_path / "lessons.jsonl"
        f.write_text(json.dumps({
            "id": "L1", "date": "2026-01-01", "incident": "oops",
            "lesson": "fix it", "enforcement": "rule", "status": "closed"
        }) + "\n", encoding="utf-8")
        db.migrate_lessons(fresh_db, f)
        row = fresh_db.execute("SELECT * FROM lessons WHERE id='L1'").fetchone()
        assert row is not None
        assert row["lesson"] == "fix it"


class TestMigrateClaims:
    def test_creates_sessions_from_claims(self, fresh_db, tmp_path):
        pf = tmp_path / "proposals.jsonl"
        pf.write_text(json.dumps({"id": "pp", "title": "Prop"}) + "\n", encoding="utf-8")
        db.migrate_proposals(fresh_db, pf)

        cf = tmp_path / "claims.jsonl"
        cf.write_text(json.dumps({
            "proposal_id": "pp", "lane": "A", "ts": "2026-01-01", "note": "claimed"
        }) + "\n", encoding="utf-8")
        db.migrate_claims(fresh_db, cf)
        sess = fresh_db.execute("SELECT count(*) FROM sessions").fetchone()[0]
        assert sess >= 1

    def test_skips_seed_row(self, fresh_db, tmp_path):
        cf = tmp_path / "claims.jsonl"
        cf.write_text(json.dumps({
            "proposal_id": "_seed", "lane": "B", "ts": "2026-01-01"
        }) + "\n", encoding="utf-8")
        db.migrate_claims(fresh_db, cf)
        assert fresh_db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


class TestClaim:
    def test_claim_updates_status(self, fresh_db):
        fresh_db.execute(
            "INSERT INTO proposals (id, title, status) VALUES ('c1', 'Claim me', 'open')"
        )
        fresh_db.commit()
        db.claim(fresh_db, "c1", "B")
        row = fresh_db.execute("SELECT status, lane FROM proposals WHERE id='c1'").fetchone()
        assert row["status"] == "claimed"
        assert row["lane"] == "B"

    def test_double_claim_raises(self, fresh_db):
        fresh_db.execute(
            "INSERT INTO proposals (id, title, status) VALUES ('c2', 'Taken', 'claimed')"
        )
        fresh_db.commit()
        with pytest.raises(ValueError, match="already claimed"):
            db.claim(fresh_db, "c2", "A")

    def test_missing_proposal_raises(self, fresh_db):
        with pytest.raises(ValueError, match="not found"):
            db.claim(fresh_db, "nonexistent", "A")


class TestLogRun:
    def test_logs_a_run(self, fresh_db):
        rid = db.log_run(fresh_db, "nightly", "claude-setup", "PASS")
        row = fresh_db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        assert row["kind"] == "nightly"
        assert row["outcome"] == "PASS"

    def test_run_with_pr_url(self, fresh_db):
        rid = db.log_run(fresh_db, "gate", "claude-setup", "FAIL",
                         pr_url="https://github.com/x/y/pull/1")
        row = fresh_db.execute("SELECT pr_url FROM runs WHERE id=?", (rid,)).fetchone()
        assert "pull/1" in row["pr_url"]


class TestApprove:
    def test_sets_approved_at(self, fresh_db):
        fresh_db.execute(
            "INSERT INTO post_queue (id, channel, draft) VALUES ('q1', 'linkedin', 'hi')"
        )
        fresh_db.commit()
        db.approve(fresh_db, "q1")
        row = fresh_db.execute("SELECT approved_at FROM post_queue WHERE id='q1'").fetchone()
        assert row["approved_at"] is not None

    def test_missing_post_raises(self, fresh_db):
        with pytest.raises(ValueError, match="not found"):
            db.approve(fresh_db, "no-such-post")


class TestStatus:
    def test_reports_all_tables(self, fresh_db):
        s = db.status(fresh_db)
        assert "sessions" in s
        assert "proposals" in s
        assert "runs" in s
        assert "lessons" in s
        assert "reputation" in s
        assert "post_queue" in s
        assert "repo_registry" in s
        assert s["schema_version"] == db.SCHEMA_VERSION


class TestConstraints:
    def test_proposal_status_constraint(self, fresh_db):
        with pytest.raises(Exception):
            fresh_db.execute(
                "INSERT INTO proposals (id, title, status) VALUES ('bad', 'X', 'invalid')"
            )

    def test_run_kind_constraint(self, fresh_db):
        with pytest.raises(Exception):
            fresh_db.execute(
                "INSERT INTO runs (id, kind, repo, started) VALUES ('r', 'bogus', 'x', '2026')"
            )

    def test_reputation_kind_constraint(self, fresh_db):
        with pytest.raises(Exception):
            fresh_db.execute(
                "INSERT INTO reputation (actor, kind, wins, losses) VALUES ('a', 'bad', 0, 0)"
            )
