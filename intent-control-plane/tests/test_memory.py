"""Tests for memory.py: typed memory kinds, jsonl store, tf-idf cosine recall.

MemoryStore reuses text_index.term_vector/cosine (the existing lexical scorer), so recall costs
no new dependency. EmbeddingBackend is the pluggable dense-embedding seam for later, tf-idf stays
the default.
"""
from __future__ import annotations

import pytest

from intent_control_plane.memory import EmbeddingBackend, MemoryStore, memory_record


class _FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [float(len(text))]


def test_memory_record_has_required_fields():
    record = memory_record("episodic", "shipped the fix", tags=["deploy"])
    for key in ("memory_id", "kind", "text", "tags", "ts"):
        assert key in record
    assert record["kind"] == "episodic"
    assert record["text"] == "shipped the fix"
    assert record["tags"] == ["deploy"]


def test_memory_record_rejects_unknown_kind():
    with pytest.raises(ValueError):
        memory_record("not_a_real_kind", "text")


def test_put_recall_roundtrip(tmp_path):
    store = MemoryStore(tmp_path / "mem.jsonl")
    record = memory_record("procedural", "run pytest before pushing", tags=["tdd"])
    store.put(record)
    results = store.recall("run pytest before pushing")
    assert len(results) == 1
    assert results[0]["memory_id"] == record["memory_id"]
    assert results[0]["tags"] == ["tdd"]


def test_recall_ranks_relevant_record_first(tmp_path):
    store = MemoryStore(tmp_path / "mem.jsonl")
    store.put(memory_record("episodic", "unrelated chatter about lunch plans"))
    store.put(memory_record("episodic", "boundary contract needs typed dtos and fail closed"))
    results = store.recall("typed dtos boundary contract", k=5)
    assert results[0]["text"] == "boundary contract needs typed dtos and fail closed"


def test_recall_kind_filter(tmp_path):
    store = MemoryStore(tmp_path / "mem.jsonl")
    store.put(memory_record("episodic", "deployed the pipeline to prod"))
    store.put(memory_record("semantic", "pipeline deploy steps require staging first"))
    results = store.recall("pipeline deploy", kind="semantic")
    assert len(results) == 1
    assert results[0]["kind"] == "semantic"


def test_recall_respects_k_limit(tmp_path):
    store = MemoryStore(tmp_path / "mem.jsonl")
    for i in range(10):
        store.put(memory_record("scratchpad", f"note about widget rollout number {i}"))
    results = store.recall("widget rollout", k=3)
    assert len(results) == 3


def test_recall_unknown_log_path_returns_empty(tmp_path):
    store = MemoryStore(tmp_path / "does-not-exist.jsonl")
    assert store.recall("anything") == []


def test_embedding_backend_protocol_shape():
    backend: EmbeddingBackend = _FakeEmbedder()
    assert isinstance(backend, EmbeddingBackend)
    assert backend.embed("hello") == [5.0]
