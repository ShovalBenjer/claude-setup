"""Pin the host-shape property of tools/audit/rules_sync.py in the root suite.

That file's own selftest covers this, and so does `tools/audit/mutations/rules.py`.
This exists for the reason `tests/test_bus_lock.py` exists: the selftest is a command
somebody has to choose to run, `mutate.py --spec rules` is slower than the whole root
suite, and a property only two deliberate invocations can see is one nobody sees on
the way past.

What is pinned is the SPLIT, not the pass. With no `~/.claude/rules` the command must
exit 0, must say which half it skipped, must still fail on a truncated rule, and must
still have examined every payload rule. Asserting only the exit code would be
satisfied by a version that returns 0 unconditionally, which is the regression these
tests exist to make loud, and the mutation run proved it is reachable: with the
`live_files` seeding removed from `scan()` the domain examined nothing on every runner
and the selftest stayed green.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "tools" / "audit" / "rules_sync.py"
ABSENT = "/nonexistent-live-rules-tree-for-pytest"


def _load():
    """Load by path. tools/ is not a package, the same reason mutate.py loads by path."""
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


def _res(mod, live_dir: str, **over) -> dict:
    d = {"payload_dir": str(mod.PAYLOAD), "live_dir": live_dir, "counted": 1,
         "shrink_checked": 1, "only_payload": [], "only_live": [], "differing": [],
         "shrunk": []}
    d.update(over)
    return d


def test_absent_live_tree_is_not_a_failure(rs):
    """The CI condition. A runner has no deployed harness, which is correct."""
    assert _report(rs, _res(rs, ABSENT))[0] == 0


def test_absent_live_tree_names_the_half_it_skipped(rs):
    """A pass whose reduced scope is invisible is worse than a fail."""
    _, text = _report(rs, _res(rs, ABSENT))
    assert "SKIP drift" in text
    assert ABSENT in text


def test_truncated_rule_still_fails_with_no_live_tree(rs):
    """Shrink is the half that would have caught 2bb97a8, and it runs anywhere."""
    code, text = _report(rs, _res(rs, ABSENT, shrunk=[
        {"rule": "boundary-contracts.md", "now": 488, "max": 5557,
         "ratio": 0.088, "max_at": "146cb7b4"}]))
    assert code == 1
    assert "boundary-contracts.md" in text


def test_drift_still_fails_where_a_live_tree_exists(rs, tmp_path):
    """The correction must not have widened anything on the host that can measure it."""
    res = _res(rs, str(tmp_path),
               differing=[{"rule": "z.md", "payload_bytes": 1, "live_bytes": 2}])
    assert _report(rs, res)[0] == 1


def test_an_empty_live_directory_is_not_an_absent_one(rs, tmp_path):
    """Absent means never deployed here. Empty means deployed and then destroyed.

    Decided inside scan(), so this probes scan() rather than a synthetic dict.
    """
    n_payload = len(list(rs.PAYLOAD.glob("*.md")))
    assert n_payload > 0, "no payload rules, so every assertion here would be vacuous"

    saved = rs.LIVE
    try:
        rs.LIVE = tmp_path
        empty = rs.scan()
        rs.LIVE = Path(ABSENT)
        absent = rs.scan()
    finally:
        rs.LIVE = saved

    assert len(empty["only_payload"]) == n_payload
    assert _report(rs, empty)[0] == 1
    assert absent["only_payload"] == []


def test_shrink_examines_every_payload_rule_with_no_live_tree(rs):
    """The assertion that a survived mutation showed was missing.

    An empty `shrunk` is both the healthy answer and the answer a dead loop gives.
    Only the count separates them, which is why scan() reports one.
    """
    saved = rs.LIVE
    try:
        rs.LIVE = Path(ABSENT)
        res = rs.scan()
    finally:
        rs.LIVE = saved
    n_payload = len(list(rs.PAYLOAD.glob("*.md")))
    assert n_payload > 0
    assert res["shrink_checked"] == n_payload


def test_the_floor_brackets_the_incident_on_both_sides(rs):
    """Below 0.088 the incident passes; above 0.90 the legitimate trims fail."""
    assert 488 < 5557 * rs.SHRINK_FLOOR, "2bb97a8 would not be caught"
    assert 0.90 * 5557 >= 5557 * rs.SHRINK_FLOOR, "healthy trims would be flagged"
