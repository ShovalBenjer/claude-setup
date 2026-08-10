"""Tests for the transcript backfill.

The module's own `selftest` is the oracle CI runs as a named step. These add the cases
that are awkward there: property-shaped checks over the id function, and the specific
contaminant classes the filter exists to reject. The two overlap on purpose. A selftest
that is the only check on its own filter is a claim, not a test.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "intent"))

import backfill_transcripts as bt  # noqa: E402
import tickets  # noqa: E402


def write_transcript(directory: Path, name: str, records: list) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write((record if isinstance(record, str) else json.dumps(record)) + "\n")
    return path


def user(text, **extra):
    row = {"type": "user", "sessionId": "s1", "timestamp": "2026-08-01T00:00:00Z",
           "cwd": "/home/shov/demo", "message": {"content": text}}
    row.update(extra)
    return row


def test_selftest_passes():
    assert bt.selftest() == 0


@pytest.mark.parametrize("record,why", [
    (user("out", toolUseResult={"ok": 1}), "a tool result is not a typed prompt"),
    (user("meta", isMeta=True), "a meta line is harness bookkeeping"),
    (user("sub", isSidechain=True), "a sidechain turn belongs to a subagent"),
    (user("<system-reminder>x</system-reminder>"), "a system reminder is injected"),
    (user("<task-notification>\nid\n"), "a task notification is machine authored"),
    (user("This session is being continued from a previous conversation. The summary"),
     "a compaction summary is assistant authored, and it is the expensive one to miss"),
    (user([{"type": "tool_result", "content": "x"}]), "list content is a tool result"),
    (user("   "), "whitespace carries no intent"),
])
def test_filter_rejects(tmp_path, record, why):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [record])
    _, prompts = bt.funnel(tmp_path / "projects")
    assert prompts == [], why


@pytest.mark.parametrize("text", [
    "fix the parser",
    "/compact",                       # a slash command is a prompt; classify calls it noise later
    "push. merge",                    # short, and real
    "1[212 08:42:43] [glfw error 65544]: pasted log output",
    "הקשר באפליקציה",
])
def test_filter_keeps(tmp_path, text):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [user(text)])
    _, prompts = bt.funnel(tmp_path / "projects")
    assert [p.text for p in prompts] == [text]


def test_torn_line_costs_one_line_not_the_file(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl",
                     [user("before"), "{ not json", user("after")])
    _, prompts = bt.funnel(tmp_path / "projects")
    assert [p.text for p in prompts] == ["before", "after"]


def test_funnel_counts_every_stage(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [
        user("kept"), user("x", toolUseResult={}), user("y", isMeta=True),
        {"type": "assistant", "message": {"content": "not counted"}},
    ])
    counts, prompts = bt.funnel(tmp_path / "projects")
    assert counts["type=user"] == 3
    assert counts["not a tool result"] == 2
    assert counts["not meta"] == 1
    assert len(prompts) == 1


def test_repeated_prompt_in_one_session_gets_distinct_ids(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [
        user("again", timestamp="2026-08-01T00:00:01Z"),
        user("again", timestamp="2026-08-01T00:00:02Z"),
    ])
    _, prompts = bt.funnel(tmp_path / "projects")
    ids = [t for _, t, _ in bt.plan(prompts, [])]
    assert len(set(ids)) == 2, "two typings of the same words are two pieces of work"


def test_ids_match_what_live_capture_would_mint(tmp_path):
    """The join that makes a recovered prompt and a captured one one ticket."""
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [user("shared")])
    _, prompts = bt.funnel(tmp_path / "projects")
    prompt = prompts[0]
    _, recovered, _ = bt.plan(prompts, [])[0]
    assert recovered == tickets.ticket_id(prompt.session, tickets.text_sha("shared"), 0)


def test_plan_skips_what_the_ledger_already_holds(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [user("once")])
    _, prompts = bt.funnel(tmp_path / "projects")
    existing = [{"session": "s1", "text_sha": tickets.text_sha("once")}]
    assert [needs for _, _, needs in bt.plan(prompts, existing)] == [False]
    assert [needs for _, _, needs in bt.plan(prompts, [])] == [True]


def test_run_is_idempotent_and_preserves_transcript_time(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl",
                     [user("recover me", timestamp="2026-07-08T18:25:11.740Z")])
    ledger, base = tmp_path / "pt.jsonl", tmp_path / "intent"

    first = bt.run(base_dir=base, ledger=ledger, root=tmp_path / "projects")
    assert (first["written"], first["enriched"], first["enrich_failed"]) == (1, 1, 0)

    second = bt.run(base_dir=base, ledger=ledger, root=tmp_path / "projects")
    assert (second["written"], second["enriched"]) == (0, 0)

    conn = sqlite3.connect(base / "intent.db")
    stamps = [r[0] for r in conn.execute("select timestamp_utc from events")]
    texts = [r[0] for r in conn.execute("select raw_text_ref is not null from events")]
    conn.close()
    assert stamps == ["2026-07-08T18:25:11.740Z"], "the clock must not replace the fact"
    assert texts == [1]
    assert tickets.verify(ledger) == []


def test_a_ledger_row_whose_event_never_landed_is_repaired(tmp_path):
    """The ten-day outage shape: hash recorded, text dropped."""
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [user("outage")])
    ledger, base = tmp_path / "pt.jsonl", tmp_path / "intent"
    bt.run(base_dir=base, ledger=ledger, root=tmp_path / "projects")

    conn = sqlite3.connect(base / "intent.db")
    conn.execute("delete from events")
    conn.commit()
    conn.close()

    repair = bt.run(base_dir=base, ledger=ledger, root=tmp_path / "projects")
    assert repair["written"] == 0, "the hash is already recorded"
    assert repair["enriched"] == 1, "the text is not, and that is the whole outage"


def test_stored_tickets_never_reports_an_existing_store_as_empty(tmp_path):
    write_transcript(tmp_path / "projects" / "-demo", "s.jsonl", [user("stored")])
    base = tmp_path / "intent"
    bt.run(base_dir=base, ledger=tmp_path / "pt.jsonl", root=tmp_path / "projects")
    assert len(bt.stored_tickets(base)) == 1
    assert bt.stored_tickets(tmp_path / "absent") == set(), "an absent store holds nothing"


def test_backfill_cannot_reach_a_workable_state(tmp_path):
    """The structural anti-invention guarantee, asserted rather than trusted."""
    source = (REPO_ROOT / "tools" / "intent" / "backfill_transcripts.py").read_text()
    for state in ("OPEN", "IN_PROGRESS", "TRIAGED", "CLOSED_VERIFIED"):
        assert f'"{state}"' not in source, f"the backfill names {state}; it may only capture"


def test_repo_name_prefers_cwd_over_the_flattened_slug():
    with_cwd = bt.Prompt(slug="-home-shov-work-repos-x", session="s", ts="", text="t",
                         cwd="/home/shov/work/repos/daily-deep-learning/daemon")
    assert bt.repo_name(with_cwd) == "daemon"
    without = bt.Prompt(slug="-home-shov-work-repos-new-recruit", session="s", ts="",
                        text="t", cwd="")
    assert bt.repo_name(without) == "recruit"  # lossy, and only reached without a cwd
