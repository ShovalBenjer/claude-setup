"""Tests for done_gate.py: the mechanical anti-fake-completion gate (craft/completion research §Q1/Q5).

Enforces "done means wired + workflow-proven + evidence", not "commit + tests green". The pure
checklist logic (done_verdict), top-level public-symbol extraction (via stdlib ast, no methods),
ref-counting, TODO detection, and the zero-caller unwired check are unit-tested; unwired detection is
also exercised on a real tmp package. No mocks.
"""
from __future__ import annotations

from intent_control_plane.done_gate import (
    count_symbol_refs,
    done_verdict,
    todo_hits,
    top_level_public_defs,
    unwired_public_symbols,
)


def test_top_level_public_defs_excludes_methods_and_private():
    source = "def foo():\n    pass\n\nclass Bar:\n    def method(self):\n        pass\n\ndef _hidden():\n    pass\n"
    assert top_level_public_defs(source) == ["foo", "Bar"]  # no method, no _hidden


def test_top_level_public_defs_survives_syntax_error():
    assert top_level_public_defs("def (:::") == []


def test_count_symbol_refs():
    assert count_symbol_refs("foo", ["def foo(): pass", "foo()\nfoo()"]) == 3  # 1 def + 2 calls


def test_done_verdict_all_pass():
    checks = {"tests_green": True, "types_clean": True, "lint_clean": True,
              "unwired": [], "todos": [], "smoke_present": True}
    assert done_verdict(checks) == {"done": True, "failing": []}


def test_done_verdict_fails_on_unwired_and_todos():
    checks = {"tests_green": True, "types_clean": True, "lint_clean": True,
              "unwired": ["persona_scorecard"], "todos": ["x.py:3"], "smoke_present": False}
    verdict = done_verdict(checks)
    assert verdict["done"] is False
    assert any("unwired" in f for f in verdict["failing"])
    assert any("todos" in f for f in verdict["failing"])
    assert "smoke_present" in verdict["failing"]


def test_todo_hits(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1  # TODO: integrate\ndef f():\n    pass  # FIXME later\n")
    hits = todo_hits(tmp_path)
    assert len(hits) == 2


def test_unwired_public_symbols_flags_zero_caller(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("def used():\n    return 1\n\ndef orphan():\n    return 2\n")
    (src / "b.py").write_text("from a import used\n\nresult = used()\n")
    result = unwired_public_symbols(tmp_path)
    assert "orphan" in result  # never called -> scaffold
    assert "used" not in result  # called in b.py -> wired
