"""Tests for spawn_grade.py: A5, close the transmission gap (spawn -> guardrails -> archive).

grade_spawn is what the live gastown-spawn calls after each run: it screens the diff through the
guardrails (scoped-diff + reward-hacking), scores it against a rubric when one is provided, and
writes the outcome to the population archive as a variant, so the company layer can grade personas
from real spawn results. Real archive jsonl (tmp), no mocks.
"""
from __future__ import annotations

import io
import json
import sys

from intent_control_plane.archive import read_variants
from intent_control_plane.spawn_grade import _main, grade_spawn

CRITERIA = [
    {"name": "tests_pass", "weight": 1.0, "kind": "deterministic"},
    {"name": "craft", "weight": 1.0, "kind": "judge"},
]

SCOPED_CLEAN = (
    "diff --git a/mod.py b/mod.py\n@@ -1,2 +1,3 @@\n def f():\n-    return 1\n+    return 2\n"
)


def test_grade_spawn_rejects_reward_hacking_even_with_good_results(tmp_path):
    arch = tmp_path / "v.jsonl"
    gamed = "diff --git a/test_x.py b/test_x.py\n@@ -1,2 +1,1 @@\n-    assert compute() == 42\n+    compute()\n"
    out = grade_spawn("task-1", "Engineering Firm", "haiku", gamed,
                      criteria=CRITERIA, results={"tests_pass": 1.0, "craft": 0.95}, archive_path=arch)
    assert out["verdict"] == "rejected-guardrail"
    assert out["flags"]  # reward-hacking flags present
    assert len(read_variants(arch)) == 1  # still archived as a (rejected) stepping stone


def test_grade_spawn_rejects_unscoped_full_rewrite(tmp_path):
    arch = tmp_path / "v.jsonl"
    rewrite = "diff --git a/big.py b/big.py\n" + "\n".join(f"-old {i}" for i in range(200))
    out = grade_spawn("task-2", "Engineering Firm", "haiku", rewrite,
                      criteria=CRITERIA, results={"tests_pass": 1.0, "craft": 0.9}, archive_path=arch)
    assert out["verdict"] == "rejected-guardrail"
    assert out["scoped"] is False


def test_grade_spawn_keeps_clean_scoped_diff_with_good_rubric(tmp_path):
    arch = tmp_path / "v.jsonl"
    out = grade_spawn("task-3", "Engineering Firm", "sonnet", SCOPED_CLEAN,
                      criteria=CRITERIA, results={"tests_pass": 1.0, "craft": 0.8}, baseline=None, archive_path=arch)
    assert out["verdict"] == "kept"
    assert out["score"] == round((1.0 + 0.8) / 2.0, 4)
    assert read_variants(arch)[0]["verdict"] == "kept"


def test_grade_spawn_disposes_deterministic_failure(tmp_path):
    arch = tmp_path / "v.jsonl"
    out = grade_spawn("task-4", "Engineering Firm", "haiku", SCOPED_CLEAN,
                      criteria=CRITERIA, results={"tests_pass": 0.0, "craft": 0.99}, archive_path=arch)
    assert out["verdict"] == "rejected"  # tests failed -> disposed regardless of craft


def test_grade_spawn_without_rubric_records_screened_only(tmp_path):
    arch = tmp_path / "v.jsonl"
    out = grade_spawn("task-5", "Product Studio", "haiku", SCOPED_CLEAN, archive_path=arch)
    assert out["verdict"] == "scored"  # screened, un-judged (no rubric supplied)
    assert len(read_variants(arch)) == 1


def test_grade_spawn_criteria_without_results_fails_closed(tmp_path):
    # audit #12 (Codex-flagged): a grading intent that cannot run (criteria present, results
    # missing) must reject, not silently degrade to the pass-through 'scored'.
    arch = tmp_path / "v.jsonl"
    out = grade_spawn("task-6", "Engineering Firm", "haiku", SCOPED_CLEAN,
                      criteria=CRITERIA, results=None, archive_path=arch)
    assert out["verdict"] == "rejected"
    assert "missing-results" in read_variants(arch)[0]["failure_tags"]


def test_main_empty_diff_returns_empty_verdict(tmp_path, monkeypatch, capsys):
    # H10: _main is the only production entrypoint (called by gastown-spawn); it was never tested.
    arch = tmp_path / "v.jsonl"
    monkeypatch.setattr(sys, "stdin", io.StringIO("   \n"))
    code = _main(["--subject", "task-7", "--persona", "Engineering Firm", "--archive-path", str(arch)])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == {"verdict": "empty", "score": 0.0}
    assert not arch.exists()  # empty diff is not archived


def test_main_grades_and_archives_real_diff(tmp_path, monkeypatch, capsys):
    arch = tmp_path / "v.jsonl"
    monkeypatch.setattr(sys, "stdin", io.StringIO(SCOPED_CLEAN))
    code = _main(["--subject", "task-8", "--persona", "Engineering Firm", "--archive-path", str(arch)])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "scored"
    variants = read_variants(arch)
    assert len(variants) == 1
    assert variants[0]["subject"] == "task-8"
    assert variants[0]["verdict"] == "scored"
