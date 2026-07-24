"""Tests for the pass^k reliability metric module (PRD T4.3)."""
from __future__ import annotations

import pytest

from intent_control_plane.reliability import pass_at_1, pass_k, reliability_report


def test_pass_at_1_all_pass_is_one():
    matrix = [[True, True, True], [True, True]]
    assert pass_at_1(matrix) == pytest.approx(1.0)


def test_pass_at_1_single_task_hand_computed():
    # n=4, c=3: 3/4 = 0.75
    matrix = [[True, True, True, False]]
    assert pass_at_1(matrix) == pytest.approx(0.75)


def test_pass_at_1_averages_across_two_tasks():
    # task 1: 3/4 = 0.75, task 2: 1/2 = 0.5 -> mean = 0.625
    matrix = [[True, True, True, False], [True, False]]
    assert pass_at_1(matrix) == pytest.approx(0.625)


def test_pass_at_1_raises_on_empty_matrix():
    with pytest.raises(ValueError):
        pass_at_1([])


def test_pass_at_1_raises_on_empty_task():
    with pytest.raises(ValueError):
        pass_at_1([[True, True], []])


def test_pass_k_all_pass_is_one_for_any_feasible_k():
    matrix = [[True, True, True, True], [True, True, True]]
    assert pass_k(matrix, k=1) == pytest.approx(1.0)
    assert pass_k(matrix, k=2) == pytest.approx(1.0)
    assert pass_k(matrix, k=3) == pytest.approx(1.0)


def test_pass_k_hand_computed_k1():
    # n=4, c=3: comb(3,1)/comb(4,1) = 3/4 = 0.75, matches pass_at_1
    matrix = [[True, True, True, False]]
    assert pass_k(matrix, k=1) == pytest.approx(0.75)


def test_pass_k_hand_computed_k2():
    # n=4, c=3: comb(3,2)/comb(4,2) = 3/6 = 0.5
    matrix = [[True, True, True, False]]
    assert pass_k(matrix, k=2) == pytest.approx(0.5)


def test_pass_k_hand_computed_k3():
    # n=4, c=3: comb(3,3)/comb(4,3) = 1/4 = 0.25
    matrix = [[True, True, True, False]]
    assert pass_k(matrix, k=3) == pytest.approx(0.25)


def test_pass_k_hand_computed_k4_is_zero():
    # n=4, c=3: comb(3,4) = 0, comb(4,4) = 1 -> 0/1 = 0.0
    matrix = [[True, True, True, False]]
    assert pass_k(matrix, k=4) == pytest.approx(0.0)


def test_pass_k_raises_when_k_exceeds_a_task_n():
    matrix = [[True, True, True, True], [True, True]]
    with pytest.raises(ValueError, match="1"):
        pass_k(matrix, k=3)


def test_pass_k_raises_when_k_less_than_1():
    matrix = [[True, True, True, False]]
    with pytest.raises(ValueError):
        pass_k(matrix, k=0)


def test_pass_k_raises_on_empty_matrix():
    with pytest.raises(ValueError):
        pass_k([], k=1)


def test_reliability_report_mixed_matrix():
    # task 0: n=4, c=3 -> feasible k up to 4
    # task 1: n=2, c=2 -> feasible k up to 2
    matrix = [[True, True, True, False], [True, True]]
    report = reliability_report(matrix, ks=[1, 2, 4, 8])

    assert report["n_tasks"] == 2
    assert report["pass_at_1"] == pytest.approx(0.875)

    # only k=1 and k=2 are feasible (min task n across tasks is 2)
    assert set(report["pass_k"].keys()) == {1, 2}
    assert report["skipped_ks"] == [4, 8]

    # k=1: task0 comb(3,1)/comb(4,1)=0.75, task1 comb(2,1)/comb(2,1)=1.0 -> mean 0.875
    assert report["pass_k"][1] == pytest.approx(0.875)
    # k=2: task0 comb(3,2)/comb(4,2)=0.5, task1 comb(2,2)/comb(2,2)=1.0 -> mean 0.75
    assert report["pass_k"][2] == pytest.approx(0.75)
