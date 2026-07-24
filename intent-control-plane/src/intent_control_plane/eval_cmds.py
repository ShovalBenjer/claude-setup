"""CLI handlers wiring the sim2real cores into `intent eval` (PRD T4.1/T4.3/T4.4/T4.7).

Each handler reads a small JSON input, runs the pure metric core (previously reachable only
from tests), records the outcome to the eval_results table so results are queryable, and
returns the metric. This turns the parked pure rungs into a live, recorded eval pipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from intent_control_plane.calibration import calibration_report
from intent_control_plane.eval_tiers import (
    Tier1Result,
    check_function_call,
    check_regex,
    check_required_keys,
    check_valid_json,
    run_tier1,
)
from intent_control_plane.reliability import reliability_report
from intent_control_plane.schema import connect, initialize
from intent_control_plane.trace_diff import diff_traces
from intent_control_plane.util import stable_id, utc_now


def _load(path: str) -> Any:
    return json.loads(Path(path).expanduser().read_text())


def _record(base_dir: Path, eval_type: str, status: str, details: dict[str, Any]) -> str:
    """Insert one eval_results row; returns the eval_id."""
    initialize(base_dir)
    eval_id = stable_id("eval")
    with connect(base_dir) as conn:
        conn.execute(
            "insert into eval_results values (?, ?, ?, ?, ?)",
            (eval_id, eval_type, status, json.dumps(details, sort_keys=True), utc_now()),
        )
        conn.commit()
    return eval_id


def eval_passk(args: argparse.Namespace) -> dict[str, Any]:
    """T4.3 pass^k reliability over a trial matrix. Input: {trials, ks?, threshold?}."""
    data = _load(args.file)
    report = reliability_report(data["trials"], data.get("ks", [1, 2, 4, 8]))
    status = "pass" if report["pass_at_1"] >= data.get("threshold", 0.0) else "fail"
    report["status"] = status
    report["eval_id"] = _record(args.base_dir, "passk", status, report)
    return report


def eval_kappa(args: argparse.Namespace) -> dict[str, Any]:
    """T4.7 judge-vs-human Cohen's kappa. Input: {judge, human, threshold?}."""
    data = _load(args.file)
    report = calibration_report(data["judge"], data["human"])
    status = "pass" if report["cohens_kappa"] >= data.get("threshold", 0.0) else "fail"
    report["status"] = status
    report["eval_id"] = _record(args.base_dir, "kappa", status, report)
    return report


def eval_trace_diff(args: argparse.Namespace) -> dict[str, Any]:
    """T4.4 deterministic trace-replay diff. Input: {recorded, candidate, ignore?}."""
    data = _load(args.file)
    result = diff_traces(data["recorded"], data["candidate"], tuple(data.get("ignore", [])))
    status = "pass" if result["identical"] else "fail"
    result["status"] = status
    result["eval_id"] = _record(args.base_dir, "trace_diff", status, result)
    return result


def eval_tier1(args: argparse.Namespace) -> dict[str, Any]:
    """T4.1 deterministic tier-1 gate. Input: {text, checks:[...], call?}.

    Each check spec is {type: valid_json|required_keys|regex|function_call, ...}. Runs before
    any judge; a fail means the caller should skip the LLM judges for that row.
    """
    data = _load(args.file)
    text = str(data.get("text", ""))
    results: list[Tier1Result] = []
    for spec in data.get("checks", []):
        kind = spec.get("type")
        if kind == "valid_json":
            results.append(check_valid_json(text))
        elif kind == "required_keys":
            results.append(check_required_keys(text, spec.get("keys", [])))
        elif kind == "regex":
            results.append(check_regex(text, spec["pattern"], spec.get("should_match", True)))
        elif kind == "function_call":
            results.append(
                check_function_call(data.get("call"), spec["name"], spec.get("required_args", []))
            )
    gate = run_tier1(results)
    status = "pass" if gate["passed"] else "fail"
    gate["status"] = status
    gate["checks_detail"] = [
        {"check": r.check, "passed": r.passed, "reason": r.reason} for r in results
    ]
    gate["eval_id"] = _record(args.base_dir, "tier1", status, gate)
    return gate
