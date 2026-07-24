"""One depth round: score candidate passes, keep the better-and-novel ones, archive them all.

swarm_pass is the composition seam of the depth engine. It does not spawn models itself (the live
cheap-model workers are the caller's job, kept out so this stays unit-testable with real fixtures
and no mocks). Given a batch of candidate passes it: scores each against the decomposed rubric,
disposes any that fail a deterministic check, keeps only those that beat the running baseline and
are not near-duplicates of an already-kept pass, and appends EVERY variant to the archive so the
weak/rejected ones survive as stepping stones (Darwin-Godel-Machine). gradient_flat is the pure
stop condition for the caller's multi-round loop (stop when no new best in `patience` rounds).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from intent_control_plane.archive import (
    ARCHIVE_LOG,
    append_variant,
    is_novel,
    keep_verdict,
    variant_record,
)
from intent_control_plane.rubric import score_rubric


def swarm_pass(
    subject: str,
    candidates: list[dict[str, Any]],
    criteria: list[dict[str, Any]],
    *,
    baseline: float | None = None,
    novelty_threshold: float = 0.99,
    archive_path: Path = ARCHIVE_LOG,
) -> dict[str, Any]:
    """Score, gate, and archive a batch of candidate passes for one artifact (one depth round).

    candidates: [{persona, model, content, results}]. Keeps a candidate only if its rubric score is
    not disposed, beats the running baseline (each kept pass raises the bar), and is novel vs the
    passes already kept this round. Returns {subject, kept, rejected, best_score, kept_variants}.
    """
    kept_texts: list[str] = []
    kept_variants: list[dict[str, Any]] = []
    rejected = 0
    running_baseline = baseline
    best = baseline if baseline is not None else 0.0
    for candidate in candidates:
        scored = score_rubric(criteria, candidate.get("results", {}))
        overall = float(scored["overall"])
        content = str(candidate.get("content", ""))
        if scored["disposed"] or keep_verdict(overall, running_baseline) != "kept" or not is_novel(content, kept_texts, novelty_threshold):
            verdict = "rejected"
        else:
            verdict = "kept"
        row = variant_record(
            subject=subject,
            persona=str(candidate.get("persona", "?")),
            model=str(candidate.get("model", "?")),
            score=overall,
            dims={k: float(v) for k, v in scored["per_criterion"].items()},
            cost_tokens=int(candidate.get("cost_tokens", 0)),
            verdict=verdict,
            failure_tags=list(scored["disposed_by"]),
            content=content,
        )
        append_variant(row, archive_path)  # every variant, so stepping stones survive
        if verdict == "kept":
            kept_texts.append(content)
            kept_variants.append(row)
            running_baseline = overall
            best = max(best, overall)
        else:
            rejected += 1
    return {
        "subject": subject,
        "kept": len(kept_variants),
        "rejected": rejected,
        "best_score": round(best, 4),
        "kept_variants": kept_variants,
    }


def gradient_flat(scores: list[float], patience: int = 2) -> bool:
    """True when the last `patience` rounds produced no new best (the depth loop has converged)."""
    if len(scores) <= patience:
        return False
    recent_best = max(scores[-patience:])
    prior_best = max(scores[:-patience])
    return recent_best <= prior_best
