"""intent evolve: the measurable-every-week harness-quality tracker (mutation-eval-keep).

Runs the golden-set eval, scores the harness, compares to the last recorded baseline, records
the delta as an eval_results row, and reports the verdict. It does NOT auto-mutate code (that
would be a speculative loop); it makes week-over-week change measurable so a real improvement
can be kept and a regression caught. This is the honest floor of the essay's Level-4 idea:
you cannot optimize what you do not measure over time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intent_control_plane.schema import connect, initialize
from intent_control_plane.util import stable_id, utc_now


def evolution_verdict(score: float, baseline: float | None, eps: float = 1e-6) -> str:
    """improved / regressed / same relative to the baseline; baseline-set on the first run."""
    if baseline is None:
        return "baseline-set"
    if score > baseline + eps:
        return "improved"
    if score < baseline - eps:
        return "regressed"
    return "same"


def golden_score(report: dict[str, Any]) -> float:
    """Fraction of golden fixtures that passed (0.0 when there are none)."""
    passed = int(report.get("passed", 0))
    failed = int(report.get("failed", 0))
    total = passed + failed
    return round(passed / total, 4) if total else 0.0


def last_evolve_score(base_dir: Path) -> float | None:
    """Score of the most recent evolve run, or None if this is the first."""
    initialize(base_dir)
    with connect(base_dir) as conn:
        row = conn.execute(
            "select details_json from eval_results where eval_type = 'evolve' "
            "order by created_at_utc desc limit 1"
        ).fetchone()
    if row is None:
        return None
    try:
        return float(json.loads(row["details_json"]).get("score"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def run_evolution(base_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    """Score the golden report, compare to the last baseline, record an evolve row, return it.

    The baseline is read before the new row is written, so it reflects the previous run. A
    regression is recorded with status 'fail' so it is queryable and cannot be mistaken for
    progress.
    """
    initialize(base_dir)
    score = golden_score(report)
    baseline = last_evolve_score(base_dir)
    verdict = evolution_verdict(score, baseline)
    details: dict[str, Any] = {
        "score": score,
        "baseline": baseline,
        "verdict": verdict,
        "fixtures": int(report.get("fixture_count", 0)),
    }
    eval_id = stable_id("eval")
    status = "fail" if verdict == "regressed" else "pass"
    with connect(base_dir) as conn:
        conn.execute(
            "insert into eval_results values (?, ?, ?, ?, ?)",
            (eval_id, "evolve", status, json.dumps(details, sort_keys=True), utc_now()),
        )
        conn.commit()
    details["eval_id"] = eval_id
    return details
