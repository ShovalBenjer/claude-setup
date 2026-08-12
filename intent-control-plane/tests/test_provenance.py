"""Tests for provenance.py: fix-commit provenance (SZZ + JIT risk + per-persona survival).

Layer 0 feeds the company scorecard. The pure heuristics (classify, jit_risk, szz_link,
survival_rate, persona_provenance) are unit-tested with real commit fixtures; git_log is smoke-
tested against THIS repo's real history (no mocks, real git). Kills LOC-as-productivity: the
persona rollup reports rework ratio and net (rework-adjusted) feature throughput, not line counts.
"""
from __future__ import annotations

from pathlib import Path

from intent_control_plane.provenance import (
    classify_commit,
    git_log,
    jit_risk,
    parse_git_log,
    persona_provenance,
    survival_rate,
    szz_link,
)


def test_classify_commit_conventional_and_keywords():
    assert classify_commit("fix(cs-agent): harden the prompt") == "fix"
    assert classify_commit("feat(depth-harness): S5 routing") == "feat"
    assert classify_commit("refactor: simplify the parser") == "refactor"
    assert classify_commit("chore(repo): ignore clutter") == "chore"
    assert classify_commit('revert "feat: bad idea"') == "fix"
    assert classify_commit("random thought") == "other"


def test_jit_risk_monotonic_and_bounded():
    low = jit_risk(churn=5, files_touched=1, fix_density=0.0)
    high = jit_risk(churn=800, files_touched=12, fix_density=0.9)
    assert 0.0 <= low <= high <= 1.0
    # more churn raises risk, holding the others fixed
    assert jit_risk(churn=400, files_touched=3, fix_density=0.2) > jit_risk(churn=40, files_touched=3, fix_density=0.2)


def test_szz_link_confidence_weighted_by_owned_lines():
    links = szz_link({"abc123": 3, "def456": 1})
    assert links[0] == {"sha": "abc123", "confidence": 0.75}
    assert links[1] == {"sha": "def456", "confidence": 0.25}
    assert szz_link({}) == []


def test_survival_rate():
    assert survival_rate(added=100, removed_later=25) == 0.75  # 75% of the added lines survived
    assert survival_rate(added=0, removed_later=0) == 0.0


def test_parse_git_log_classifies_each_line():
    text = "sha1\tfeat: add thing\nsha2\tfix: repair thing\n\nsha3\tchore: tidy\n"
    rows = parse_git_log(text)
    assert [r["kind"] for r in rows] == ["feat", "fix", "chore"]
    assert rows[0]["sha"] == "sha1"


def test_persona_provenance_rework_and_net_throughput():
    commits = [
        {"persona": "Engineering Firm", "kind": "feat", "caused_fix": True},
        {"persona": "Engineering Firm", "kind": "feat", "caused_fix": False},
        {"persona": "Engineering Firm", "kind": "feat", "caused_fix": False},
        {"persona": "Engineering Firm", "kind": "fix", "caused_fix": False},
    ]
    card = persona_provenance(commits)["Engineering Firm"]
    assert card["rework_ratio"] == 0.25            # 1 fix of 4 commits
    assert card["net_feature_throughput"] == 2     # 3 feats minus 1 that caused a fix


def test_git_log_reads_this_real_repo():
    """Integration smoke: the parser reads real history, not a fixture.

    It asserts the SHAPE of what parsing returns, deliberately not the CONTENT
    of recent history. The original closing line required a feat commit within
    the last 50, which was a fact about the week's git activity rather than
    about this code: it passed for weeks, then failed CI on 2026-08-12 with
    zero code change after a six-PR merge campaign pushed every feat commit
    past position 50. A unit oracle that a merge can flip is measuring the
    calendar (same class as lesson L-2026-08-07-e, a directory read as the
    product model).
    """
    root = Path(__file__).resolve().parents[1]
    commits = git_log(root, max_count=50)
    assert len(commits) > 0
    allowed = {"feat", "fix", "refactor", "chore", "other"}
    for c in commits:
        assert c["kind"] in allowed, c
        assert c["sha"], c
