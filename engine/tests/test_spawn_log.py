"""The spawn ledger records what ran, and never breaks the spawn that ran.

These exist because the hook they cover was wired in settings.json to a file
that did not exist, in either clone, and failed on every single Agent call
without anything noticing until three spawns in one turn reported it three
times. The failure mode being guarded is therefore not "the row is wrong", it
is "the hook is louder than the work it observes".
"""
from __future__ import annotations

import datetime
import io
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "intent"))

import spawn_log  # noqa: E402

NOW = datetime.datetime(2026, 8, 7, 12, 0, 0)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "quality-contract.json").write_text("{}", encoding="utf-8")
    (tmp_path / "state").mkdir()
    return tmp_path


def write_routing(project, rows):
    with open(project / "state" / "routing.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def test_the_row_names_the_subagent_that_ran(project):
    payload = {"tool_input": {"subagent_type": "evidence-clerk",
                              "description": "check a claim", "prompt": "x" * 40},
               "session_id": "s1", "cwd": str(project)}
    row = spawn_log.row_for(payload, str(project), NOW)
    assert row["subagent_type"] == "evidence-clerk"
    assert row["prompt_chars"] == 40
    assert row["session"] == "s1"


def test_an_unnamed_subagent_records_as_general_purpose_not_empty(project):
    """The Agent tool defaults to general-purpose when the field is omitted.

    Recording "" would put every default spawn in its own bucket and understate
    how often the router's persona was ignored in favour of the catch-all,
    which is the exact ratio this ledger exists to measure.
    """
    row = spawn_log.row_for({"tool_input": {}}, str(project), NOW)
    assert row["subagent_type"] == "general-purpose"


def test_a_recent_router_decision_is_attached_with_its_own_timestamp(project):
    write_routing(project, [
        {"ts": (NOW - datetime.timedelta(seconds=30)).isoformat(),
         "personas": ["Evidence Clerk"], "skills": ["decision-grade"]},
    ])
    row = spawn_log.row_for({"tool_input": {"subagent_type": "evidence-clerk"}},
                            str(project), NOW)
    assert row["router_named"] == ["Evidence Clerk"]
    assert row["router_named_at"] == (NOW - datetime.timedelta(seconds=30)).isoformat()


def test_a_stale_router_decision_is_recorded_as_absent_not_attached(project):
    """Past the window the association is invented, so it is not made.

    A wrong attachment is worse than a missing one here: it manufactures an
    agreement between what the router named and what was spawned that nobody
    observed, and the ratio is built out of exactly those agreements.
    """
    write_routing(project, [
        {"ts": (NOW - datetime.timedelta(seconds=601)).isoformat(),
         "personas": ["Mayor Opus"], "skills": []},
    ])
    row = spawn_log.row_for({"tool_input": {}}, str(project), NOW)
    assert row["router_named"] == []
    assert row["router_named_at"] == ""


def test_only_the_most_recent_routing_row_is_considered(project):
    """An old row must not be reached past a fresh one that fell outside nothing.

    Scanning further back on a miss would let a spawn attach to whichever
    historical row happened to be in window, which is worse than the stale case
    above because it looks deliberate.
    """
    write_routing(project, [
        {"ts": (NOW - datetime.timedelta(seconds=30)).isoformat(),
         "personas": ["Old"], "skills": []},
        {"ts": (NOW - datetime.timedelta(seconds=900)).isoformat(),
         "personas": ["Newer But Stale"], "skills": []},
    ])
    row = spawn_log.row_for({"tool_input": {}}, str(project), NOW)
    assert row["router_named"] == []


def test_a_corrupt_routing_line_does_not_stop_the_row(project):
    with open(project / "state" / "routing.jsonl", "w", encoding="utf-8") as fh:
        fh.write("not json at all\n")
    row = spawn_log.row_for({"tool_input": {"subagent_type": "qa-lab"}},
                            str(project), NOW)
    assert row["subagent_type"] == "qa-lab"
    assert row["router_named"] == []


def test_a_missing_routing_ledger_is_not_an_error(project):
    assert spawn_log.last_routing_row(str(project), NOW) is None


def test_the_hook_exits_zero_and_appends_when_run_end_to_end(project):
    payload = {"tool_input": {"subagent_type": "qa-lab", "description": "run tests",
                              "prompt": "hi"},
               "session_id": "s9", "cwd": str(project)}
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "intent", "spawn_log.py")],
                       input=json.dumps(payload), capture_output=True, text=True,
                       cwd=str(project))
    assert r.returncode == 0
    rows = (project / "state" / "agent-spawns.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    assert json.loads(rows[0])["subagent_type"] == "qa-lab"


def test_garbage_on_stdin_still_exits_zero_and_prints_nothing(project):
    """The whole point. A hook that fails must not fail the spawn.

    stdout is asserted empty as well: PostToolUse output is model-visible, so a
    chatty hook taxes every spawn in the session.
    """
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "intent", "spawn_log.py")],
                       input="}{ not json", capture_output=True, text=True,
                       cwd=str(project))
    assert r.returncode == 0
    assert r.stdout == ""


def test_an_unwritable_ledger_still_exits_zero(project, monkeypatch, capsys):
    """A state dir that cannot be written loses the record, never the spawn.

    Driven in-process rather than by subprocess on purpose: a subprocess run
    from an arbitrary cwd falls back to the real repository root and would
    append a junk row to the tracked ledger, so the test would pass while
    corrupting the thing it is about.
    """
    def boom(*a, **k):
        raise OSError("read-only")

    monkeypatch.setattr(spawn_log, "setup_root", boom)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {}})))
    assert spawn_log.main() == 0
    assert capsys.readouterr().out == ""
