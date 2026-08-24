"""Tests for context-pack memory decay/entropy: recency weight, novelty dedup, combined rank."""
from __future__ import annotations

from intent_control_plane.text_index import (
    dedup_key,
    rank_by_relevance_and_recency,
    recency_weight,
)


def test_recency_weight_halves_at_half_life():
    assert recency_weight("2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z") == 1.0  # now -> 1
    assert abs(recency_weight("2026-07-01T00:00:00Z", "2026-07-15T00:00:00Z") - 0.5) < 1e-9  # +14d
    assert recency_weight("2026-08-01T00:00:00Z", "2026-07-01T00:00:00Z") == 1.0  # future -> no penalty


def test_recency_weight_bad_timestamp_is_no_penalty():
    assert recency_weight("garbage", "2026-07-01T00:00:00Z") == 1.0
    assert recency_weight("2026-07-01T00:00:00Z", "") == 1.0


def test_dedup_key_normalizes_and_truncates():
    assert dedup_key("  Hello   WORLD  ") == "hello world"
    assert dedup_key("abc" * 100)[:3] == "abc"
    assert len(dedup_key("x" * 200)) == 60


def test_rank_prefers_fresher_when_relevance_equal():
    old = {"model_text": "deploy the widget", "repo_path": "r", "timestamp_utc": "2026-06-01T00:00:00Z"}
    new = {"model_text": "deploy the widget", "repo_path": "r", "timestamp_utc": "2026-07-01T00:00:00Z"}
    ranked = rank_by_relevance_and_recency([old, new], "deploy widget", "2026-07-02T00:00:00Z")
    assert ranked[0] is new  # equal relevance, fresher wins
    assert ranked[1] is old


def test_rank_relevance_still_beats_recency_when_the_fresh_row_is_irrelevant():
    stale_relevant = {"model_text": "deploy the widget dashboard now", "repo_path": "r", "timestamp_utc": "2026-05-01T00:00:00Z"}
    fresh_irrelevant = {"model_text": "unrelated chatter", "repo_path": "r", "timestamp_utc": "2026-07-02T00:00:00Z"}
    ranked = rank_by_relevance_and_recency(
        [fresh_irrelevant, stale_relevant], "deploy widget dashboard", "2026-07-02T00:00:00Z"
    )
    assert ranked[0] is stale_relevant  # zero-relevance fresh row never wins
