"""The harness can locate itself, and an explicit override still refuses to be ignored.

This resolver spent nine days in `new-recruit`, a consumer, while the producer it
resolves documented neither it nor the weaker pattern the other consumer used.
Promoted 2026-08-09. The promotion is what these tests are mostly about: a copy
living INSIDE the harness has to answer a question the consumer copy never faced,
and the first run from its new home raised, because the default product root was
a hardcoded `parent.parent` that pointed one directory short.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "harness"))

import harness  # noqa: E402


def test_the_copy_inside_the_harness_resolves_to_the_harness():
    path, source = harness.resolve()
    assert source == "self"
    assert os.path.isfile(os.path.join(path, "tools", "gate", "gate.py"))


def test_self_resolution_walks_up_rather_than_assuming_a_depth():
    """A fixed depth broke on the first run from the new location.

    Walking means moving this file deeper does not silently return the wrong
    directory, it just keeps finding the same gate.
    """
    assert harness._own_harness() is not None
    assert str(harness._own_harness()) == ROOT


def test_a_wrong_explicit_override_raises_instead_of_falling_through(monkeypatch, tmp_path):
    """The module's central rule, and it must survive the self leg.

    Adding self-resolution created a new way for a wrong CLAUDE_HARNESS to be
    quietly ignored, since this file always sits inside a real harness now. The
    env check runs first for exactly that reason.
    """
    monkeypatch.setenv("CLAUDE_HARNESS", str(tmp_path))
    with pytest.raises(harness.HarnessNotFound):
        harness.resolve()


def test_a_correct_explicit_override_wins_over_self(monkeypatch):
    monkeypatch.setenv("CLAUDE_HARNESS", ROOT)
    path, source = harness.resolve()
    assert source == "env"
    assert path == ROOT


def test_an_explicit_product_root_reads_that_product_ref_not_self(tmp_path):
    """The bug the promotion introduced, caught by running it rather than reading it.

    Self-detection answers "I am the harness and nobody told me otherwise". An
    explicit product_root is somebody telling it otherwise. Before this, asking
    the promoted copy where daily-deep-learning finds its harness returned its
    OWN repository via "self" and never opened the ref file written for that
    product, so the ref leg was dead for every consumer the moment the resolver
    moved inside a harness.
    """
    ref = tmp_path / harness.REF_NAME
    ref.write_text("path = {}\n".format(ROOT), encoding="utf-8")
    path, source = harness.resolve(product_root=str(tmp_path))
    assert source == "harness-ref"
    assert path == ROOT


def test_self_still_answers_when_no_product_root_is_named():
    """The other side of the same knob, so the fix does not delete the feature."""
    assert harness.resolve()[1] == "self"


def test_a_directory_without_the_gate_is_not_a_harness(tmp_path):
    """The marker is the gate entry point, not a marker file.

    A marker file can be copied somewhere useless. This cannot.
    """
    assert harness._is_harness(tmp_path) is False
    (tmp_path / "tools" / "gate").mkdir(parents=True)
    (tmp_path / "tools" / "gate" / "gate.py").write_text("", encoding="utf-8")
    assert harness._is_harness(tmp_path) is True


def test_parse_ref_reads_paths_repo_and_sha_and_ignores_comments(tmp_path):
    ref = tmp_path / ".harness-ref"
    ref.write_text(
        "# a comment\n"
        "repo = https://example.com/x.git\n"
        "sha  = deadbeef\n"
        "path = /one\n"
        "path = /two   # trailing comment\n"
        "nonsense\n",
        encoding="utf-8")
    got = harness.parse_ref(ref)
    assert got["repo"] == "https://example.com/x.git"
    assert got["sha"] == "deadbeef"
    assert got["paths"] == ["/one", "/two"]


def test_a_missing_ref_file_is_empty_rather_than_an_error(tmp_path):
    got = harness.parse_ref(tmp_path / "nope")
    assert got == {"repo": None, "sha": None, "paths": []}
