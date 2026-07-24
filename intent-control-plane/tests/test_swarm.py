"""Tests for swarm.py: one depth round scoring candidate passes against the decomposed rubric.

swarm_pass ties the pieces together: score each candidate (rubric), keep only those that beat the
running baseline and are not near-duplicates, dispose any that fail a deterministic check, and
archive EVERY variant (kept and rejected) so weak ones survive as stepping stones (DGM). Candidates
are plain dicts (real fixtures, no mocks); the archive is a real tmp jsonl. gradient_flat is the
pure stop condition for the multi-round loop.
"""
from __future__ import annotations

from intent_control_plane.archive import read_variants
from intent_control_plane.swarm import gradient_flat, swarm_pass

CRITERIA = [
    {"name": "tests_pass", "weight": 1.0, "kind": "deterministic"},
    {"name": "craft", "weight": 1.0, "kind": "judge"},
]


def _cand(content: str, tests: float, craft: float, persona: str = "Engineering Firm") -> dict:
    return {"persona": persona, "model": "haiku", "content": content, "results": {"tests_pass": tests, "craft": craft}}


def test_swarm_keeps_better_rejects_worse(tmp_path):
    arch = tmp_path / "variants.jsonl"
    candidates = [
        _cand("a first pass at the parser", 1.0, 0.5),        # 0.75 -> kept (baseline was None)
        _cand("a worse regressed parser attempt", 1.0, 0.3),  # 0.65 -> rejected (< 0.75)
        _cand("a much better parser with all edge cases handled", 1.0, 0.9),  # 0.95 -> kept
    ]
    summary = swarm_pass("artifact-1", candidates, CRITERIA, baseline=None, archive_path=arch)
    assert summary["kept"] == 2
    assert summary["rejected"] == 1
    assert summary["best_score"] == round((1.0 + 0.9) / 2.0, 4)


def test_swarm_disposes_deterministic_failure(tmp_path):
    arch = tmp_path / "variants.jsonl"
    candidates = [
        _cand("passes tests, decent craft", 1.0, 0.4),
        _cand("gorgeous but the tests fail", 0.0, 0.99),  # disposed despite craft 0.99
    ]
    summary = swarm_pass("a2", candidates, CRITERIA, archive_path=arch)
    assert summary["kept"] == 1


def test_swarm_rejects_near_duplicate(tmp_path):
    arch = tmp_path / "variants.jsonl"
    text = "refactor the boundary contract with typed dtos and a 502 on bad upstream json"
    candidates = [_cand(text, 1.0, 0.9), _cand(text, 1.0, 0.95)]  # identical content -> 2nd not novel
    summary = swarm_pass("a3", candidates, CRITERIA, archive_path=arch)
    assert summary["kept"] == 1


def test_swarm_archives_all_variants_including_stepping_stones(tmp_path):
    arch = tmp_path / "variants.jsonl"
    candidates = [_cand("a good pass here", 1.0, 0.9), _cand("a weak stepping stone attempt", 1.0, 0.1)]
    swarm_pass("a4", candidates, CRITERIA, archive_path=arch)
    rows = read_variants(arch)
    assert len(rows) == 2  # the weak/rejected variant is retained, not pruned
    assert {r["verdict"] for r in rows} == {"kept", "rejected"}


def test_gradient_flat_stop_condition():
    assert gradient_flat([0.5, 0.6, 0.7], patience=2) is False  # still improving
    assert gradient_flat([0.5, 0.7, 0.7, 0.7], patience=2) is True  # no new best in last 2 rounds
    assert gradient_flat([0.9], patience=2) is False  # not enough history
