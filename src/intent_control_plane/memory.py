"""Typed memory: episodic/semantic/procedural/scratchpad records, jsonl store, tf-idf recall.

A3 slice (spec 2026-07-11 depth harness): a company persona or the depth engine writes typed
memory rows here and recalls them by relevance. recall() reuses text_index.term_vector/cosine
(the existing lexical scorer), so there is no new dependency; EmbeddingBackend is the typed seam
for swapping in a real dense-embedding model later without touching MemoryStore's call sites.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from intent_control_plane.text_index import cosine, term_vector
from intent_control_plane.util import stable_id, utc_now

MEMORY_KINDS = ("episodic", "semantic", "procedural", "scratchpad")

MEMORY_LOG = Path.home() / ".intent" / "memory" / "records.jsonl"


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Pluggable dense-embedding seam.

    tf-idf (text_index.term_vector/cosine) is the default backend MemoryStore.recall uses; a real
    embedding model implements this protocol and can be swapped in without changing recall's
    call sites. Not implemented here on purpose: no real model ships in this zero-dependency repo.
    """

    def embed(self, text: str) -> list[float]: ...


def memory_record(
    kind: str,
    text: str,
    *,
    tags: list[str] | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    """Build one typed memory row. Raises ValueError for an unknown kind (fail closed)."""
    if kind not in MEMORY_KINDS:
        raise ValueError(f"unknown memory kind: {kind!r} (expected one of {MEMORY_KINDS})")
    return {
        "memory_id": stable_id("mem"),
        "kind": kind,
        "text": text,
        "tags": list(tags or []),
        "ts": ts or utc_now(),
    }


class MemoryStore:
    """jsonl-backed memory ledger with tf-idf cosine recall, filterable by kind."""

    def __init__(self, log_path: Path = MEMORY_LOG) -> None:
        self.log_path = log_path

    def put(self, record: dict[str, Any]) -> None:
        """I/O: append one memory record to the jsonl ledger, creating the dir on first write."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _read_all(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        out: list[dict[str, Any]] = []
        for raw in self.log_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
        return out

    def recall(self, query: str, kind: str | None = None, k: int = 5) -> list[dict[str, Any]]:
        """Rank stored records by tf-idf cosine similarity to query, filtered by kind, top-k desc.

        Stable on ties (original ledger order), mirroring text_index.rank_by_relevance_and_recency.
        """
        query_vector = term_vector(query)
        rows = self._read_all()
        if kind is not None:
            rows = [row for row in rows if row.get("kind") == kind]
        scored: list[tuple[float, int, dict[str, Any]]] = []
        for index, row in enumerate(rows):
            score = cosine(query_vector, term_vector(str(row.get("text", ""))))
            scored.append((score, index, row))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [row for _, _, row in scored[:k]]
