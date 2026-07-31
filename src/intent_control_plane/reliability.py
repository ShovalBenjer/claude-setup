"""pass^k reliability metric (PRD T4.3 / mojuco sim2real rung).

Single-pass accuracy (pass@1) overstates agent reliability. tau-bench
(arXiv 2406.12045) shows an agent measured at 61% pass@1 collapses to 25%
pass^8: run the same task 8 times independently and require ALL 8 to
succeed, and most of the apparent competence disappears. A model that gets
lucky once looks identical to a model that is actually reliable if the eval
only ever samples one trial per task.

pass^k is the probability that k independently-sampled trials of a task all
succeed, averaged over tasks. Given n trials per task with c successes, the
probability that k trials drawn without replacement from those n are all
successes is comb(c, k) / comb(n, k) (the standard unbiased pass^k estimator
used by tau-bench and the HumanEval pass@k line of work). This module runs
that estimator over a trial matrix (one row per task, one bool per trial) so
an eval harness can report pass^k instead of pass@1.
"""
from __future__ import annotations

from math import comb
from typing import Any


def pass_at_1(trial_matrix: list[list[bool]]) -> float:
    """Mean per-task success rate: mean over tasks of sum(trials)/len(trials).

    Raises ValueError if the matrix is empty or any task has no trials: a
    metric over no data is undefined, so this fails closed rather than
    silently returning 0.0 or nan.
    """
    if not trial_matrix:
        raise ValueError("pass_at_1: trial_matrix is empty")
    for i, trials in enumerate(trial_matrix):
        if not trials:
            raise ValueError(f"pass_at_1: task {i} has no trials")
    rates = [sum(trials) / len(trials) for trials in trial_matrix]
    return sum(rates) / len(rates)


def pass_k(trial_matrix: list[list[bool]], k: int) -> float:
    """tau-bench pass^k: probability that k trials drawn without replacement all succeed.

    For each task with n=len(trials), c=sum(trials), the task's contribution
    is comb(c, k) / comb(n, k), averaged over tasks.

    Raises ValueError if k < 1, if the matrix is empty, or if any task has
    fewer trials than k (naming the offending task index and its n): pass^k
    is undefined for a task that was not sampled k times.
    """
    if k < 1:
        raise ValueError(f"pass_k: k must be >= 1, got {k}")
    if not trial_matrix:
        raise ValueError("pass_k: trial_matrix is empty")
    for i, trials in enumerate(trial_matrix):
        n = len(trials)
        if n < k:
            raise ValueError(f"pass_k: task {i} has only n={n} trials, need k={k}")
    contributions = []
    for trials in trial_matrix:
        n = len(trials)
        c = sum(trials)
        contributions.append(comb(c, k) / comb(n, k))
    return sum(contributions) / len(contributions)


def reliability_report(trial_matrix: list[list[bool]], ks: list[int]) -> dict[str, Any]:
    """Report pass_at_1 and pass^k for every feasible k in ks.

    A k is feasible if every task has at least k trials (k <= min task n).
    Infeasible ks are skipped, not raised, so a caller can request a fixed
    list like [1, 2, 4, 8] against a matrix with uneven trial counts without
    a per-k try/except.
    """
    min_n = min(len(trials) for trials in trial_matrix)
    pass_k_values: dict[int, float] = {}
    skipped_ks: list[int] = []
    for k in ks:
        if k <= min_n:
            pass_k_values[k] = pass_k(trial_matrix, k)
        else:
            skipped_ks.append(k)
    return {
        "n_tasks": len(trial_matrix),
        "pass_at_1": pass_at_1(trial_matrix),
        "pass_k": pass_k_values,
        "skipped_ks": skipped_ks,
    }
