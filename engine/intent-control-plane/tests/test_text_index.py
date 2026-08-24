"""Unit coverage for the extracted retrieval/scoring helpers (previously untested)."""
from __future__ import annotations

from intent_control_plane.text_index import cosine, term_vector, terms, text_hash


def test_terms_drops_stopwords_and_short_tokens():
    got = terms("Deploy the Widgora dashboard to production")
    assert {"deploy", "widgora", "dashboard", "production"} <= got
    assert "the" not in got  # stopword
    assert "to" not in got  # under 3 chars


def test_cosine_of_identical_vectors_is_one():
    v = term_vector("deploy widgora production pipeline")
    assert abs(cosine(v, v) - 1.0) < 1e-9


def test_cosine_of_disjoint_vectors_is_zero():
    a = term_vector("deploy production pipeline")
    b = term_vector("elephant giraffe zebra")
    assert cosine(a, b) == 0.0


def test_text_hash_is_stable_and_distinct():
    assert text_hash("same") == text_hash("same")
    assert text_hash("a") != text_hash("b")
