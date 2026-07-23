# -*- coding: utf-8 -*-
"""Slop lint — gate on prose deliverables (Deep Work Protocol rule 7, ADR-0005).
Flags LLM-overrepresented patterns vs a human baseline (Antislop ICLR 2026 method,
harness-side banlist). Not a style suggestion — a gate: exit 1 on hits.

Usage: slop_lint.py <file.md> [...]   (or - for stdin)
"""
import re, sys

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


def scan(text):
    hits = []
    for pat in BANNED_PHRASES:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append(("phrase", m.group(0), text[:m.start()].count("\n") + 1))
    for m in DASH.finditer(text):
        hits.append(("em/en-dash", m.group(0).strip(), text[:m.start()].count("\n") + 1))
    return hits


def main():
    args = sys.argv[1:] or ["-"]
    total = 0
    for a in args:
        text = sys.stdin.read() if a == "-" else open(a, encoding="utf-8", errors="replace").read()
        hits = scan(text)
        for kind, frag, line in hits:
            print(f"{a}:{line}: [{kind}] {frag!r}")
        total += len(hits)
    if total:
        print(f"\nSLOP: {total} hit(s). Regenerate the flagged spans with the constraint named.", file=sys.stderr)
        sys.exit(1)
    print("clean", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
