"""Tests for skill_invoke telemetry: parse a PostToolUse payload, write it, read it back.

Closes the loop measured by the 2026-07-10 audit: sessions.db session_events had a
'skill_invoke' event_type defined and zero rows. This writer populates it; the router's
skill_usage_counts (Tier 1e) reads it.
"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from intent_control_plane import cli
from intent_control_plane.cli import parse_skill_event
from intent_control_plane.harness.router import skill_usage_counts


def test_parse_skill_event_extracts_skill_and_session():
    payload = {"tool_name": "Skill", "tool_input": {"skill": "reground"}, "session_id": "abc"}
    assert parse_skill_event(payload) == {"skill": "reground", "session": "abc"}


def test_parse_skill_event_ignores_non_skill_tools():
    assert parse_skill_event({"tool_name": "Bash", "tool_input": {"command": "ls"}}) is None


def test_parse_skill_event_ignores_missing_skill_name():
    assert parse_skill_event({"tool_name": "Skill", "tool_input": {}}) is None


def test_log_skill_writes_a_skill_invoke_row(tmp_path):
    db = tmp_path / "sessions.db"
    res = cli.log_skill(SimpleNamespace(skill="tdd", session="s1", db=str(db)))
    assert res["status"] == "logged"
    conn = sqlite3.connect(db)
    rows = conn.execute("select event_type, detail, session_id from session_events").fetchall()
    conn.close()
    assert rows == [("skill_invoke", "tdd", "s1")]


def test_log_skill_creates_missing_parent_dir(tmp_path):
    # regression: sqlite3.connect fails if the DB parent dir does not exist (Codex review)
    db = tmp_path / "nested" / "deeper" / "sessions.db"
    res = cli.log_skill(SimpleNamespace(skill="x", session="s", db=str(db)))
    assert res["status"] == "logged"
    assert db.exists()


def test_log_skill_feeds_router_usage_counts(tmp_path):
    # end-to-end: Tier 0b writer -> Tier 1e reader, proving the measurement loop closes
    db = tmp_path / "sessions.db"
    cli.log_skill(SimpleNamespace(skill="reground", session="s", db=str(db)))
    cli.log_skill(SimpleNamespace(skill="reground", session="s", db=str(db)))
    cli.log_skill(SimpleNamespace(skill="tdd", session="s", db=str(db)))
    assert skill_usage_counts(db) == {"reground": 2, "tdd": 1}
