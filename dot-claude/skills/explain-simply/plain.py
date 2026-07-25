#!/usr/bin/env python3
"""Measure whether a piece of writing is actually plain, instead of asserting it.

Why this is a script and not only a SKILL.md. A skill that says "write simply" is
a wish. Every previous style rule in this repo was enforced by nothing, so drift
was invisible: the rule and its violation looked identical from outside. This file
turns each rule into a check that can print [FAIL] against real text, which means
a claim about readability can name a command instead of a feeling.

The rules and their numbers are sourced, not invented:

  digital.gov/guides/plain-language/writing  (the successor host for
  plainlanguage.gov, which 301-redirects there)
    - active voice, present tense
    - no hidden verbs: a real verb turned into a noun and propped up by a weak
      linking verb ("conduct an analysis of" for "analyze")
    - shorter words, short sections, short paragraphs, one topic per paragraph

  Federal plain-language guidance, numeric targets
    - average sentence 15 to 20 words, no single sentence over 25
    - active voice in MORE than half of sentences
    - no acronym used before it is expanded
    - public-facing text at roughly a 7th to 8th grade reading level

Three sources could not be read and so contributed nothing: the DOL plain-language
PDF returned HTTP 403, wid.org's Federal PL Guidelines PDF returned unparsed
binary, and the Australian Style Manual sentence-length page timed out at 60s. If
a number below looks unfamiliar it came from the two sources above, not from those.

One rule here is this repository's own and has no external source, stated plainly
so nobody mistakes it for a plain-language convention: `unbacked_number`. A numeral
in prose must also appear somewhere in the document inside code, because in this
repo a number in claim text is a liability unless a command produced it. That rule
exists because "24% to 64%" survived in resume copy for weeks with no measurement
behind it and had to be retracted.

Known limits, stated rather than hidden:

  Passive detection is the be-verb-plus-past-participle heuristic, the same one
  the sources describe. It over-reports: "was tired" and "is interested" are
  adjectives, not passives. That is why the check is a RATIO against a threshold
  and never "zero passives" -- an over-reporting detector with a zero threshold
  would be unusable, and an unusable check gets deleted or ignored, which is worse
  than a loose one.

  Sentence splitting is regex, not a parser. Decimals and a short abbreviation
  list are protected; "Sec. 3" style references will split wrongly.

  Headings, fenced code, inline code, table rows and URLs are removed before any
  prose measurement. A heading is not a sentence and would otherwise merge into
  the paragraph below it and corrupt every length number.

Usage:
    plain.py check FILE [FILE ...]   exit 1 if any check fires
    plain.py check FILE --json       machine-readable findings
    plain.py selftest                prove every check can fire AND can stay quiet
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):          # console codepage here is cp1255
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- thresholds -----------------------------------------------------------
# Each is compared with an explicit boundary so an off-by-one is catchable: the
# selftest plants text sitting exactly ON each boundary and requires silence.
MAX_SENTENCE_WORDS = 25      # no single sentence over 25 words
MAX_AVG_WORDS = 20           # average sentence 15-20 words, so 20 is still fine
MIN_ACTIVE_RATIO = 0.5       # active in MORE than half, so exactly half fails
MAX_PARAGRAPH_SENTENCES = 5  # short paragraphs, one topic each

BE_FORMS = {
    "am", "is", "are", "was", "were", "be", "been", "being",
}
# Modals and auxiliaries that legitimately precede "be"/"been" in a passive.
PRE_BE = {"could", "should", "would", "will", "shall", "may", "might", "must",
          "can", "has", "have", "had", "is", "are", "was", "were"}

IRREGULAR_PARTICIPLES = {
    "given", "taken", "made", "done", "seen", "known", "shown", "written",
    "held", "kept", "left", "sent", "built", "found", "told", "brought",
    "caught", "chosen", "driven", "drawn", "eaten", "fallen", "forgotten",
    "gotten", "hidden", "lost", "meant", "met", "paid", "put", "read",
    "run", "said", "set", "spent", "split", "spoken", "thrown", "understood",
    "broken", "begun", "cut", "dealt", "felt", "let", "lit", "proven",
}
# Adjectival be-complements that the heuristic would otherwise call passive.
PARTICIPLE_FALSE_FRIENDS = {
    "tired", "interested", "excited", "pleased", "worried", "concerned",
    "aware", "able", "required", "needed", "supposed", "used", "based",
    "limited", "related", "involved", "detailed", "advanced",
}

# A weak linking verb followed closely by a nominalization is a hidden verb.
LINKING_VERBS = {
    "achieve", "achieves", "achieved", "effect", "effects", "effected",
    "give", "gives", "gave", "given", "have", "has", "had", "make", "makes",
    "made", "reach", "reaches", "reached", "take", "takes", "took", "taken",
    "conduct", "conducts", "conducted", "perform", "performs", "performed",
    "provide", "provides", "provided", "undertake", "undertakes", "undertook",
}
# "ysis" is here because the source's own worked example is "conduct an analysis
# of" -> "analyze", and an -ysis noun matches none of the other suffixes.
NOMINAL_SUFFIXES = ("ment", "ments", "tion", "tions", "sion", "sions",
                    "ance", "ances", "ence", "ences", "ity", "ities",
                    "ysis", "yses")

# Acronyms nobody expands in an engineering document. Anything else must be
# expanded at or before first use.
WELL_KNOWN_ACRONYMS = {
    "AI", "API", "CI", "CD", "CLI", "CPU", "CSS", "CSV", "DB", "DNS", "DOM",
    "E2E", "GPU", "HTML", "HTTP", "HTTPS", "ID", "IDE", "JSON", "OS", "PDF",
    "PR", "RAM", "REST", "SDK", "SQL", "SSH", "TCP", "TLS", "UI", "URL", "UX",
    "XML", "YAML", "OK", "TODO", "FAQ", "PII", "MIT", "GNU", "USB", "VM",
    "I", "A", "AM", "PM", "US", "UK", "IT", "NO", "ON", "OR", "AND", "TO",
}

# Words that make writing longer without making it clearer, plus the register
# this repo has been told twice to stay out of.
JARGON = {
    "utilize": "use",
    "utilizes": "uses",
    "leverage": "use",
    "leverages": "uses",
    "facilitate": "help",
    "facilitates": "helps",
    "commence": "start",
    "commences": "starts",
    "endeavor": "try",
    "ascertain": "find out",
    "aforementioned": "this",
    "pursuant": "under",
    "herein": "here",
    "thereof": "of it",
    "subsequently": "later",
    "additionally": "also",
    "seamless": "(say what it does)",
    "seamlessly": "(say what it does)",
    "robust": "(say what it survives)",
    "cutting-edge": "(say what it does)",
    "delve": "look",
    "tapestry": "(cut it)",
    "empower": "let",
    "empowers": "lets",
    "elevate": "improve",
    "holistic": "whole",
    "synergy": "(cut it)",
}
JARGON_PHRASES = {
    "in order to": "to",
    "prior to": "before",
    "subsequent to": "after",
    "at this point in time": "now",
    "due to the fact that": "because",
    "in the event that": "if",
    "for the purpose of": "to",
    "with regard to": "about",
    "a number of": "some",
    "it should be noted that": "(cut it)",
}

_ABBR = ("e.g.", "i.e.", "etc.", "vs.", "cf.", "approx.", "Mr.", "Dr.", "No.")
_SENT_HOLE = "\x00"


# --- text extraction ------------------------------------------------------
def split_code_and_prose(text: str) -> tuple[str, str]:
    """Return (prose, code) with code removed from prose but kept for lookup.

    Both halves are needed: prose is what gets measured, and code is what makes
    a numeral in prose defensible. Returning only prose would make
    `unbacked_number` unimplementable, and returning only a stripped string
    would make it unfalsifiable.
    """
    code_parts: list[str] = []

    body = text
    if body.startswith("---\n"):                 # YAML frontmatter is metadata
        end = body.find("\n---", 4)
        if end != -1:
            code_parts.append(body[:end])
            body = body[end + 4:]

    def eat(m):
        code_parts.append(m.group(0))
        return "\n"

    body = re.sub(r"```.*?```", eat, body, flags=re.S)
    body = re.sub(r"`[^`\n]+`", eat, body)
    body = re.sub(r"https?://\S+", " ", body)

    kept = []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):             # a heading is not a sentence
            continue
        if stripped.startswith("|"):             # a table row is not prose
            code_parts.append(line)
            continue
        if set(stripped) <= set("-=*_ ") and stripped:
            continue                             # rule / divider
        # A list item is its own unit, not a sentence inside the paragraph above
        # it. Without the blank line, six bullets read as one six-sentence
        # paragraph and paragraph_too_long fires on writing that is already
        # broken up. A continuation line carries no marker and so still joins
        # the item above it, which is correct.
        marker = re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line)
        if marker:
            kept.append("")
            kept.append(line[marker.end():])
        else:
            kept.append(line)
    return "\n".join(kept), "\n".join(code_parts)


def paragraphs(prose: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]


def sentences(prose: str) -> list[str]:
    """Split into sentences, protecting decimals and a short abbreviation list."""
    t = prose
    for a in _ABBR:
        t = t.replace(a, a.replace(".", _SENT_HOLE))
    t = re.sub(r"(\d)\.(\d)", r"\1" + _SENT_HOLE + r"\2", t)
    out = []
    for part in re.split(r"(?<=[.!?])[)\"']*\s+", t):
        s = part.replace(_SENT_HOLE, ".").strip()
        if s and re.search(r"[A-Za-z]", s):
            out.append(s)
    return out


def words(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]*|\d[\d,.]*", sentence)


def line_of(text: str, snippet: str) -> int:
    probe = snippet[:40]
    i = text.find(probe)
    return text.count("\n", 0, i) + 1 if i >= 0 else 0


# --- individual rules -----------------------------------------------------
def is_passive(sentence: str) -> str | None:
    """Return the matched span if the sentence looks passive, else None.

    Heuristic: a be-verb, optionally after a modal, followed within two words by
    a past participle. False friends are excluded by name because an adjectival
    complement is the dominant false positive.
    """
    toks = [w.lower() for w in words(sentence)]
    for i, tok in enumerate(toks):
        if tok not in BE_FORMS:
            continue
        if tok in ("be", "been") and (i == 0 or toks[i - 1] not in PRE_BE):
            continue
        for j in range(i + 1, min(i + 3, len(toks))):
            cand = toks[j]
            if cand in PARTICIPLE_FALSE_FRIENDS:
                break
            if cand in IRREGULAR_PARTICIPLES or (
                    cand.endswith("ed") and len(cand) > 4):
                return " ".join(toks[i:j + 1])
    return None


def hidden_verbs(sentence: str) -> list[str]:
    """Find a weak linking verb propping up a nominalization."""
    toks = words(sentence)
    hits = []
    for i, tok in enumerate(toks):
        if tok.lower() not in LINKING_VERBS:
            continue
        for j in range(i + 1, min(i + 4, len(toks))):
            cand = toks[j].lower()
            if len(cand) > 6 and cand.endswith(NOMINAL_SUFFIXES):
                hits.append("{} ... {}".format(tok, toks[j]))
                break
    return hits


def unexplained_acronyms(prose: str) -> list[str]:
    """An acronym must be expanded at or before its first use."""
    bad = []
    seen = set()
    for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,7})s?\b", prose):
        acr = m.group(1)
        if acr in WELL_KNOWN_ACRONYMS or acr in seen:
            continue
        seen.add(acr)
        window = prose[max(0, m.start() - 120):m.end() + 120]
        expanded = (
            re.search(r"\(\s*" + re.escape(acr) + r"\s*\)", window)
            or re.search(re.escape(acr) + r"\s*\([A-Za-z][^)]{3,}\)", window)
        )
        if not expanded:
            bad.append(acr)
    return bad


def jargon_hits(prose: str) -> list[str]:
    low = prose.lower()
    hits = []
    for phrase, better in JARGON_PHRASES.items():
        if phrase in low:
            hits.append('"{}" -> "{}"'.format(phrase, better))
    for word, better in JARGON.items():
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            hits.append('"{}" -> "{}"'.format(word, better))
    return hits


def unbacked_numbers(prose: str, code: str) -> list[str]:
    """A numeral in prose must also appear inside code somewhere in the document.

    This repo's own rule, not a plain-language convention. Years are exempt: a
    date is traceable to a calendar. Identifiers such as C-026, v1.2 and
    2026-07-25 never reach here because tokenising on whitespace keeps them
    whole and they fail the pure-numeral shape.
    """
    bad = []
    for raw in prose.split():
        tok = raw.strip("()[]{}.,;:!?\"'`*_")
        if not re.fullmatch(r"\d[\d,]*(?:\.\d+)?%?", tok):
            continue
        digits = tok.rstrip("%")
        if re.fullmatch(r"(?:19|20)\d\d", digits):
            continue
        if digits in code or digits.replace(",", "") in code.replace(",", ""):
            continue
        bad.append(tok)
    return bad


# --- the review -----------------------------------------------------------
def review(text: str) -> dict:
    """Run every rule. Returns findings keyed by check name, plus the stats.

    Findings is a dict and never a list of strings, because the mutation spec
    and the selftest both need to assert WHICH check fired. A flat list would
    let one check's finding satisfy an assertion about another.
    """
    prose, code = split_code_and_prose(text)
    sents = sentences(prose)
    findings: dict[str, list] = {}

    def add(name, item):
        findings.setdefault(name, []).append(item)

    total_words = 0
    passive_n = 0
    for s in sents:
        n = len(words(s))
        total_words += n
        if n > MAX_SENTENCE_WORDS:
            add("sentence_too_long", {"line": line_of(text, s), "words": n,
                                      "text": s[:90]})
        span = is_passive(s)
        if span:
            passive_n += 1
            add("passive_sentence", {"line": line_of(text, s), "span": span,
                                     "text": s[:90]})
        for h in hidden_verbs(s):
            add("hidden_verb", {"line": line_of(text, s), "hit": h})

    avg = (total_words / len(sents)) if sents else 0.0
    active_ratio = ((len(sents) - passive_n) / len(sents)) if sents else 1.0

    if avg > MAX_AVG_WORDS:
        add("avg_sentence_too_long", {"avg": round(avg, 1),
                                      "limit": MAX_AVG_WORDS})
    if sents and active_ratio <= MIN_ACTIVE_RATIO:
        add("passive_majority", {"active_ratio": round(active_ratio, 2),
                                 "need_more_than": MIN_ACTIVE_RATIO})

    for p in paragraphs(prose):
        n = len(sentences(p))
        if n > MAX_PARAGRAPH_SENTENCES:
            add("paragraph_too_long", {"line": line_of(text, p), "sentences": n})

    for acr in unexplained_acronyms(prose):
        add("unexplained_acronym", {"acronym": acr})
    for h in jargon_hits(prose):
        add("jargon", {"hit": h})
    for num in unbacked_numbers(prose, code):
        add("unbacked_number", {"number": num})

    return {
        "findings": findings,
        "stats": {"sentences": len(sents), "avg_words": round(avg, 1),
                  "active_ratio": round(active_ratio, 2),
                  "paragraphs": len(paragraphs(prose))},
    }


# --- commands -------------------------------------------------------------
# Ordered worst-first so the report leads with what is broken.
SEVERITY = ["unbacked_number", "passive_majority", "avg_sentence_too_long",
            "sentence_too_long", "paragraph_too_long", "hidden_verb",
            "unexplained_acronym", "jargon", "passive_sentence"]
# A single passive sentence is information, not a violation: the heuristic
# over-reports, so only the RATIO gates. Listed here so the exemption is
# explicit rather than an accident of which keys the printer happens to read.
ADVISORY = {"passive_sentence"}


def cmd_check(a) -> int:
    reports = {}
    for path in a.paths:
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            if not getattr(a, "quiet", False):
                print("[FAIL] unreadable: {} ({})".format(path, exc))
            return 2
        reports[path] = review(text)

    if a.json:
        print(json.dumps(reports, indent=2, sort_keys=True))

    # The selftest calls this function and asserts on its EXIT CODE, so it passes
    # quiet=True. Without that, a green selftest would print the dirty fixture's
    # own "[FAIL]" lines, and tools/audit/mutate.py attributes a caught mutation
    # by grepping for exactly that marker -- fixture noise would be read as the
    # check that caught it.
    quiet = getattr(a, "quiet", False)
    violations = 0
    for path, rep in reports.items():
        st = rep["stats"]
        hard = {k: v for k, v in rep["findings"].items() if k not in ADVISORY}
        head = "{}  sentences={} avg_words={} active={}".format(
            path, st["sentences"], st["avg_words"], st["active_ratio"])
        if not a.json and not quiet:
            print(("[ok  ] " if not hard else "[FAIL] ") + head)
            for name in SEVERITY:
                for item in rep["findings"].get(name, []):
                    mark = "note " if name in ADVISORY else "FAIL "
                    print("  [{}] {}: {}".format(mark, name, item))
        violations += sum(len(v) for v in hard.values())
    if violations:
        print("\n{} violation(s)".format(violations))
    return 1 if violations else 0


def cmd_selftest(a) -> int:
    """Prove every check can fire AND can stay quiet.

    Both halves are load-bearing. A check that only ever fires is noise, and a
    check nothing can reach is decorative -- this repo has shipped both, most
    recently a deny rule no candidate path could ever match. So each rule gets
    a violating fixture that MUST fire and a boundary fixture sitting exactly on
    the threshold that must NOT, which is what makes an off-by-one visible.
    """
    fails = []

    def bad(msg):
        print("[FAIL] " + msg)
        fails.append(msg)

    def check(cond, msg):
        print("[ok  ] " + msg) if cond else bad(msg)

    def fired(text, name):
        return name in review(text)["findings"]

    w = lambda n: " ".join(["word"] * n)  # noqa: E731 - fixture builder

    # --- sentence length -------------------------------------------------
    # 26 content words fires, exactly 25 does not.
    check(fired("Alpha " + w(25) + ".", "sentence_too_long"),
          "a 26-word sentence is reported")
    check(not fired("Alpha " + w(24) + ".", "sentence_too_long"),
          "a sentence of exactly 25 words is NOT reported (boundary)")

    # --- average sentence length -----------------------------------------
    over = ("Alpha " + w(20) + ". ") * 3          # avg 21
    at = ("Alpha " + w(19) + ". ") * 3            # avg 20 exactly
    check(fired(over, "avg_sentence_too_long"), "an average of 21 words is reported")
    check(not fired(at, "avg_sentence_too_long"),
          "an average of exactly 20 words is NOT reported (boundary)")

    # --- passive ratio ---------------------------------------------------
    p = "The file was written by the tool. "
    act = "The tool writes the file. "
    check(is_passive("The file was written by the tool.") is not None,
          "be-verb plus past participle is detected as passive")
    check(is_passive("The tool writes the file.") is None,
          "a plain active sentence is not called passive")
    check(is_passive("It could have been captured silently.") is not None,
          "modal plus been plus participle is detected as passive")
    check(is_passive("He was tired.") is None,
          "an adjectival be-complement is not called passive (false friend)")
    check(fired(p * 2 + act * 2, "passive_majority"),
          "exactly half active fires, because the rule needs MORE than half")
    check(not fired(p * 2 + act * 3, "passive_majority"),
          "three of five active does NOT fire (boundary)")

    # --- hidden verbs -----------------------------------------------------
    check(hidden_verbs("We conduct an analysis of the data."),
          "a linking verb propping up a nominalization is reported")
    check(not hidden_verbs("We analyze the data."),
          "the direct verb form is NOT reported")
    check(hidden_verbs("The agency made a payment to the vendor."),
          "make plus a nominalization is reported (source's own example)")
    check(not hidden_verbs("The change made the tool faster."),
          "a linking verb with no nearby nominalization is quiet")

    # --- paragraphs -------------------------------------------------------
    six = " ".join("Short line {} here.".format(i) for i in range(6))
    five = " ".join("Short line {} here.".format(i) for i in range(5))
    check(fired(six, "paragraph_too_long"), "a six-sentence paragraph is reported")
    check(not fired(five, "paragraph_too_long"),
          "a five-sentence paragraph is NOT reported (boundary)")
    # Found by running this checker on its own SKILL.md: six bullets were read as
    # one six-sentence paragraph, so the rule fired on writing already broken up.
    bullets = "\n".join("- Short line {} here.".format(i) for i in range(6))
    check(not fired(bullets, "paragraph_too_long"),
          "a six-item list is NOT one paragraph, because a bullet is its own unit")
    check(fired(bullets + "\n\n" + six, "paragraph_too_long"),
          "a real long paragraph beside a list is still reported")

    # --- acronyms ---------------------------------------------------------
    check(fired("The GTMX report is late.", "unexplained_acronym"),
          "an acronym used with no expansion is reported")
    check(not fired("The go-to-market exchange (GTMX) report is late.",
                    "unexplained_acronym"),
          "an acronym expanded before use is NOT reported")
    check(not fired("The JSON file is late.", "unexplained_acronym"),
          "a well-known acronym is NOT reported")

    # --- jargon -----------------------------------------------------------
    check(fired("We utilize the tool in order to ship.", "jargon"),
          "a jargon word and a wordy phrase are both reported")
    check(not fired("We use the tool to ship.", "jargon"),
          "the plain rewrite is NOT reported")
    # Asserted separately by CONTENT, not just by "the jargon key fired". One
    # table going empty would otherwise hide behind the other one still firing.
    check(any("in order to" in h for h in jargon_hits("We ship in order to win.")),
          "the wordy-phrase table is reached")
    check(any("utilize" in h for h in jargon_hits("We utilize it.")),
          "the single-word table is reached")

    # --- unbacked numbers (this repo's own rule) --------------------------
    check(fired("The suite covers 417 cases.", "unbacked_number"),
          "a numeral with nothing behind it is reported")
    check(not fired("The suite covers 417 cases.\n\n```\n417 passed\n```\n",
                    "unbacked_number"),
          "the same numeral is NOT reported once a command output carries it")
    check(not fired("Written on 2026 by hand.", "unbacked_number"),
          "a year is NOT reported (calendar is traceable)")
    check(not fired("See claim C-026 and version v1.2 here.", "unbacked_number"),
          "an identifier holding digits is NOT a bare numeral")

    # --- extraction -------------------------------------------------------
    prose, code = split_code_and_prose(
        "---\nname: x\n---\n# Heading\nReal prose here.\n"
        "- Real bullet text.\n"
        "`inline` and ```\nfenced\n``` and https://example.com/a\n| a | b |\n")
    check("Real bullet text." in prose,
          "a list item's own text survives having its marker removed")
    check("Heading" not in prose, "a heading is removed before measurement")
    check("fenced" not in prose and "fenced" in code,
          "a fenced block leaves prose and lands in code")
    check("inline" not in prose and "inline" in code,
          "inline code leaves prose and lands in code")
    check("example.com" not in prose, "a URL is removed before measurement")
    check("name: x" not in prose, "frontmatter is removed before measurement")
    check("Real prose here." in prose, "actual prose survives extraction")

    # --- the report itself ------------------------------------------------
    # A checker whose exit code does not follow its findings is decorative.
    tmp = tempfile.mkdtemp(prefix="plain-selftest-")
    dirty = os.path.join(tmp, "dirty.md")
    clean = os.path.join(tmp, "clean.md")
    with open(dirty, "w", encoding="utf-8") as fh:
        fh.write("We utilize the tool in order to ship 417 things.\n")
    with open(clean, "w", encoding="utf-8") as fh:
        fh.write("The tool ships the work. It writes one file at a time.\n")

    ns = argparse.Namespace(paths=[dirty], json=False, quiet=True)
    check(cmd_check(ns) == 1, "check exits 1 on a document with violations")
    ns = argparse.Namespace(paths=[clean], json=False, quiet=True)
    check(cmd_check(ns) == 0, "check exits 0 on a clean document")
    ns = argparse.Namespace(paths=[os.path.join(tmp, "missing.md")], json=False,
                            quiet=True)
    check(cmd_check(ns) == 2, "check exits 2 on an unreadable path")

    # An advisory finding must not by itself turn the exit code red, or the
    # over-reporting passive detector would make every document fail.
    only_note = os.path.join(tmp, "note.md")
    with open(only_note, "w", encoding="utf-8") as fh:
        fh.write("The tool writes files. The file was written by the tool. "
                 "It ships now. The work lands here. Nothing else runs.\n")
    rep = review(open(only_note, encoding="utf-8").read())
    ns = argparse.Namespace(paths=[only_note], json=False, quiet=True)
    check("passive_sentence" in rep["findings"]
          and not (set(rep["findings"]) - ADVISORY)
          and cmd_check(ns) == 0,
          "an advisory-only document reports the note and still exits 0")

    print()
    if fails:
        print("{} check(s) FAILED".format(len(fails)))
        return 1
    print("all checks passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="measure one or more files")
    c.add_argument("paths", nargs="+")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)
    s = sub.add_parser("selftest", help="prove the checks can fail")
    s.set_defaults(fn=cmd_selftest)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
