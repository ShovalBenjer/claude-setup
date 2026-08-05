"""Pin the host-shape property of tools/audit/rules_sync.py.

The selftest inside that file already covers this, and so does
`tools/audit/mutations/rules.py`. This exists anyway for the reason
`tests/test_bus_lock.py` exists: the selftest is one command that a person has to
choose to run, and `mutate.py --spec rules` is slower than the whole root suite. A
property that only three deliberate invocations can see is one nobody sees on the
way past.

What is pinned is the split, not the pass. `rules_sync.py check` on a machine with
no `~/.claude/rules` must exit 0, must SAY which half did not run, and must still be
able to fail on a truncated rule. Asserting only the exit code would be satisfied by
a version that returns 0 unconditionally, which is the regression this file is here
to make loud.
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "tools" / "audit" / "rules_sync.py"


def _load():
    """Load by path. tools/ is not a package, same reason mutate.py loads by path."""
    spec = importlib.util.spec_from_file_location("_rules_sync_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def rs():
    return _load()


def _report(mod, res: dict) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.report(res)
    return code, buf.getvalue()


def _base(mod, **over) -> dict:
    d = {"payload_dir": str(mod.PAYLOAD), "live_dir": "/no/such/rules",
         "live_present": True, "counted": 1, "shrink_checked": 1,
         "only_payload": [], "only_live": [], "differing": [], "shrunk": []}
    d.update(over)
    return d


def test_absent_live_tree_is_not_a_failure(rs):
    """The CI condition. A runner has no deployed harness, which is correct."""
    code, _ = _report(rs, _base(rs, live_present=False))
    assert code == 0


def test_absent_live_tree_names_the_check_it_skipped(rs):
    """A pass whose reduced scope is invisible is worse than a fail."""
    _, text = _report(rs, _base(rs, live_present=False))
    assert "NOT RUN" in text
    assert "/no/such/rules" in text


def test_truncated_rule_still_fails_without_a_live_tree(rs):
    """The shrink half is the check that would have caught 2bb97a8. It runs anywhere."""
    res = _base(rs, live_present=False,
                shrunk=[{"rule": "boundary-contracts.md", "now": 488, "max": 5557,
                         "ratio": 0.088, "max_at": "146cb7b4"}])
    code, text = _report(rs, res)
    assert code == 1
    assert "boundary-contracts.md" in text


def test_present_live_tree_still_fails_on_drift(rs):
    """The repair must not have widened anything on the host that can measure it."""
    res = _base(rs, differing=[{"rule": "z.md", "payload_bytes": 1, "live_bytes": 2}])
    assert _report(rs, res)[0] == 1


def test_empty_live_directory_is_not_the_same_fact_as_an_absent_one(rs, tmp_path):
    """Absent means not deployed here. Empty means deployed and then destroyed."""
    saved = rs.LIVE
    try:
        rs.LIVE = tmp_path
        empty = rs.scan()
        rs.LIVE = Path("/nonexistent-live-rules-tree-for-pytest")
        absent = rs.scan()
    finally:
        rs.LIVE = saved

    n_payload = len(list(rs.PAYLOAD.glob("*.md")))
    assert n_payload > 0, "no payload rules, so every assertion below would be vacuous"

    assert empty["live_present"] is True
    assert len(empty["only_payload"]) == n_payload
    assert _report(rs, empty)[0] == 1

    assert absent["live_present"] is False
    assert absent["only_payload"] == []


def test_shrink_runs_over_every_payload_rule_with_no_live_tree(rs):
    """An empty `shrunk` is the healthy answer AND the answer a dead loop gives.

    Only the count separates them, which is why scan() reports one.
    """
    saved = rs.LIVE
    try:
        rs.LIVE = Path("/nonexistent-live-rules-tree-for-pytest")
        res = rs.scan()
    finally:
        rs.LIVE = saved
    assert res["shrink_checked"] == len(list(rs.PAYLOAD.glob("*.md")))
    assert res["shrink_checked"] > 0


def test_the_shrink_floor_brackets_the_incident_on_both_sides(rs):
    """Below 0.088 the incident passes; above 0.90 the legitimate trims fail."""
    assert 488 < 5557 * rs.SHRINK_FLOOR, "2bb97a8 would not be caught"
    assert 0.90 * 5557 >= 5557 * rs.SHRINK_FLOOR, "healthy trims would be flagged"
