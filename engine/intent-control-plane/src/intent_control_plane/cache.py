"""Semantic cache (P2, harness-maturity backlog): the biggest untapped speed lever.

Start simple, exact+normalized key first (embedding-nearest can layer on later without
changing this contract): cache_key hashes a whitespace-normalized, lowercased payload,
prefixed by a kind so two call sites (e.g. "llm" vs "tool") never collide on the same
text. CacheStore is the only I/O, one jsonl ledger per Path, append-only, mirroring
archive.append_variant / policy.append_telemetry (insert-then-scan-latest, malformed
lines skipped rather than fatal).

TTL freshness never calls a clock internally beyond util.utc_now() at put() time to
stamp the write; every freshness check (is_fresh, and therefore get()) takes an
injected now_ts string, so expiry is fully deterministic to test.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from intent_control_plane.util import utc_now


def _normalize(payload: str) -> str:
    """Lowercase + collapse whitespace, the same idea as text_index.dedup_key."""
    return re.sub(r"\s+", " ", (payload or "").strip().lower())


def cache_key(kind: str, payload: str) -> str:
    """sha256 hex digest of `<kind>:<normalized payload>`, so a whitespace/case-only
    difference or a shared payload text across kinds never collides silently."""
    digest_input = f"{kind}:{_normalize(payload)}"
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def is_fresh(entry: dict[str, Any], now_ts: str) -> bool:
    """True if now_ts is within entry['ttl_seconds'] of entry['ts'].

    Any unparseable timestamp or missing ttl fails closed (not fresh), so a corrupt
    entry is always a miss rather than a silently-stale hit.
    """
    ts = entry.get("ts")
    ttl = entry.get("ttl_seconds")
    if not isinstance(ts, str) or ttl is None:
        return False
    parsed_ts = _parse_ts(ts)
    parsed_now = _parse_ts(now_ts)
    if parsed_ts is None or parsed_now is None:
        return False
    age_seconds = (parsed_now - parsed_ts).total_seconds()
    return age_seconds <= float(ttl)


class CacheStore:
    """A jsonl-backed cache: one append-only ledger, latest row per key wins on read."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._hits = 0
        self._misses = 0

    def put(self, key: str, value: str, ttl_seconds: float, now_ts: str | None = None) -> None:
        """I/O: append one cache entry, creating the parent dir on first write."""
        entry = {
            "key": key,
            "value": value,
            "ts": now_ts if now_ts is not None else utc_now(),
            "ttl_seconds": float(ttl_seconds),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _latest_entry(self, key: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        latest: dict[str, Any] | None = None
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            text = raw.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("key") == key:
                latest = row
        return latest

    def get(self, key: str, now_ts: str) -> str | None:
        """Latest fresh value for key, or None on miss (unknown key or expired TTL)."""
        entry = self._latest_entry(key)
        if entry is None or not is_fresh(entry, now_ts):
            self._misses += 1
            return None
        self._hits += 1
        return str(entry["value"])

    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses}
