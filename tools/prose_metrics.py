# -*- coding: utf-8 -*-
"""Density and variance metrics for markdown prose (L-2026-07-31-b).

slop_lint.py gates the RULED form of the dash rule: a spaced em dash fails, and
nothing else about sentence shape is looked at. A 5.4k-word deliverable passed it
with zero em dashes, zero en dashes and two non-ASCII characters, and still read
as machine written. What the operator was pointing at was density and uniformity,
which the banlist cannot see.

This module measures the property. It does not judge it. There is no threshold
here on purpose:

  The only fitted corpus in this ecosystem is voice-metrics/profiles.json, whose
  four profiles are all WhatsApp, thread-level, both sides, 35,472 sends with a
  median length near 20 characters. Fitting a markdown-document band from chat
  sends is the error profiles.py:118-121 already documents for line_cv. A
  threshold invented instead would be a second RULED rule wearing a number, which
  is the exact failure class this work exists to close.

So: measure, log, and fit later from the collected distribution. `fit()` takes a
named corpus of real documents when one exists.

The extractor is the part that carries the correctness risk. Over raw markdown,
`--no-ignore`, `tools/slop_lint.py` and `L-2026-07-31-b` all count as hyphen
compounds, so the metric would mostly measure how much a document quotes code.
That is L-2026-07-29-d, an oracle that cannot separate code from prose about
code. prose_of() strips the code channels before anything is counted, and
tests/test_prose_metrics.py pins each strip.
"""
import math
import re
import statistics

# --------------------------------------------------------------- extraction

FENCE = re.compile(r"^```.*?^```", re.M | re.S)
INDENTED = re.compile(r"^(?: {4}|\t).*$", re.M)
INLINE_CODE = re.compile(r"`[^`\n]+`")
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.M)
LINK = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")     # keep the label, drop the URL
BARE_URL = re.compile(r"<?https?://\S+>?")
PATHISH = re.compile(r"\S*[/\\~]\S*")               # paths, globs, flags with slashes
FLAG = re.compile(r"(?<!\w)--?[A-Za-z][\w-]*")      # --no-ignore, -rn
IDENT = re.compile(r"\b\w+(?:_\w+)+\b")             # snake_case identifiers
LESSON_ID = re.compile(r"\bL-\d{4}-\d{2}-\d{2}-[a-z]\b")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
HEADING = re.compile(r"^#{1,6}\s+", re.M)
LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.M)
EMPHASIS = re.compile(r"[*_]{1,3}")
QUOTE = re.compile(r"^\s*>+\s?", re.M)
HRULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.M)


def prose_of(text):
    """Markdown reduced to the spans a reader reads as sentences.

    Removed, in order, because each one otherwise contaminates a count:
    front matter, fenced blocks, indented blocks, tables, inline code, link
    URLs, bare URLs, paths, CLI flags, snake_case identifiers, lesson ids and
    ISO dates. Heading and list markers go too, but their text stays: a heading
    is prose a reader reads.
    """
    t = FRONT_MATTER.sub("", text)
    t = FENCE.sub("\n", t)
    t = INDENTED.sub("", t)
    t = TABLE_ROW.sub("", t)
    t = INLINE_CODE.sub(" ", t)
    t = LINK.sub(r"\1", t)
    t = BARE_URL.sub(" ", t)
    t = LESSON_ID.sub(" ", t)
    t = ISO_DATE.sub(" ", t)
    t = PATHISH.sub(" ", t)
    t = FLAG.sub(" ", t)
    t = IDENT.sub(" ", t)
    t = HRULE.sub("", t)
    t = QUOTE.sub("", t)
    t = HEADING.sub("\n", t)
    t = LIST_MARK.sub("\n", t)
    t = EMPHASIS.sub("", t)
    return t


# ----------------------------------------------------------------- sentences

# Split after . ? ! when the next thing starts a new sentence. Guarded against
# the three cases that produce phantom sentences in this repo's prose:
# abbreviations (e.g., i.e., vs.), version and section numbers (0.5, ADR-0005.2),
# and ellipsis.
ABBREV = r"(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)(?<!\betc)(?<!\bcf)(?<!\bNo)"
SENT_END = re.compile(ABBREV + r"(?<!\.\.)(?<=[.?!])[\"')\]]*\s+(?=[A-Z֐-׿(\[])")
DIGIT_DOT = re.compile(r"(?<=\d)\.(?=\d)")


