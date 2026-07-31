# -*- coding: utf-8 -*-
"""Oracle for tools/prose_metrics.py (L-2026-07-31-b).

The claim under test is narrow and worth stating, because the ticket asked for
more than this module delivers: these tests pin the MEASUREMENT and the code/
prose separation. They do not pin a threshold, because no corpus exists at this
register to fit one from (see prose_metrics.__doc__). A test asserting a band
here would be the guessed threshold the ticket forbids, dressed as an oracle.

Two-direction requirement from the ticket, adapted honestly:
  - a document that quotes code heavily must NOT read as hyphen-dense, since its
    compounds are file names (this is the case that would have made the metric
    useless in this repo specifically)
  - uniform prose must score a lower sentence variance than uneven prose
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import prose_metrics as pm  # noqa: E402


# ------------------------------------------------------------- extraction

def test_fenced_code_is_not_prose():
    doc = "Real sentence here about the gate.\n\n```python\nfoo_bar = --no-ignore\n```\n"
    assert "foo_bar" not in pm.prose_of(doc)
    assert "Real sentence" in pm.prose_of(doc)


def test_inline_code_and_paths_and_flags_are_stripped():
    doc = ("Run `tools/slop_lint.py` with --no-ignore against "
           "C:/Users/shova/claude-setup and read the result.")
    p = pm.prose_of(doc)
    for leak in ("slop_lint", "--no-ignore", "claude-setup"):
        assert leak not in p, f"{leak!r} survived extraction"


def test_lesson_ids_and_dates_do_not_count_as_compounds():
    doc = "L-2026-07-31-b was filed on 2026-07-31 and it names the gate exactly."
    assert pm.HYPHEN_COMPOUND.findall(pm.prose_of(doc)) == []


def test_link_label_survives_url_removal():
    p = pm.prose_of("See [the audit report](https://example.com/a-b-c) for the numbers.")
    assert "the audit report" in p
    assert "example.com" not in p


def test_table_rows_and_front_matter_are_dropped():
    doc = "---\nname: x\n---\n| a-b | c-d |\nA genuine sentence about density.\n"
    p = pm.prose_of(doc)
    assert "a-b" not in p and "name: x" not in p
    assert "genuine sentence" in p


def test_real_compound_still_counts():
    doc = "The state-of-the-art harness is a well-known false-positive machine."
    got = pm.HYPHEN_COMPOUND.findall(pm.prose_of(doc))
    assert "state-of-the-art" in got and "well-known" in got and "false-positive" in got


# ------------------------------------------------------------- sentences

def test_abbreviations_do_not_split_sentences():
    s = pm.sentences("The gate fires on e.g. a dash. It does not fire on hyphens.")
    assert len(s) == 2, s


def test_decimal_numbers_do_not_split_sentences():
    assert len(pm.sentences("The score was 0.93 on held-out data and nobody rechecked it.")) == 1


def test_hard_wrapped_sentence_is_one_sentence_not_three():
    """Regression for the defect this module shipped with for one hour: splitting
    on every newline measured the author's wrap column and reported it as
    sentence length. Real value on a 4,287-word spec was mean 7.5 words, max 21."""
    doc = ("The gate reads the file and reports every hit that it finds in the\n"
           "prose, then exits with a status the hook reads as a block, which is\n"
           "the entire mechanism and the reason nobody noticed.\n")
    assert len(pm.sentences(pm.prose_of(doc))) == 1
    assert pm.measure(doc)["sent_words_mean"] > 25


def test_blockquote_markers_do_not_enter_the_word_count():
    assert ">" not in pm.prose_of("> A quoted line about the gate.\n")


def test_one_word_lines_are_not_sentences():
    assert pm.sentences("Blocked.\nDone.\nThis one is an actual sentence.") == [
        "This one is an actual sentence."]


# --------------------------------------------------------------- metrics

UNIFORM = " ".join(
    ["The gate reads the file and reports the count of hits it found."] * 12)
UNEVEN = (
    "It failed. The gate reads the file, reports every hit it found, and then "
    "exits with a status that the hook interprets as a block, which is the whole "
    "mechanism. Nobody checked. One line of the diff was stale and three "
    "renewals rested on it. Fixed now.")


def test_uniform_prose_scores_lower_sentence_variance_than_uneven():
    u = pm.measure(UNIFORM)
    v = pm.measure(UNEVEN)
    assert u["sent_words_cv"] < v["sent_words_cv"], (u["sent_words_cv"], v["sent_words_cv"])


def test_code_heavy_document_is_not_reported_as_hyphen_dense():
    doc = ("The sweep found nothing and the reason was the ignore file.\n\n"
           "```sh\nrg -l --no-ignore 'a-b|c-d' tools/slop_lint.py\n```\n\n"
           "That is the whole finding and it took two runs to see it.\n")
    assert pm.measure(doc)["hyphen_compounds"] == 0


def test_hyphen_rate_is_per_word():
    m = pm.measure("A well-known problem here.")     # 4 words, 1 compound
    assert m["hyphen_compounds"] == 1
    assert 0.2 < m["hyphen_rate"] < 0.3, m["hyphen_rate"]


def test_fit_rejects_a_corpus_of_stubs():
    with pytest.raises(ValueError):
        pm.fit(["too short to band."] * 20, "stub", "unit test")


def test_fit_returns_percentiles_for_every_metric():
    corpus = [UNEVEN * 20] * 8
    prof = pm.fit(corpus, "unit", "unit test", min_words=50)
    assert prof["n"] == 8 and prof["kind"] == "MEASURED"
    for k in ("hyphen_rate", "sent_words_sd", "sent_words_cv"):
        assert set(prof["metrics"][k]) == {f"p{p}" for p in pm.PCTS}


# --------------------------------------------------- mutation control

def test_metric_can_go_red_when_the_extractor_is_disabled():
    """The four-layer standard: prove the check discriminates rather than
    returning a constant. With extraction bypassed, the code-quoting document
    above reports compounds it does not contain as prose."""
    doc = ("The sweep found nothing and the reason was the ignore file.\n\n"
           "```sh\nrg -l --no-ignore 'a-b|c-d' tools/slop_lint.py\n```\n")
    assert pm.measure(doc)["hyphen_compounds"] == 0
    assert len(pm.HYPHEN_COMPOUND.findall(doc)) > 0, "mutant is not distinguishable"


# ------------------------------------------------------- gate integration

def test_slop_lint_stays_green_on_dense_prose_and_still_reports():
    """Warn-only is the contract. Density must never change the exit code until
    a band is fitted; if this test ever fails, a threshold was smuggled in."""
    dense = (UNIFORM + " " + "A state-of-the-art well-known false-positive "
             "high-signal low-noise result. ") * 6
    env = dict(os.environ, SLOP_NO_LOG="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "slop_lint.py"), "-"],
                       input=dense, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[density]" in r.stderr and "no band fitted" in r.stderr


def test_slop_lint_still_fails_on_the_old_banlist():
    env = dict(os.environ, SLOP_NO_LOG="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "slop_lint.py"), "-"],
                       input="We must delve into the tapestry.", capture_output=True,
                       text=True, env=env)
    assert r.returncode == 1
