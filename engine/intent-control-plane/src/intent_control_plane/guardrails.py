"""Anti-reward-hacking screen, scoped-diff check, topology-fitness pre-check (P21, constraints 6-7).

Three cheap guards on the depth loop. reward_hacking_flags screens a proposed diff for the gaming
patterns the 2026 literature documented: deleting the check that would fail it, skipping a test, or
suppressing a gate. is_scoped_diff rejects full-file rewrites and over-broad diffs, because
full-rewrite freedom measurably increases both the frequency and subtlety of reward hacking, so a
swarm worker only gets to make a scoped edit. topology_fitness decides swarm vs orchestrate before
fanning out: swarm only when the work is decomposable and loosely coupled, else sequence it (a wrong
topology actively degrades performance).

Pure functions, no I/O.
"""
from __future__ import annotations

import re

# (pattern, flag) pairs matched against unified-diff lines. Removed lines start '-', added '+'.
_GAMING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^-\s*(assert|raise)\b"), "removed-assertion-or-raise"),
    (re.compile(r"^-\s*(def|async def)\s+test_"), "removed-test-case"),
    (re.compile(r"^\+.*(pytest\.skip|@pytest\.mark\.(skip|xfail)|\.skip\(|xit\()"), "added-test-skip"),
    (
        re.compile(r"^\+.*(#\s*type:\s*ignore|eslint-disable|continueOnError\s*:\s*true|\|\|\s*true|--no-verify)"),
        "added-check-suppression",
    ),
]


def reward_hacking_flags(diff_text: str) -> list[str]:
    """Return the distinct gaming patterns found in a proposed diff (empty for a clean diff)."""
    flags: set[str] = set()
    for line in diff_text.splitlines():
        for pattern, flag in _GAMING_PATTERNS:
            if pattern.search(line):
                flags.add(flag)
    return sorted(flags)


def is_scoped_diff(diff_text: str, max_files: int = 3, max_removed_per_file: int = 120) -> bool:
    """True if the diff is a bounded, scoped edit rather than a full-file rewrite or a sprawling change.

    Rejects when it touches more than max_files files, or when any single file removes more than
    max_removed_per_file lines (the signature of a wholesale rewrite).
    """
    files = 0
    removed_in_file = 0
    scoped = True
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            files += 1
            removed_in_file = 0
        elif line.startswith("-") and not line.startswith("---"):
            removed_in_file += 1
            if removed_in_file > max_removed_per_file:
                scoped = False
    return scoped and files <= max_files


def topology_fitness(local_passes: int, coupling: float) -> str:
    """Choose 'swarm' (independent local passes) or 'orchestrate' (coupled work) before fanning out.

    Swarm only when there are at least two independent passes AND coupling is low; otherwise a
    single orchestrated sequence, since a wrong topology degrades performance rather than helping.
    """
    if local_passes >= 2 and coupling < 0.5:
        return "swarm"
    return "orchestrate"
