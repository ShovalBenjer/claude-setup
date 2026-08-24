"""Mutation spec for tools/audit/skill_deps.py.

The classifier answers "can this skill start on this host". Its two ways of being
useless are opposites: pass everything (then it never rejects an Obsidian skill),
or trip on data (then it flags a dictionary for containing the word "notion",
which the first real run actually did). Both are mutated here.
"""

TARGET = "engine/tools/audit/skill_deps.py"
ARGV = ["selftest"]

MUTATIONS = [
    (
        "probe always finds the binary",
        "Every absent binary reads as present, so a skill that cannot start is "
        "reported runnable. This is the failure that would have let the operator's "
        "rejected recommendations back in.",
        "    return shutil.which(name) is not None",
        "    return True",
    ),
    (
        "no requirement is ever detected",
        "Every skill classifies as unbound, which looks like a clean tree and is "
        "the most reassuring possible way for this check to be worthless.",
        "    found: list[tuple[str, str, str]] = []\n    for name, kind, pat in REQUIREMENTS:",
        "    found: list[tuple[str, str, str]] = []\n    for name, kind, pat in []:",
    ),
    (
        "wordlists are scanned as instructions",
        "A 200,000-line English lexicon reads as a Notion and Obsidian dependency, "
        "which is the exact false positive looks_like_wordlist was written to stop.",
        "    if len(lines) < 200:\n        return False",
        "    if len(lines) < 200:\n        return False\n    return False",
    ),
    (
        "blocked rows carry no evidence",
        "The verdict survives but the snippet that lets a human downgrade it does "
        "not, so 26 blocked becomes an unauditable number instead of a gradable list.",
        '"evidence": {k: why[k] for k in sorted(set(absent))}',
        '"evidence": {}',
    ),
]

MUTATIONS.append((
    "--strict never fails",
    "The one path proposed for a gate domain (TODO SKILLDEP-03) always exits 0, so "
    "wiring it in would add a domain that can only ever pass. A check that cannot "
    "go red is worse than no check, because it reports coverage.",
    'return 1 if a.strict and counts["blocked"] else 0',
    "return 0",
))
