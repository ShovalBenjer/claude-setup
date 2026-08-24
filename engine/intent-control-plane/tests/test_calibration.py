"""Tests for judge-calibration metrics."""
from __future__ import annotations

import pytest

from intent_control_plane.calibration import (
    calibration_report,
    cohens_kappa,
    interpret_kappa,
    observed_agreement,
    verbosity_correlation,
)


def test_observed_agreement_fraction():
    assert observed_agreement([1, 1, 0], [1, 0, 0]) == pytest.approx(2 / 3)


def test_observed_agreement_validates():
    with pytest.raises(ValueError):
        observed_agreement([1], [1, 0])
    with pytest.raises(ValueError):
        observed_agreement([], [])


def test_cohens_kappa_perfect_agreement():
    assert cohens_kappa([1, 0, 1], [1, 0, 1]) == pytest.approx(1.0)


def test_cohens_kappa_hand_computed():
    # po=0.75, pe=0.5 -> (0.75-0.5)/(1-0.5) = 0.5
    assert cohens_kappa([1, 1, 0, 0], [1, 0, 0, 0]) == pytest.approx(0.5)


def test_cohens_kappa_full_disagreement_is_negative():
    assert cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]) < 0


def test_cohens_kappa_both_constant_same_label():
    # pe == 1.0 (both raters constant on one label): guard the 0/0, return 1.0
    assert cohens_kappa([1, 1, 1], [1, 1, 1]) == pytest.approx(1.0)


def test_cohens_kappa_string_labels():
    assert cohens_kappa(["yes", "no", "yes"], ["yes", "no", "yes"]) == pytest.approx(1.0)


def test_cohens_kappa_validates():
    with pytest.raises(ValueError):
        cohens_kappa([1, 0], [1])
    with pytest.raises(ValueError):
        cohens_kappa([], [])


def test_interpret_kappa_bands():
    assert interpret_kappa(-0.1) == "poor"
    assert interpret_kappa(0.1) == "slight"
    assert interpret_kappa(0.3) == "fair"
    assert interpret_kappa(0.5) == "moderate"
    assert interpret_kappa(0.7) == "substantial"
    assert interpret_kappa(0.85) == "almost perfect"


def test_verbosity_correlation_perfect_positive():
    assert verbosity_correlation([1.0, 2.0, 3.0], [10, 20, 30]) == pytest.approx(1.0)


def test_verbosity_correlation_zero_variance_raises():
    with pytest.raises(ValueError):
        verbosity_correlation([1.0, 2.0, 3.0], [5, 5, 5])


def test_verbosity_correlation_too_few_points_raises():
    with pytest.raises(ValueError):
        verbosity_correlation([1.0], [10])


def test_verbosity_correlation_length_mismatch_raises():
    with pytest.raises(ValueError):
        verbosity_correlation([1.0, 2.0], [10])


def test_calibration_report_keys_and_values():
    report = calibration_report([1, 1, 0, 0], [1, 0, 0, 0])
    assert report["n"] == 4
    assert report["observed_agreement"] == pytest.approx(0.75)
    assert report["cohens_kappa"] == pytest.approx(0.5)
    assert report["interpretation"] == "moderate"


def test_calibration_report_validates():
    with pytest.raises(ValueError):
        calibration_report([1], [1, 0])
