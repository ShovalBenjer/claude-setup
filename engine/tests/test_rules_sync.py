"""Oracle for tools/audit/rules_sync.py's check() adapter (item 2, docs/taste.md
2026-08-24 "global rule-enforcement oracle" migration).

THE TRAP THIS FILE PINS

rules_sync.py's report() is not a thin printer over scan()'s dict: it branches on
`live_present` (Path(res["live_dir"]).is_dir()) and SKIPS the three drift categories
(only_payload, only_live, differing) entirely when no live ~/.claude/rules tree
exists — the CI case, and the exact regression this file's own docstring records
(SKIP drift, still run shrink, say which half ran; a domain that silently checks
half of what its name implies is worse than one that fails).

A naive check() that converts scan()'s raw dict straight to Finding objects would
emit drift findings on every CI runner that report() would have suppressed. The
tests below verify check() and report() agree on problem COUNT in both states —
live tree present, live tree absent — using synthetic scan() results the same way
selftest()'s own _quiet_report() cases do, so this does not depend on this
machine's actual ~/.claude/rules existing or not.
"""
from __future__ import annotations

import io
import sys
import contextlib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "audit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import rules_sync as RS  # noqa: E402


def _quiet_report_count(res: dict) -> int:
    """How many problems report() prints for this scan() result, counted from its
    own return code semantics is not enough (it's just 0 or 1); count printed FAIL
    lines instead, the same signal report()'s own problems counter uses."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        RS.report(res)
    return buf.getvalue().count("FAIL ")


class CheckAgreesWithReportLiveTreePresent(unittest.TestCase):
    def _res(self, live_dir, **overrides):
        base = {"payload_dir": "/x", "live_dir": live_dir, "counted": 1,
                "only_payload": [], "only_live": [], "differing": [], "shrunk": []}
        base.update(overrides)
        return base

    def test_only_payload_counted_when_live_present(self):
        with mock.patch.object(RS, "scan", return_value=self._res(
                "/tmp", only_payload=["x.md"])):
            findings = RS.check()
        res = self._res("/tmp", only_payload=["x.md"])
        self.assertEqual(len(findings), _quiet_report_count(res))
        self.assertEqual(len(findings), 1)

    def test_differing_carries_byte_counts_in_meta(self):
        d = [{"rule": "z.md", "payload_bytes": 10, "live_bytes": 20}]
        with mock.patch.object(RS, "scan", return_value=self._res("/tmp", differing=d)):
            findings = RS.check()
        self.assertEqual(findings[0].meta["payload_bytes"], 10)
        self.assertEqual(findings[0].meta["live_bytes"], 20)

    def test_shrunk_carries_ratio_in_meta(self):
        s = [{"rule": "w.md", "now": 488, "max": 5557, "ratio": 0.09, "max_at": "146cb7b4"}]
        with mock.patch.object(RS, "scan", return_value=self._res("/tmp", shrunk=s)):
            findings = RS.check()
        self.assertEqual(findings[0].meta["ratio"], 0.09)
        self.assertEqual(findings[0].severity, "high")


class CheckAgreesWithReportNoLiveTree(unittest.TestCase):
    """The trap: with no live directory, report() skips drift. check() must too."""

    def _res_no_live(self, **overrides):
        base = {"payload_dir": "/x", "live_dir": "/definitely-does-not-exist-anywhere",
                "counted": 1, "only_payload": [], "only_live": [], "differing": [],
                "shrunk": []}
        base.update(overrides)
        return base

    def test_only_payload_NOT_counted_without_live_tree(self):
        res = self._res_no_live(only_payload=["x.md"])
        with mock.patch.object(RS, "scan", return_value=res):
            findings = RS.check()
        self.assertEqual(_quiet_report_count(res), 0, "report() must suppress this")
        self.assertEqual(len(findings), 0, "check() must agree and suppress it too")

    def test_differing_NOT_counted_without_live_tree(self):
        d = [{"rule": "z.md", "payload_bytes": 1, "live_bytes": 2}]
        res = self._res_no_live(differing=d)
        with mock.patch.object(RS, "scan", return_value=res):
            findings = RS.check()
        self.assertEqual(_quiet_report_count(res), 0)
        self.assertEqual(len(findings), 0)

    def test_shrunk_IS_counted_without_live_tree(self):
        # The half that still runs on CI: shrink is host-independent.
        s = [{"rule": "w.md", "now": 488, "max": 5557, "ratio": 0.09, "max_at": "146cb7b4"}]
        res = self._res_no_live(shrunk=s)
        with mock.patch.object(RS, "scan", return_value=res):
            findings = RS.check()
        self.assertEqual(_quiet_report_count(res), 1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].checker, "rules_sync.shrunk")


class CheckAgainstRealRepoScan(unittest.TestCase):
    """One check against the tool's own real scan(), not a mock, so a change to
    scan()'s field names breaks this test rather than only the mocked ones above."""

    def test_check_runs_against_real_scan_without_raising(self):
        findings = RS.check()
        self.assertIsInstance(findings, list)
        for f in findings:
            self.assertIn(f.severity, ("high", "medium", "low"))


if __name__ == "__main__":
    unittest.main()
