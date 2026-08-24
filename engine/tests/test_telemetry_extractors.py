"""Pin the telemetry extractors against BOTH ledger generations.

`tools/telemetry/collect.py` has its own selftest and now a mutation spec. This exists
for the reason `tests/test_bus_lock.py` and `tests/test_rules_sync_no_live_tree.py` exist:
a selftest is a command somebody has to choose to run, `mutate.py --spec telemetry` is
slower than the whole root suite, and this component publishes to GitHub every 30 minutes
under a systemd timer with nobody watching.

Every row below is copied from a real ledger, not invented. The defect these pin was not
a logic error; it was an extractor naming ONE spelling of a field the ledger writes under
two, so the OLD spelling is what gets asserted. A test written against the new spelling
would pass against the very code that published 52 empty rows.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TELEMETRY = REPO / "tools" / "telemetry"


def _load(name: str):
    """Load by path. tools/ is not a package, the same reason mutate.py loads by path."""
    spec = importlib.util.spec_from_file_location("_tele_" + name, TELEMETRY / (name + ".py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def collect():
    return _load("collect")


@pytest.fixture()
def publish():
    return _load("publish")


def _payload(subject: str) -> str:
    for sep in (": ", " -> ", "] "):
        if sep in subject:
            return subject.split(sep, 1)[1]
    return subject


# --------------------------------------------------------------- the old generation

def test_a_lesson_dated_with_date_keeps_its_timestamp(collect):
    """22 of these published with no timestamp, so they passed every window forever."""
    ev = collect._from_lessons({"id": "L006", "status": "open", "date": "2026-07-27",
                                "incident": "a gate PASS claimed from a stale ledger"})
    assert ev["ts"] == "2026-07-27"
    assert _payload(ev["subject"]).strip(), "published as 'L006:' and nothing else"
    assert ev["ref"] == "L006"


def test_a_claim_using_ts_and_proposal_id_is_complete(collect):
    """30 of these published as 'lane B claimed:' with nothing after the colon."""
    ev = collect._from_claims({"lane": "B", "ts": "2026-07-31T14:05:00",
                               "proposal_id": "session-2026-07-31-estate-unification",
                               "note": "cross-lane, claimed with operator approval"})
    assert ev["ts"] == "2026-07-31T14:05:00"
    assert _payload(ev["subject"]).strip()
    assert ev["ref"] == "session-2026-07-31-estate-unification"


def test_the_new_generation_still_wins_when_both_are_present(collect):
    """The fallback must be a fallback, not a replacement."""
    ev = collect._from_lessons({"id": "L1", "status": "open", "ts": "2026-08-01",
                                "date": "2026-07-01", "class": "new", "incident": "old"})
    assert ev["ts"] == "2026-08-01"
    assert "new" in ev["subject"]


def test_an_empty_field_does_not_beat_a_populated_fallback(collect):
    """A ledger writing "" is saying it does not know. Reading it as data is the bug."""
    assert collect.first_of({"a": "", "b": "   ", "c": "x"}, "a", "b", "c") == "x"
    ev = collect._from_claims({"lane": "A", "claimed_at": "", "ts": "2026-08-05",
                               "scope": "", "note": "real text"})
    assert ev["ts"] == "2026-08-05"
    assert "real text" in ev["subject"]


# --------------------------------------------------------------- worktrees

def test_a_git_pointer_file_is_a_worktree_and_a_directory_is_a_repo(collect, tmp_path):
    wt, real = tmp_path / "wt", tmp_path / "real"
    (wt / "state").mkdir(parents=True)
    (wt / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n", encoding="utf-8")
    (real / "state").mkdir(parents=True)
    (real / ".git").mkdir()
    assert collect.is_worktree(wt) is True
    assert collect.is_worktree(real) is False


def test_discover_records_the_worktree_it_skipped(collect, tmp_path):
    """A silent omission reads as coverage. 212 of 516 events came from one worktree."""
    for name, is_wt in (("wt", True), ("real", False)):
        d = tmp_path / name
        (d / "state").mkdir(parents=True)
        if is_wt:
            (d / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
        else:
            (d / ".git").mkdir()
    saved = collect.REPO_ROOTS
    try:
        collect.REPO_ROOTS = [tmp_path]
        noted: list[str] = []
        found = collect.discover_repos(noted)
    finally:
        collect.REPO_ROOTS = saved
    assert [p.name for p in found] == ["real"]
    assert noted == ["wt"]


# --------------------------------------------------------------- the window

def test_an_undated_row_is_excluded_from_a_window_and_kept_without_one(collect, tmp_path):
    """Until 2026-08-05 an undated row passed EVERY window, so it never aged out."""
    import datetime as dt

    repo = tmp_path / "planted"
    (repo / "state").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "state" / "lessons.jsonl").write_text(
        json.dumps({"id": "L-UNDATED", "status": "open", "lesson": "no stamp"}) + "\n",
        encoding="utf-8")
    saved = collect.REPO_ROOTS
    try:
        collect.REPO_ROOTS = [tmp_path]
        unwindowed, _ = collect.collect()
        windowed, audit = collect.collect(dt.datetime.now() - dt.timedelta(days=3650))
    finally:
        collect.REPO_ROOTS = saved
    assert len(unwindowed) == 1, "the row exists and must survive an unwindowed query"
    assert windowed == []
    assert audit["__meta__"]["undated_dropped"] == 1, "the exclusion must be countable"


# --------------------------------------------------------------- the dedupe guarantee

def test_fingerprint_still_collapses_the_same_fact_at_two_timestamps(collect, publish):
    """The guarantee a well-meaning fix would delete.

    160 collapses in the live corpus are INTENDED: the same lesson re-read on a later run
    is one fact, not two, and that is why `fingerprint()` excludes `ts` on purpose. Adding
    the timestamp to the key would drop the collision count to zero and look like a fix
    for the blank-row problem, while actually reposting every standing alert forever.
    """
    a = collect.event(repo="claude-setup", source="lessons", kind="lesson",
                      severity=collect.ALERT, subject="L006: x", ref="L006",
                      ts="2026-08-01T10:00:00")
    b = dict(a, ts="2026-08-05T22:00:00")
    assert publish.fingerprint(a) == publish.fingerprint(b)


def test_two_claims_that_differ_only_in_note_are_distinct(collect, publish):
    """Before the fix both rendered as 'lane B claimed:' and collided into one item."""
    x = collect._from_claims({"lane": "B", "ts": "2026-08-01", "proposal_id": "p1",
                              "note": "first thing"})
    y = collect._from_claims({"lane": "B", "ts": "2026-08-01", "proposal_id": "p2",
                              "note": "second thing"})
    assert publish.fingerprint(x) != publish.fingerprint(y)
