"""Lexical retrieval and scoring helpers: sparse term vectors, cosine, session terms.

Split from cli.py on 2026-07-09. Pure helpers plus thin sqlite readers; the command
handlers (rebuild_index, vector_search) stay in cli.py and import from here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from intent_control_plane.schema import connect, initialize
from intent_control_plane.util import utc_now


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def recency_weight(row_ts: str, now_ts: str, half_life_days: float = 14.0) -> float:
    """Exponential recency decay: 1.0 now, 0.5 at one half-life, ->0 for old rows.

    An unparseable or future timestamp gets weight 1.0 (no penalty), so a bad ts never
    silently drops a row from the pack.
    """
    parsed_row = _parse_iso(row_ts)
    parsed_now = _parse_iso(now_ts)
    if parsed_row is None or parsed_now is None:
        return 1.0
    age_days = (parsed_now - parsed_row).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    return float(0.5 ** (age_days / half_life_days))


def dedup_key(text: str, width: int = 60) -> str:
    """Normalized prefix for novelty dedup: lowercased, whitespace-collapsed first `width` chars."""
    normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return normalized[:width]


def rank_by_relevance_and_recency(
    rows: list[Any], task: str, now_ts: str, half_life_days: float = 14.0
) -> list[Any]:
    """Rank rows by event_score * recency_weight, descending, stable on ties (original order).

    This is the entropy-aware ranking: a fresh relevant event outranks a stale one of equal
    lexical relevance, so the pack stops being recency-only or relevance-only.
    """
    scored: list[tuple[float, int, Any]] = []
    for index, row in enumerate(rows):
        relevance = event_score(row, task)
        recency = recency_weight(row["timestamp_utc"], now_ts, half_life_days)
        scored.append((relevance * recency, index, row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in scored]

STOP_WORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "has",
    "have",
    "into",
    "not",
    "that",
    "the",
    "this",
    "with",
    "you",
    "your",
}


def event_score(row: sqlite3.Row, task: str) -> int:
    terms = {term for term in re.split(r"\W+", task.lower()) if term}
    haystack = f"{row['model_text']} {row['repo_path'] or ''}".lower()
    return sum(1 for term in terms if term in haystack)


def terms(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9]+", text.lower())
        if len(token) >= 3 and token not in STOP_WORDS
    }


def term_vector(text: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for token in terms(text):
        counts[token] = counts.get(token, 0.0) + 1.0
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {key: round(value / norm, 6) for key, value in sorted(counts.items())}


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    keys = set(left) & set(right)
    return sum(left[key] * right[key] for key in keys)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upsert_vector(
    conn: sqlite3.Connection,
    item_id: str,
    item_type: str,
    source_id: str,
    text: str,
) -> None:
    conn.execute(
        """
        insert or replace into vector_index (
          item_id, item_type, source_id, vector_json, text_hash, updated_at_utc
        ) values (?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            item_type,
            source_id,
            json.dumps(term_vector(text), sort_keys=True),
            text_hash(text),
            utc_now(),
        ),
    )


def cwd_terms(cwd: str | None) -> set[str]:
    if not cwd:
        return set()
    path = Path(cwd)
    parts = set(terms(path.name))
    if path.parent.name == "projects":
        parts.update(terms(path.name.replace("-", " ")))
    return parts


def recent_session_terms(base_dir: Path, cwd: str | None, session: str | None) -> set[str]:
    initialize(base_dir)
    query_terms: set[str] = set()
    with connect(base_dir) as conn:
        rows = conn.execute(
            """
            select model_text, repo_path from events
            where (? is null or repo_path = ?)
               or (? is not null and session_id = ?)
            order by timestamp_utc desc
            limit 20
            """,
            (cwd, cwd, session, session),
        ).fetchall()
    for row in rows:
        query_terms.update(terms(row["model_text"]))
        query_terms.update(cwd_terms(row["repo_path"]))
    return query_terms


def latest_rows(conn: sqlite3.Connection, repo: str | None, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        select * from events
        where (? is null or repo_path = ?)
        order by timestamp_utc desc
        limit ?
        """,
        (repo, repo, limit),
    ).fetchall()