def paragraphs(prose):
    """Blocks separated by a blank line, with hard-wrapped lines rejoined.

    This is not cosmetic. Splitting on every newline measured LINE length and
    called it sentence length: on docs/specs/2026-07-31-research-corpus-and-cache.md
    it reported mean 7.5 words and a maximum of 21, for a document whose real
    sentences run past 40. Every variance figure downstream of that was a
    statistic about the author's wrap column. Headings and list items are given
    their own blank line by prose_of() so they stay separate units.
    """
    out = []
    for block in re.split(r"\n\s*\n", prose):
        joined = " ".join(l.strip() for l in block.split("\n") if l.strip())
        if joined:
            out.append(joined)
    return out


def sentences(prose):
    """Sentence spans, minimum two words. A one-word line is a label, not a
    sentence, and counting labels drags the variance toward zero for free."""
    out = []
    for b in paragraphs(prose):
        for s in SENT_END.split(b):
            s = s.strip()
            if len(s.split()) >= 2:
                out.append(s)
    return out


# ------------------------------------------------------------------- metrics

WORD = re.compile(r"[A-Za-z֐-׿][\w'’-]*")
# A hyphen compound: word-word, both sides alphabetic. Rules out ranges (10-20),
# leading dashes and trailing dashes.
HYPHEN_COMPOUND = re.compile(
    r"(?<![\w-])[A-Za-z֐-׿]+(?:-[A-Za-z֐-׿]+)+(?![\w-])")


def measure(text):
    """Density and variance for one markdown document.

    hyphen_rate is per word, not per character: 2.8 percent of words carrying a
    compound is a different claim from 2.8 percent of bytes, and the word figure
    is the one a reader perceives.

    Both a character and a word view of sentence length are reported because the
    observed 14.8 in L-2026-07-31-b came without a unit, and picking one would
    be guessing at the very number this is meant to settle.
    """
    prose = prose_of(text)
    words = WORD.findall(prose)
    nw = len(words)
    comp = HYPHEN_COMPOUND.findall(prose)
    sents = sentences(prose)
    wlen = [len(s.split()) for s in sents]
    clen = [len(s) for s in sents]

    def sd(xs):
        return statistics.pstdev(xs) if len(xs) > 1 else 0.0

    mw = statistics.mean(wlen) if wlen else 0.0
    mc = statistics.mean(clen) if clen else 0.0
    return {
        "words": nw,
        "sentences": len(sents),
        "hyphen_compounds": len(comp),
        "hyphen_rate": len(comp) / nw if nw else 0.0,
        "sent_words_mean": mw,
        "sent_words_sd": sd(wlen),
        "sent_words_cv": sd(wlen) / mw if mw else 0.0,
        "sent_chars_mean": mc,
        "sent_chars_sd": sd(clen),
        "sent_chars_cv": sd(clen) / mc if mc else 0.0,
    }


# ----------------------------------------------------------------- fitting

PCTS = (10, 25, 50, 75, 90, 95, 99)


def _pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p / 100
    f = math.floor(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def fit(texts, name, scope, min_words=200):
    """Empirical distribution over a named corpus of real documents.

    min_words drops stubs. A 30-word index page has one sentence and a variance
    of zero, and a corpus of those would band every real document as suspicious.

    Nothing calls this yet with an authored corpus, because none exists at this
    register. It is here so that the threshold, when it is set, is set by fitting
    and not by taste.
    """
    ms = [measure(t) for t in texts]
    ms = [m for m in ms if m["words"] >= min_words and m["sentences"] >= 5]
    if not ms:
        raise ValueError(f"no documents met min_words={min_words} for {name}")
    prof = {"name": name, "scope": scope, "n": len(ms), "kind": "MEASURED",
            "metrics": {}}
    for key in ("hyphen_rate", "sent_words_sd", "sent_words_cv",
                "sent_chars_sd", "sent_chars_cv"):
        vals = [m[key] for m in ms]
        prof["metrics"][key] = {f"p{p}": round(_pct(vals, p), 6) for p in PCTS}
    return prof
