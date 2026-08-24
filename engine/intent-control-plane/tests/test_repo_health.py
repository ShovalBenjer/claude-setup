"""Tests for the AI-native LOC-budget checker."""
from __future__ import annotations

from intent_control_plane.repo_health import (
    CLASS_BUDGET,
    FILE_BUDGET,
    FUNC_BUDGET,
    file_findings,
)


def test_clean_file_has_no_findings(tmp_path):
    assert file_findings(tmp_path / "m.py", "def small():\n    return 1\n") == []


def test_flags_long_function_as_hard(tmp_path):
    body = "\n".join(f"    x{i} = {i}" for i in range(FUNC_BUDGET[1] + 5))
    findings = file_findings(tmp_path / "m.py", f"def big():\n{body}\n")
    fn = [f for f in findings if f.kind == "function" and f.name == "big"]
    assert fn and fn[0].loc > FUNC_BUDGET[1]
    assert fn[0].severity == "hard"


def test_flags_large_file(tmp_path):
    src = "\n".join("x = 1" for _ in range(FILE_BUDGET[0] + 10)) + "\n"
    findings = file_findings(tmp_path / "big.py", src)
    assert any(f.kind == "file" for f in findings)


def test_soft_vs_hard_severity(tmp_path):
    body = "\n".join(f"    x{i} = {i}" for i in range(FUNC_BUDGET[0] + 3))  # over soft, under hard
    findings = file_findings(tmp_path / "m.py", f"def midsize():\n{body}\n")
    fn = [f for f in findings if f.kind == "function"]
    assert fn and fn[0].severity == "soft"


def test_class_budget_flagged(tmp_path):
    body = "\n".join(f"    attr_{i} = {i}" for i in range(CLASS_BUDGET[0] + 5))
    findings = file_findings(tmp_path / "m.py", f"class Big:\n{body}\n")
    assert any(f.kind == "class" for f in findings)
