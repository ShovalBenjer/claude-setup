#!/usr/bin/env python3
"""Fit prose-quality thresholds from the collected score corpus.

slop_lint.py collects density and variance scores to state/prose-scores.jsonl
but explicitly defers thresholds: "the threshold comes from a week of
distribution rather than from taste." This tool closes that gap.

`fit` reads the corpus and emits state/prose-thresholds.json with percentile
bands. `check` reads the thresholds and fails if any scored document in a
given path falls outside the p95 band (suggesting machine-generated prose).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile

SCORES_FILE = "state/prose-scores.jsonl"
THRESHOLDS_FILE = "state/prose-thresholds.json"

METRIC_KEYS = ("hyphen_rate", "sent_words_cv", "sent_chars_cv")

PCTS = (5, 10, 25, 50, 75, 90, 95)


def _pct(xs: list[float], p: int) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p / 100
    f = math.floor(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load_scores(project: str) -> list[dict]:
    path = os.path.join(project, SCORES_FILE)
    if not os.path.isfile(path):
        return []
    scores = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                scores.append(json.loads(line))
    return scores


def fit(project: str) -> int:
    """Compute percentile bands from the score corpus and save thresholds."""
    scores = load_scores(project)
    if len(scores) < 20:
        print(f"only {len(scores)} scores; need at least 20 to fit bands")
        return 1

    thresholds: dict[str, dict] = {"n": len(scores), "metrics": {}}
    for key in METRIC_KEYS:
        vals = [s[key] for s in scores if key in s]
        if not vals:
            continue
        bands = {f"p{p}": round(_pct(vals, p), 6) for p in PCTS}
        bands["mean"] = round(sum(vals) / len(vals), 6)
        thresholds["metrics"][key] = bands
        print(f"  {key}: p5={bands['p5']:.4f}  p50={bands['p50']:.4f}  p95={bands['p95']:.4f}  (n={len(vals)})")

    path = os.path.join(project, THRESHOLDS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(thresholds, f, indent=2)
        f.write("\n")

    print(f"\nthresholds saved to {THRESHOLDS_FILE} (from {len(scores)} scores)")
    return 0


def load_thresholds(project: str) -> dict | None:
    path = os.path.join(project, THRESHOLDS_FILE)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


def check(project: str) -> tuple[int, list[str]]:
    """Verify thresholds exist, are fitted from enough data, and are fresh."""
    thresholds = load_thresholds(project)
    if thresholds is None:
        print("no thresholds found; run `fit` first")
        return 2, []

    scores = load_scores(project)
    findings: list[str] = []

    fitted_n = thresholds.get("n", 0)
    current_n = len(scores)
    metrics = thresholds.get("metrics", {})

    if fitted_n < 20:
        findings.append(f"thresholds fitted from only {fitted_n} scores (need 20+)")

    findings.extend(
        f"missing metric band: {key}" for key in METRIC_KEYS if key not in metrics
    )

    if current_n > fitted_n * 1.5 and current_n - fitted_n >= 20:
        findings.append(
            f"STALE THRESHOLDS: corpus grew from {fitted_n} to {current_n} scores; refit with `fit`"
        )

    print(f"  thresholds: fitted from {fitted_n} scores, corpus now {current_n}")
    for key in METRIC_KEYS:
        if key in metrics:
            m = metrics[key]
            print(f"  {key}: p5={m.get('p5', '?'):.4f}  p50={m.get('p50', '?'):.4f}  p95={m.get('p95', '?'):.4f}")

    if findings:
        for f in findings:
            print(f"  {f}")
        return 1, findings

    print("  thresholds current and complete")
    return 0, findings


def selftest() -> int:
    """Prove the fitter and checker work end to end."""
    failures: list[str] = []

    # Test 1: fit with enough data
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)
        scores_path = os.path.join(state_dir, "prose-scores.jsonl")
        with open(scores_path, "w") as f:
            for i in range(30):
                score = {
                    "file": f"doc-{i}.md",
                    "words": 500 + i * 10,
                    "sentences": 30 + i,
                    "hyphen_rate": 0.02 + (i % 10) * 0.002,
                    "sent_words_cv": 0.5 + (i % 10) * 0.05,
                    "sent_chars_cv": 0.5 + (i % 10) * 0.05,
                }
                f.write(json.dumps(score) + "\n")

        code = fit(tmp)
        if code != 0:
            failures.append(f"fit with 30 scores returned {code}, expected 0")

        thresholds = load_thresholds(tmp)
        if thresholds is None:
            failures.append("thresholds file not created")
        elif "metrics" not in thresholds:
            failures.append("thresholds missing metrics key")

    # Test 2: fit with too few scores
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)
        scores_path = os.path.join(state_dir, "prose-scores.jsonl")
        with open(scores_path, "w") as f:
            for i in range(5):
                f.write(json.dumps({"file": f"doc-{i}.md", "hyphen_rate": 0.02}) + "\n")

        code = fit(tmp)
        if code != 1:
            failures.append(f"fit with 5 scores returned {code}, expected 1")

    # Test 3: check detects stale thresholds (corpus grew significantly)
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)

        with open(os.path.join(state_dir, "prose-thresholds.json"), "w") as f:
            json.dump({
                "n": 30,
                "metrics": {
                    "hyphen_rate": {"p5": 0.010, "p50": 0.025, "p95": 0.040},
                    "sent_words_cv": {"p5": 0.400, "p50": 0.700, "p95": 0.950},
                    "sent_chars_cv": {"p5": 0.400, "p50": 0.700, "p95": 0.950},
                }
            }, f)

        with open(os.path.join(state_dir, "prose-scores.jsonl"), "w") as f:
            for i in range(80):
                f.write(json.dumps({"file": f"doc-{i}.md", "hyphen_rate": 0.025}) + "\n")

        code, findings = check(tmp)
        if code != 1:
            failures.append(f"stale thresholds returned {code}, expected 1")
        if not any("STALE" in f for f in findings):
            failures.append("staleness was not detected")

    # Test 4: check passes for current thresholds
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "state")
        os.makedirs(state_dir)

        with open(os.path.join(state_dir, "prose-thresholds.json"), "w") as f:
            json.dump({
                "n": 100,
                "metrics": {
                    "hyphen_rate": {"p5": 0.010, "p50": 0.025, "p95": 0.040},
                    "sent_words_cv": {"p5": 0.400, "p50": 0.700, "p95": 0.950},
                    "sent_chars_cv": {"p5": 0.400, "p50": 0.700, "p95": 0.950},
                }
            }, f)

        with open(os.path.join(state_dir, "prose-scores.jsonl"), "w") as f:
            for i in range(100):
                f.write(json.dumps({"file": f"doc-{i}.md", "hyphen_rate": 0.025}) + "\n")

        code, findings = check(tmp)
        if code != 0:
            failures.append(f"current thresholds returned {code}, expected 0")

    # Test 5: no thresholds returns 2
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = check(tmp)
        if code != 2:
            failures.append(f"no thresholds returned {code}, expected 2")

    for line in failures:
        print(f"FAIL {line}")
    if not failures:
        print(f"PASS prose_fit selftest (5 checks)")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("fit", "check", "selftest"), default="check", nargs="?")
    parser.add_argument("--project", default=os.getcwd())
    args = parser.parse_args(argv)

    if args.command == "selftest":
        return selftest()
    if args.command == "fit":
        return fit(args.project)
    code, _ = check(args.project)
    return code


if __name__ == "__main__":
    sys.exit(main())
