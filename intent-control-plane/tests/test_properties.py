"""Property-based invariants for the pure cores (hypothesis, no mocks).

Complements the example-based tests: these assert the laws that must hold for ALL inputs,
not just the hand-picked rows (the tau-bench pass^k monotonicity, kappa range, cosine
bounds, and the context-band ordering).
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from intent_control_plane.calibration import cohens_kappa
from intent_control_plane.reliability import pass_at_1, pass_k
from intent_control_plane.text_index import cosine, term_vector
from intent_control_plane.tower import context_budget_band

_words = st.text(alphabet="abcdefghijklmnop ", min_size=0, max_size=40)
_trial_matrix = st.lists(st.lists(st.booleans(), min_size=1, max_size=8), min_size=1, max_size=6)
_labels = st.lists(st.integers(min_value=0, max_value=3), min_size=1, max_size=30)


@given(_words)
def test_term_vector_is_l2_normalized(text):
    vector = term_vector(text)
    if vector:
        norm = sum(value * value for value in vector.values()) ** 0.5
        assert abs(norm - 1.0) < 1e-6


@given(_words)
def test_cosine_self_is_one_for_nonempty(text):
    vector = term_vector(text)
    if vector:
        # term_vector rounds components to 6 decimals, so cosine(v, v) is exact only to ~2e-6
        assert abs(cosine(vector, vector) - 1.0) < 1e-5


@given(_words, _words)
def test_cosine_symmetric_and_bounded(a, b):
    va, vb = term_vector(a), term_vector(b)
    value = cosine(va, vb)
    assert abs(value - cosine(vb, va)) < 1e-9  # symmetry is exact (same rounded components)
    # term_vector rounds components to 6 decimals, so the L2 norm (and thus cosine(v, v)) is
    # exact only to ~1e-6; the [0, 1] bound holds within that rounding tolerance.
    assert -1e-5 <= value <= 1.0 + 1e-5


@given(_trial_matrix)
def test_pass_at_1_in_unit_interval(matrix):
    assert 0.0 <= pass_at_1(matrix) <= 1.0


@given(_trial_matrix)
def test_pass_k_is_non_increasing_in_k_and_equals_pass_at_1_at_k1(matrix):
    min_n = min(len(row) for row in matrix)
    previous = 1.0
    for k in range(1, min_n + 1):
        value = pass_k(matrix, k)
        assert 0.0 <= value <= 1.0
        assert value <= previous + 1e-9  # pass^k never exceeds pass^(k-1)
        previous = value
    assert abs(pass_k(matrix, 1) - pass_at_1(matrix)) < 1e-9


@given(_labels)
def test_kappa_self_agreement_is_one(labels):
    assert abs(cohens_kappa(labels, labels) - 1.0) < 1e-9


@given(_labels, _labels)
def test_kappa_in_minus_one_to_one(a, b):
    n = min(len(a), len(b))
    if n == 0:
        return
    value = cohens_kappa(a[:n], b[:n])
    assert -1.0 - 1e-9 <= value <= 1.0 + 1e-9


@given(st.integers(min_value=0, max_value=500_000), st.integers(min_value=0, max_value=500_000))
def test_band_never_greener_with_more_tokens(x, y):
    order = {"green": 0, "amber": 1, "red": 2}
    low, high = sorted((x, y))
    assert order[context_budget_band(low)] <= order[context_budget_band(high)]


@given(st.integers(min_value=0, max_value=10_000_000))
def test_band_is_always_a_valid_label(tokens):
    assert context_budget_band(tokens) in {"green", "amber", "red"}
