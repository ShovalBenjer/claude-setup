"""Tests for archive.py: the population store (DGM/ShinkaEvolve/Self-Harness mechanics).

The archive is the shared spine for the depth engine (stepping-stone variants) and the company
layer (benched personas). Pure decision logic (record, parent selection, keep gate, novelty) is
unit + property tested; append/read is the only I/O (jsonl, mirrors policy.append_telemetry).
"""
from __future__ import annotations

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from intent_control_plane.archive import (
    append_variant,
    is_novel,
    keep_verdict,
    read_variants,
    select_parents,
    variant_record,
)


def _variant(vid: str, score: float) -> dict:
    return variant_record(subject="artifact-x", persona="Engineering Firm", model="haiku", score=score) | {
        "variant_id": vid
    }


def test_variant_record_has_required_fields():
    row = variant_record(subject="art", persona="Product Studio", model="sonnet", score=0.8)
    for key in ("variant_id", "ts", "subject", "persona", "model", "score", "verdict", "failure_tags"):
        assert key in row
    assert row["score"] == 0.8
    assert row["failure_tags"] == []


def test_select_parents_full_exploitation_returns_top_elites():
    pool = [_variant("a", 0.9), _variant("b", 0.2), _variant("c", 0.7)]
    picked = select_parents(pool, k=2, exploitation_ratio=1.0, rng=random.Random(0))
    assert [v["variant_id"] for v in picked] == ["a", "c"]  # the two highest scores, in order


def test_select_parents_keeps_weak_stepping_stones_eligible():
    # exploitation_ratio 0 with k == len(pool): every variant is eligible, weak ones included.
    pool = [_variant("a", 0.9), _variant("b", 0.01), _variant("c", 0.5)]
    picked = select_parents(pool, k=3, exploitation_ratio=0.0, rng=random.Random(1))
    assert {v["variant_id"] for v in picked} == {"a", "b", "c"}


def test_select_parents_empty_or_nonpositive_k():
    assert select_parents([], k=3, exploitation_ratio=0.5, rng=random.Random(0)) == []
    assert select_parents([_variant("a", 0.5)], k=0, exploitation_ratio=0.5, rng=random.Random(0)) == []


@given(
    scores=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=12),
    k=st.integers(min_value=1, max_value=12),
    ratio=st.floats(min_value=0.0, max_value=1.0),
    seed=st.integers(min_value=0, max_value=9999),
)
def test_select_parents_returns_k_unique_from_pool(scores, k, ratio, seed):
    pool = [_variant(f"v{i}", s) for i, s in enumerate(scores)]
    picked = select_parents(pool, k=k, exploitation_ratio=ratio, rng=random.Random(seed))
    ids = [v["variant_id"] for v in picked]
    assert len(ids) == min(k, len(pool))
    assert len(set(ids)) == len(ids)  # no duplicates
    assert set(ids) <= {v["variant_id"] for v in pool}  # only from the pool


def test_keep_verdict_keeps_when_better_and_no_regression():
    assert keep_verdict(0.8, baseline=0.6, held_out=[0.7, 0.9], held_out_baselines=[0.7, 0.85]) == "kept"


def test_keep_verdict_rejects_on_held_out_regression():
    # improves on the targeted score but regresses a neighbor -> rejected (the #1 self-improve trap)
    assert keep_verdict(0.9, baseline=0.6, held_out=[0.5], held_out_baselines=[0.8]) == "rejected"


def test_keep_verdict_rejects_when_not_better():
    assert keep_verdict(0.6, baseline=0.6) == "rejected"


def test_keep_verdict_first_run_no_baseline_keeps():
    assert keep_verdict(0.4, baseline=None) == "kept"


def test_keep_verdict_held_out_is_keyword_only():
    # audit #13: held_out and held_out_baselines are same-typed; passed positionally a caller can
    # swap them and silently invert the regression gate. Keyword-only makes the swap a TypeError.
    with pytest.raises(TypeError):
        keep_verdict(0.9, 0.6, [0.5], [0.8])


def test_keep_verdict_rejects_on_held_out_length_mismatch():
    # Codex follow-up to #13: zip(strict=False) silently truncated an unpaired held-out case, so a
    # regression in the extra case was ignored and the variant kept. A mismatch cannot be verified.
    assert keep_verdict(0.9, baseline=0.6, held_out=[0.9, 0.5], held_out_baselines=[0.8]) == "rejected"


def test_is_novel_rejects_near_duplicate_accepts_different():
    prior = ["the boundary contract needs typed dtos and a 502 on bad upstream json"]
    assert is_novel(prior[0], prior) is False  # identical -> not novel
    assert is_novel("switch the button colour token to azure and add a skeleton loader", prior) is True


def test_append_and_read_variants_roundtrip(tmp_path):
    log = tmp_path / "variants.jsonl"
    append_variant(_variant("a", 0.5), log)
    append_variant(_variant("b", 0.9), log)
    log.write_text(log.read_text() + "not-json\n")  # a malformed line must be skipped, not fatal
    rows = read_variants(log)
    assert [r["variant_id"] for r in rows] == ["a", "b"]
