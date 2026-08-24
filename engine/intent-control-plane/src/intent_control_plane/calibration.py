"""Judge-calibration metrics: inter-rater agreement for the LLM judge panel.

PRD T4.7. Run-to-run LLM-judge self-agreement can approach coin-flip on some tasks
(arXiv 2603.05399), so a judge is only trustworthy after a periodic sample is scored
against human labels. This module is the pure-metric layer: Cohen's kappa (agreement
corrected for chance), observed agreement, a Landis-Koch interpretation band, and a
cheap verbosity-bias correlation. Wiring it to sample the live grok-4-1 / DeepSeek-V3.2
panel against human labels is a separate, shared-HOME task; this module is stdlib-only
and unwired by design.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def _validate_pair(a: list[Any], b: list[Any]) -> None:
    """Raise ValueError if the two label series cannot be compared."""
    if len(a) != len(b):
        raise ValueError(f"length mismatch: {len(a)} vs {len(b)}")
    if not a:
        raise ValueError("empty input")


def observed_agreement(a: list[Any], b: list[Any]) -> float:
    """Fraction of positions where a[i] == b[i]."""
    _validate_pair(a, b)
    agree = sum(1 for x, y in zip(a, b, strict=True) if x == y)
    return agree / len(a)


def cohens_kappa(a: list[Any], b: list[Any]) -> float:
    """Cohen's kappa: agreement corrected for chance, (po - pe) / (1 - pe).

    Labels may be any hashable value. `po` is observed agreement, `pe` is the
    chance agreement (sum over categories of p_a(c) * p_b(c)). When both raters
    are constant on a single shared label, pe == 1.0 and 1 - pe == 0; that is
    perfect agreement, so return 1.0 rather than dividing by zero.
    """
    _validate_pair(a, b)
    n = len(a)
    po = observed_agreement(a, b)
    count_a = Counter(a)
    count_b = Counter(b)
    categories = set(count_a) | set(count_b)
    pe = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def interpret_kappa(kappa: float) -> str:
    """Landis-Koch interpretation band for a kappa value."""
    if kappa < 0:
        return "poor"
    if kappa < 0.2:
        return "slight"
    if kappa < 0.4:
        return "fair"
    if kappa < 0.6:
        return "moderate"
    if kappa < 0.8:
        return "substantial"
    return "almost perfect"


def verbosity_correlation(scores: list[float], lengths: list[int]) -> float:
    """Pearson correlation between judged scores and output lengths.

    A strong positive value hints the judge rewards length. Raises ValueError if
    the series differ in length, have fewer than 2 points, or either has zero
    variance (correlation is undefined, fail closed).
    """
    if len(scores) != len(lengths):
        raise ValueError(f"length mismatch: {len(scores)} vs {len(lengths)}")
    n = len(scores)
    if n < 2:
        raise ValueError("need at least 2 points for a correlation")
    mean_s = sum(scores) / n
    mean_l = sum(lengths) / n
    cov = sum((s - mean_s) * (length - mean_l) for s, length in zip(scores, lengths, strict=True))
    var_s = sum((s - mean_s) ** 2 for s in scores)
    var_l = sum((length - mean_l) ** 2 for length in lengths)
    if var_s == 0 or var_l == 0:
        raise ValueError("zero variance: correlation undefined")
    return float(cov / (var_s**0.5 * var_l**0.5))


def calibration_report(judge_labels: list[Any], human_labels: list[Any]) -> dict[str, Any]:
    """Kappa + observed agreement + Landis-Koch band for judge vs human labels."""
    _validate_pair(judge_labels, human_labels)
    kappa = cohens_kappa(judge_labels, human_labels)
    return {
        "n": len(judge_labels),
        "observed_agreement": observed_agreement(judge_labels, human_labels),
        "cohens_kappa": kappa,
        "interpretation": interpret_kappa(kappa),
    }
