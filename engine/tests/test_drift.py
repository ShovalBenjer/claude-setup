"""Pytest wrapper over the drift sentinel's own selftest.

The selftest is the oracle; this makes the root suite (and CI's unit domain)
fail when it fails, the wiring gap the 2026-08-12 corpus audit flagged for
tools/corpus. One test per named check so a regression is attributable.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "drift"))
from drift import selftest_checks  # noqa: E402

with tempfile.TemporaryDirectory() as _tmp:
    _CHECKS = selftest_checks(Path(_tmp))


@pytest.mark.parametrize("name,ok", _CHECKS, ids=[n for n, _ in _CHECKS])
def test_drift_selftest(name, ok):
    assert ok, name
