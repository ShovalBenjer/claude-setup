"""Tests for tools/slop_lint.py, the prose gate (ADR-0005 rule 7).

The gate exits 1 on any hit, so the properties that matter are: every banned
category fires on its own representative, clean prose stays clean, and the line
number reported is the one a reader would look at to fix it. The prose-metrics
collector is tested in tests/test_prose_metrics.py; here we only assert that it
never fails the run, because a broken collector that starts rejecting prose the
gate itself has no rule against is the failure its own docstring names.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "slop_lint_under_test", ROOT / "tools" / "slop_lint.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


sl = _load()


class TestScanBannedPhrases:
    def test_each_banned_phrase_fires(self):
        samples = [
            "We must delve into the specifics.",
            "a rich tapestry of options",
            "It's worth noting that the test passed.",
            "In today's fast-paced world, speed matters.",
            "navigating the landscape of deployment",
            "unlocking the potential of automation",
            "at the end of the day it works",
            "a testament to the team's effort",
            "in the realm of testing",
            "plays a crucial role in the pipeline",
            "fostering collaboration across teams",
            "the seamlessly integrated solution",
            "a robust solution for deployment",
            "the ever-evolving codebase",
            "harnessing the power of tests",
            "this empowers developers to ship",
            "cutting-edge technology in practice",
            "stands as a pillar of quality",
            "this underscores the need for tests",
        ]
        for sample in samples:
            hits = sl.scan(sample)
            phrases = [h for h in hits if h[0] == "phrase"]
            assert len(phrases) >= 1, f"missed banned phrase in: {sample}"

    def test_clean_prose_has_no_phrase_hits(self):
        clean = "The gate ran and exited zero. 435 tests passed across the root suite."
        assert [h for h in sl.scan(clean) if h[0] == "phrase"] == []


class TestScanDash:
    def test_spaced_em_dash_fires(self):
        hits = sl.scan("The map is generated — a hand edit reads as drift.")
        dashes = [h for h in hits if h[0] == "em/en-dash"]
        assert len(dashes) == 1

    def test_spaced_en_dash_fires(self):
        hits = sl.scan("Ran the gate – it passed.")
        dashes = [h for h in hits if h[0] == "em/en-dash"]
        assert len(dashes) == 1

    def test_unspaced_dash_does_not_fire(self):
        hits = sl.scan("Pages 12—14 of the spec.")
        assert [h for h in hits if h[0] == "em/en-dash"] == []

    def test_hyphen_does_not_fire(self):
        hits = sl.scan("The read-only sweep found 261 dead paths.")
        assert [h for h in hits if h[0] == "em/en-dash"] == []


class TestScanRitual:
    def test_second_person_praise_fires(self):
        for phrase in (
            "You're right, the fix is correct.",
            "That's correct, I changed it.",
            "Good catch on the missing comma.",
            "My apologies for the oversight.",
        ):
            hits = sl.scan(phrase)
            rituals = [h for h in hits if h[0] == "ritual"]
            assert len(rituals) >= 1, f"missed ritual in: {phrase}"

    def test_evaluative_opener_fires(self):
        for opener in ("Perfect.", "Great!", "Excellent,", "Absolutely.", "Exactly!"):
            text = opener + " The tests pass."
            hits = sl.scan(text)
            rituals = [h for h in hits if h[0] == "ritual"]
            assert len(rituals) >= 1, f"missed opener: {opener}"

    def test_mid_sentence_adjective_does_not_fire(self):
        hits = sl.scan("The lto setting is perfect for this, verified by benchmark.")
        assert [h for h in hits if h[0] == "ritual"] == []


class TestScanLineNumbers:
    def test_hit_reports_correct_line_number(self):
        text = "Line one is clean.\nLine two is clean.\nWe delve into nonsense."
        hits = sl.scan(text)
        assert len(hits) == 1
        kind, frag, line = hits[0]
        assert line == 3
        assert "delve" in frag.lower()

    def test_multiple_hits_on_different_lines(self):
        text = "We delve here.\n\n\nAnd we seamlessly integrate there."
        hits = sl.scan(text)
        lines = sorted(h[2] for h in hits)
        assert lines[0] == 1
        assert lines[-1] == 4


class TestScanClean:
    def test_fully_clean_text(self):
        text = (
            "The gate ran on the current tree and exited zero. "
            "Root suite: 650 passed, 31 skipped, 1 xfailed. "
            "The codemap was regenerated after staging."
        )
        assert sl.scan(text) == []


class TestLogProse:
    def test_short_documents_are_skipped(self):
        result = sl.log_prose("test.md", "A few words only.")
        assert result is None

    def test_slop_no_log_prevents_file_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SLOP_NO_LOG", "1")
        long_text = ("This is a sentence with enough words. " * 50)
        result = sl.log_prose("test.md", long_text)
        assert result is not None
        assert "words" in result

    def test_collector_never_fails_the_run(self, monkeypatch):
        monkeypatch.setattr(sl, "SCORES", "/nonexistent/path/scores.jsonl")
        monkeypatch.delenv("SLOP_NO_LOG", raising=False)
        result = sl.log_prose("test.md", "Short.")
        assert result is None


class TestMainExitCode:
    def test_clean_file_exits_zero(self, tmp_path):
        f = tmp_path / "clean.md"
        f.write_text("The gate ran and exited zero. All tests passed.", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "slop_lint.py"), str(f)],
            capture_output=True, text=True,
            env={**os.environ, "SLOP_NO_LOG": "1"}, timeout=30)
        assert proc.returncode == 0

    def test_sloppy_file_exits_one(self, tmp_path):
        f = tmp_path / "sloppy.md"
        f.write_text("We must delve into the details of this approach.", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "slop_lint.py"), str(f)],
            capture_output=True, text=True,
            env={**os.environ, "SLOP_NO_LOG": "1"}, timeout=30)
        assert proc.returncode == 1
        assert "delve" in proc.stdout.lower()

    def test_multiple_files_accumulate_hits(self, tmp_path):
        f1 = tmp_path / "a.md"
        f1.write_text("We delve here.", encoding="utf-8")
        f2 = tmp_path / "b.md"
        f2.write_text("Clean prose only.", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "slop_lint.py"), str(f1), str(f2)],
            capture_output=True, text=True,
            env={**os.environ, "SLOP_NO_LOG": "1"}, timeout=30)
        assert proc.returncode == 1
