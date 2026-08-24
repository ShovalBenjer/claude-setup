"""Mutation spec for tools/audit/pile.py.

This tool's output is a deletion list. Every failure mode here ends with a file
being removed that should have survived, which is the one direction that cannot
be undone by re-running the scan.
"""

TARGET = "engine/tools/audit/pile.py"
ARGV = ["selftest"]

MUTATIONS = [
    (
        "runtime instruction files lose their protection",
        "dot-codex/AGENTS.md is byte-identical to the root CLAUDE.md and would be "
        "proposed for deletion, silently unconfiguring the Codex runtime. The "
        "first real run did exactly this and it was caught by reading the list, "
        "not by the tool.",
        "        if os.path.basename(f) in PROTECTED_BASENAMES:\n            continue",
        "        if False:\n            continue",
    ),
    (
        "forks are reported as identical",
        "A skill that diverged across trees reads as a safe collapse, so the "
        "merge silently discards whichever version did not win.",
        "        identical = len(set(sigs.values())) == 1",
        "        identical = True",
    ),
    (
        "a skill's SKILL.md is counted as a loose document too",
        "The same file appears in both halves of the manifest, so the document "
        "count and the skill count disagree about it and a collapse can be "
        "proposed twice from two different rules.",
        "        if any(f.startswith(t + \"/\") for t in PAYLOAD_TREES):\n            continue",
        "        if False:\n            continue",
    ),
    (
        "the survivor is not excluded from the removal list",
        "Every copy including the one meant to be kept lands in "
        "proposed_removals, so collapsing a group deletes the content outright.",
        '"proposed_removals": [p for p, _ in ordered[1:]],',
        '"proposed_removals": [p for p, _ in ordered],',
    ),
]
