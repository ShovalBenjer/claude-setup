# -*- coding: utf-8 -*-
"""Slop lint — gate on prose deliverables (Deep Work Protocol rule 7, ADR-0005).
Flags LLM-overrepresented patterns vs a human baseline (Antislop ICLR 2026 method,
harness-side banlist). Not a style suggestion — a gate: exit 1 on hits.

Usage: slop_lint.py <file.md> [...]   (or - for stdin)
"""
import json, os, re, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prose_metrics  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
from finding import Finding  # noqa: E402

# scan()'s three-tuple kinds map onto Finding.severity. Every kind here is a
# hard fail in main() (exit 1), so "phrase"/"em/en-dash"/"ritual" are all
# "high" — there is no existing soft/warn tier in this checker's CLI contract
# for check() to preserve, unlike panel.py's high/medium/low personas.
_KIND_SEVERITY = {"phrase": "high", "em/en-dash": "high", "ritual": "high"}

# Density and variance, added 2026-07-31 for L-2026-07-31-b. WARN ONLY, and it
# stays warn-only until a fitted band exists: the file this gate cleared while
# reading as machine written had zero dashes, so the banlist above is evidence
# about one list and one dash rule and nothing more. Scores are appended to
# state/prose-scores.jsonl so the threshold comes from a week of distribution
# rather than from taste. See prose_metrics.py for why no number is asserted here.
SCORES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "state", "prose-scores.jsonl")


def log_prose(path, text):
    """Measure and record. Never fails the run: a broken collector must not
    start rejecting prose that the gate itself has no rule against."""
    try:
        m = prose_metrics.measure(text)
        if m["words"] < 200 or m["sentences"] < 5:
            return None
        if os.environ.get("SLOP_NO_LOG") or not os.path.isdir(os.path.dirname(SCORES)):
            return m
        row = {"ts": datetime.datetime.now(datetime.timezone.utc)
               .strftime("%Y-%m-%dT%H:%M:%SZ"), "file": os.path.basename(path)}
        row.update({k: (round(v, 6) if isinstance(v, float) else v)
                    for k, v in m.items()})
        with open(SCORES, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return m
    except Exception as e:                       # collector, not gate
        print(f"prose_metrics unavailable: {e}", file=sys.stderr)
        return None

# Lexical slop: phrases far more common in LLM text than human writing.
BANNED_PHRASES = [
    r"\bdelve\b", r"\btapestry\b", r"\bit'?s worth noting\b", r"\bin today'?s .{0,20}world\b",
    r"\bnavigat(e|ing) the .{0,20}(landscape|complexit)", r"\bunlock(ing)? the (power|potential)\b",
    r"\bat the end of the day\b", r"\ba testament to\b", r"\bin the realm of\b",
    r"\bplays? a (crucial|pivotal|vital) role\b", r"\bfoster(ing)? .{0,15}(collaboration|innovation)\b",
    r"\bseamless(ly)?\b", r"\brobust(ness)?\b.{0,20}\bsolution\b", r"\bever-(evolving|changing)\b",
    r"\bharness(ing)? the\b", r"\bempower(ing|s|ed)?\b", r"\bcutting-edge\b",
    r"\brich tapestry\b", r"\bstands? as a\b", r"\bunderscore(s|d)?\b",
]
# Structural slop
DASH = re.compile(r" [—–] ")                       # em/en dash as connector (Shoval rule)
RULE_OF_THREE = re.compile(r"\b(\w+), (\w+),? and (\w+)\b")  # heuristic; reported as soft

# Ritual acknowledgement, added 2026-07-30. Kept byte-identical to the copies in
# payload/dot-claude/hooks/completion_gate.py so the file channel and the response channel
# cannot correct the operator differently. tests/test_completion_gate.py pins the pair.
RITUAL = re.compile(
    r"(?i)(?:"
    r"\byou(?:'re| are|r)\s+(?:absolutely\s+|completely\s+|totally\s+|quite\s+|so\s+)?"
    r"(?:right|correct)\b"
    r"|\bthat'?s\s+(?:absolutely\s+|completely\s+)?(?:right|correct|fair|a fair point)\b"
    r"|\b(?:good|great|fair|excellent|nice)\s+(?:catch|point|call|question|spot)\b"
    r"|\bmy apolog(?:y|ies)\b|\bi apologi[sz]e\b"
    r"|\b(?:thanks|thank you)\s+for\s+(?:the\s+)?(?:catch|correction|pointing|flagging)"
    r")"
)
# Anchored to line start so "perfect for this" survives and "Perfect." does not.
RITUAL_OPENER = re.compile(
    r"^\s*(?:Perfect|Great|Excellent|Amazing|Wonderful|Fantastic|Awesome|Brilliant|"
    r"Absolutely|Certainly|Indeed|Nice|Exactly|Spot on|Good news)\b[\s!.,:;]",
    re.MULTILINE,
)


def scan(text):
    hits = []
    for pat in BANNED_PHRASES:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append(("phrase", m.group(0), text[:m.start()].count("\n") + 1))
    for m in DASH.finditer(text):
        hits.append(("em/en-dash", m.group(0).strip(), text[:m.start()].count("\n") + 1))
    for pat in (RITUAL, RITUAL_OPENER):
        for m in pat.finditer(text):
            hits.append(("ritual", m.group(0).strip(), text[:m.start()].count("\n") + 1))
    return hits


def check(diff_or_text, file=""):
    """The item-2 shared-signature entry point (docs/taste.md, 2026-08-24):
    check(diff_or_text) -> list[Finding]. Wraps scan() rather than
    reimplementing it, so the two can never drift on what counts as a hit;
    scan() stays the single source of truth and this is purely a Finding
    adapter. `file` is optional since slop_lint historically operates on
    whatever text it's handed (a file's content or stdin), not a diff with
    its own embedded path."""
    return [
        Finding(checker=f"slop_lint.{kind.replace('/', '-')}", severity=_KIND_SEVERITY[kind],
                file=file, line=line, why=f"{kind}: {frag!r}", snippet=frag, source="local")
        for kind, frag, line in scan(diff_or_text)
    ]


def main():
    args = sys.argv[1:] or ["-"]
    total = 0
    for a in args:
        text = sys.stdin.read() if a == "-" else open(a, encoding="utf-8", errors="replace").read()
        hits = scan(text)
        for kind, frag, line in hits:
            print(f"{a}:{line}: [{kind}] {frag!r}")
        total += len(hits)
        m = log_prose(a, text)
        if m:
            print(f"{a}: [density] hyphen {m['hyphen_rate']*100:.2f}% of "
                  f"{m['words']} words | sentence sd {m['sent_words_sd']:.1f}w "
                  f"{m['sent_chars_sd']:.1f}c over {m['sentences']} sentences "
                  f"(no band fitted; measurement only)", file=sys.stderr)
    if total:
        print(f"\nSLOP: {total} hit(s). Regenerate the flagged spans with the constraint named.", file=sys.stderr)
        sys.exit(1)
    print("clean", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
