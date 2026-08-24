"""Tests for cache.py: the semantic cache (P2, the biggest untapped speed lever).

cache_key is pure (sha256 of a whitespace-normalized, lowercased, kind-prefixed payload);
CacheStore is the only I/O, one jsonl ledger per Path, mirroring archive.append_variant /
policy.append_telemetry. TTL freshness is driven entirely by an injected now_ts string (no
internal clock call beyond util.utc_now at put() time), so expiry is deterministic to test.
"""
from __future__ import annotations

from intent_control_plane.cache import CacheStore, cache_key, is_fresh


def test_cache_key_is_deterministic():
    assert cache_key("llm", "hello world") == cache_key("llm", "hello world")


def test_cache_key_normalizes_whitespace_and_case():
    a = cache_key("llm", "  Hello   World  ")
    b = cache_key("llm", "hello world")
    assert a == b


def test_cache_key_is_a_sha256_hex_digest():
    key = cache_key("llm", "hello world")
    assert len(key) == 64
    int(key, 16)  # raises ValueError if not valid hex


def test_cache_key_kind_prefix_changes_the_key():
    assert cache_key("llm", "hello world") != cache_key("tool", "hello world")


def test_put_get_roundtrip(tmp_path):
    store = CacheStore(tmp_path / "cache.jsonl")
    key = cache_key("llm", "what is 2+2")
    store.put(key, "4", ttl_seconds=60, now_ts="2026-07-11T12:00:00Z")
    assert store.get(key, now_ts="2026-07-11T12:00:30Z") == "4"


def test_ttl_expiry_returns_none_when_stale(tmp_path):
    store = CacheStore(tmp_path / "cache.jsonl")
    key = cache_key("llm", "old question")
    store.put(key, "stale-answer", ttl_seconds=30, now_ts="2026-07-11T12:00:00Z")
    # 5 minutes later, ttl was only 30s -> expired, must miss (not return stale data)
    assert store.get(key, now_ts="2026-07-11T12:05:00Z") is None


def test_get_miss_returns_none_for_unknown_key(tmp_path):
    store = CacheStore(tmp_path / "cache.jsonl")
    assert store.get("no-such-key", now_ts="2026-07-11T12:00:00Z") is None


def test_stats_counts_hits_and_misses(tmp_path):
    store = CacheStore(tmp_path / "cache.jsonl")
    key = cache_key("llm", "q")
    store.put(key, "a", ttl_seconds=60, now_ts="2026-07-11T12:00:00Z")
    assert store.get(key, now_ts="2026-07-11T12:00:10Z") == "a"  # hit
    assert store.get("missing", now_ts="2026-07-11T12:00:10Z") is None  # miss
    assert store.get(key, now_ts="2026-07-11T13:00:10Z") is None  # expired -> miss
    assert store.stats() == {"hits": 1, "misses": 2}


def test_malformed_jsonl_line_is_skipped(tmp_path):
    path = tmp_path / "cache.jsonl"
    store = CacheStore(path)
    key = cache_key("llm", "q")
    store.put(key, "a", ttl_seconds=60, now_ts="2026-07-11T12:00:00Z")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
    assert store.get(key, now_ts="2026-07-11T12:00:05Z") == "a"


def test_put_overwrites_earlier_value_for_same_key(tmp_path):
    store = CacheStore(tmp_path / "cache.jsonl")
    key = cache_key("llm", "q")
    store.put(key, "first", ttl_seconds=60, now_ts="2026-07-11T12:00:00Z")
    store.put(key, "second", ttl_seconds=60, now_ts="2026-07-11T12:00:05Z")
    assert store.get(key, now_ts="2026-07-11T12:00:06Z") == "second"


def test_is_fresh_true_within_ttl_false_after():
    entry = {"ts": "2026-07-11T12:00:00Z", "ttl_seconds": 60}
    assert is_fresh(entry, "2026-07-11T12:00:59Z") is True
    assert is_fresh(entry, "2026-07-11T12:01:01Z") is False
