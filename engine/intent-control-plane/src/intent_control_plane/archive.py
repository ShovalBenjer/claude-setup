"""Population archive: scored variants that survive as stepping stones, not just the best.

The shared spine of the self-evolving depth harness (spec 2026-07-11): the depth engine reads it
for parent variants to build on, and the company layer reads it as the bench of demoted personas
with their failure history intact. Two hard lessons from the 2026 self-evolving-agent literature
are baked in here: keep weak variants as stepping stones (Darwin-Godel-Machine: monotonic
keep-best gets stuck in local optima), and gate keep-if-better on a held-out slice, not only the
case it targeted (Self-Harness / Meta-Harness: overfit-to-the-target is the #1 failure mode).

Pure decision logic (variant_record, select_parents, keep_verdict, is_novel) is unit + property
tested; append_variant / read_variants are the only I/O (one jsonl ledger, stdlib json to keep
the package zero-dependency; an optional orjson accelerator can wrap these if profiling ever
shows the append is hot).
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from intent_control_plane.text_index import cosine, term_vector
from intent_control_plane.util import stable_id, utc_now

ARCHIVE_LOG = Path.home() / ".intent" / "archive" / "variants.jsonl"

# Floor weight so a zero-scoring variant is still an eligible stepping stone, never weight 0.
_EXPLORE_FLOOR = 0.01


def variant_record(
    subject: str,
    persona: str,
    model: str,
    score: float,
    *,
    dims: dict[str, float] | None = None,
    cost_tokens: int = 0,
    verdict: str = "scored",
    parent_id: str | None = None,
    failure_tags: list[str] | None = None,
    content: str = "",
) -> dict[str, Any]:
    """One scored variant (a pass on an artifact, or a persona's graded outcome).

    content holds the raw trace/diff (truncated), not a summary, because compression is the
    dominant failure mode of harness optimizers (Meta-Harness); the compressed key is derived at
    retrieval time, never stored in place of the raw evidence.
    """
    return {
        "variant_id": stable_id("var"),
        "ts": utc_now(),
        "subject": subject,
        "persona": persona,
        "model": model,
        "score": round(float(score), 6),
        "dims": dict(dims or {}),
        "cost_tokens": int(cost_tokens),
        "verdict": verdict,
        "parent_id": parent_id,
        "failure_tags": list(failure_tags or []),
        "content": content[:2000],
    }


def _weighted_sample_without_replacement(
    items: list[dict[str, Any]], weights: list[float], n: int, rng: random.Random
) -> list[dict[str, Any]]:
    """Pick n distinct items with probability proportional to weight (roulette, no replacement)."""
    pool = list(items)
    pool_weights = list(weights)
    picked: list[dict[str, Any]] = []
    for _ in range(min(n, len(pool))):
        total = sum(pool_weights)
        if total <= 0:
            index = rng.randrange(len(pool))
        else:
            threshold = rng.random() * total
            acc = 0.0
            index = len(pool) - 1
            for i, weight in enumerate(pool_weights):
                acc += weight
                if threshold <= acc:
                    index = i
                    break
        picked.append(pool.pop(index))
        pool_weights.pop(index)
    return picked


def select_parents(
    variants: list[dict[str, Any]], k: int, exploitation_ratio: float, rng: random.Random
) -> list[dict[str, Any]]:
    """Choose k parents: a top-elite fraction (exploitation) plus score-weighted explorers.

    exploitation_ratio in [0, 1] sets how much of k comes from the current best (elites); the rest
    is sampled score-weighted from the whole remaining pool, so a weak stepping-stone variant is
    always eligible rather than pruned. Deterministic for a seeded rng. Returns <= k variants.
    """
    if k <= 0 or not variants:
        return []
    pool = list(variants)
    k = min(k, len(pool))
    ranked = sorted(pool, key=lambda v: float(v.get("score", 0.0)), reverse=True)
    n_elite = min(k, math.ceil(k * exploitation_ratio))
    elites = ranked[:n_elite]
    elite_ids = {v["variant_id"] for v in elites}
    remaining = [v for v in ranked if v["variant_id"] not in elite_ids]
    n_explore = k - len(elites)
    weights = [float(v.get("score", 0.0)) + _EXPLORE_FLOOR for v in remaining]
    explorers = (
        _weighted_sample_without_replacement(remaining, weights, n_explore, rng) if n_explore > 0 else []
    )
    return elites + explorers


def keep_verdict(
    score: float,
    baseline: float | None,
    *,
    held_out: list[float] | None = None,
    held_out_baselines: list[float] | None = None,
    eps: float = 1e-6,
) -> str:
    """kept only if strictly better than baseline AND non-regressive on every held-out neighbor.

    The held-out gate is the guardrail against a pass that overfits the one rubric case it
    targeted while silently regressing the others (Self-Harness propose->evaluate->accept). A
    None baseline (first run) passes the improvement check; a held-out regression still rejects.
    held_out and held_out_baselines are keyword-only: they are same-typed and adjacent, so a
    positional caller could swap them and silently invert the regression check (audit #13). Unequal
    lengths cannot be paired, so the regression check is unverifiable and the verdict fails closed to
    'rejected' rather than silently truncating an unpaired case (Codex follow-up to #13).
    """
    if baseline is not None and score <= baseline + eps:
        return "rejected"
    if held_out and held_out_baselines:
        if len(held_out) != len(held_out_baselines):
            return "rejected"
        for current, prior in zip(held_out, held_out_baselines, strict=True):
            if current < prior - eps:
                return "rejected"
    return "kept"


def is_novel(candidate_text: str, recent_texts: list[str], threshold: float = 0.99) -> bool:
    """True if the candidate is not a near-duplicate of any recent text (cosine < threshold).

    Reuses the existing lexical term-vector cosine, so novelty rejection costs no new dependency
    (ShinkaEvolve rejects near-duplicate proposals before spending an eval on them).
    """
    candidate_vector = term_vector(candidate_text)
    return all(cosine(candidate_vector, term_vector(prior)) < threshold for prior in recent_texts)


def append_variant(row: dict[str, Any], log_path: Path = ARCHIVE_LOG) -> None:
    """I/O: append one variant to the jsonl archive, creating the dir on first write."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_variants(log_path: Path = ARCHIVE_LOG) -> list[dict[str, Any]]:
    """Read all variants from the ledger; malformed or non-dict lines are skipped, never fatal."""
    if not log_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out
