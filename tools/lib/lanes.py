"""Canonical lane identifiers, and the one thing that makes them readable across
the 2026-07-30 renumber.

Lane letters were B/C/D/E from ADR-0013 until 2026-07-30, when the operator
renumbered them to A/B/C/D so the live set starts at A again (retired Lane A had
left a hole at the front). The renumber is a pure relabel: no charter's scope
changed, only its letter.

The hazard this module exists to close: the letters COLLIDE across the cutover.
`{"lane": "B"}` written on 2026-07-29 means the harness; the identical row written
on 2026-07-31 means the resume engine. state/*.jsonl are append-only ledgers and
state/bus.jsonl is hash-chained, so the historical rows were deliberately NOT
rewritten -- rewriting them would have destroyed the chain and falsified the record
to make a cosmetic rename look clean. Instead every reader of a lane field in a
ledger resolves it through `resolve`, which needs the row's timestamp.

A reader that ignores the timestamp will silently attribute 396 refutation rows and
11 lessons to the wrong lane. That is the failure mode this module is here to make
impossible to reach by accident, so `resolve` requires the timestamp positionally
rather than defaulting it to now.
"""

from __future__ import annotations

# The instant the renumber landed. Rows stamped at or after this belong to scheme 2.
# Deliberately a date boundary rather than a commit time: the ledgers carry
# whole-second UTC stamps and no row was written during the renumber itself, so a
# coarser boundary cannot misfile a row and is auditable by eye.
SCHEME_2_CUTOVER = "2026-07-30T00:00:00Z"

# scheme 2 (current). The letter a new row must use.
LANE_NAMES = {
    "A": "claude-setup harness",
    "B": "resume / hiring engine",
    "C": "learning (hasadna)",
    "D": "content and publishing",
    "?": "unmapped cwd (not a lane)",
}

# scheme 1 (pre-2026-07-30). Kept so a historical row can still be NAMED, not just
# relabelled. Retired Lane A is in here because rows predating 2026-07-29 can carry
# it, and a resolver that cannot name a letter it will encounter is not a resolver.
LANE_NAMES_SCHEME_1 = {
    "A": "concierge (retired 2026-07-29, never used)",
    "B": "claude-setup harness",
    "C": "resume / hiring engine",
    "D": "learning (hasadna)",
    "E": "content and publishing",
    "?": "unmapped cwd (not a lane)",
}

# scheme 1 letter -> scheme 2 letter. Retired Lane A maps to nothing: its scope was
# folded into the harness lane, but a row it wrote is not a harness row, so it stays
# distinguishable as RETIRED rather than being quietly merged into A's new meaning.
SCHEME_1_TO_2 = {
    "B": "A",
    "C": "B",
    "D": "C",
    "E": "D",
    "?": "?",
}


def scheme_for(ts: str) -> int:
    """Which numbering scheme a row's `lane` field was written under.

    `ts` is the row's own ISO-8601 UTC timestamp. An empty or unparseable stamp
    returns 1, not 2: the ledgers that predate the cutover are the ones with loose
    stamping, and defaulting an undated row to the CURRENT scheme would relabel
    history, which is the exact error this module exists to prevent.
    """
    if not ts:
        return 1
    return 2 if str(ts) >= SCHEME_2_CUTOVER else 1


def resolve(letter: str, ts: str) -> tuple[str, str]:
    """Map a ledger row's lane letter to (current_letter, human_name).

    `ts` is required. See the module docstring: a timestamp-free resolve is the bug.

    A scheme-1 "A" resolves to ("RETIRED", ...) rather than to a live lane, because
    the retired concierge lane's scope was folded into the harness lane without its
    rows becoming harness rows.
    """
    letter = (letter or "?").strip().upper()
    if scheme_for(ts) == 2:
        return letter, LANE_NAMES.get(letter, "unknown lane {!r}".format(letter))
    if letter == "A":
        return "RETIRED", LANE_NAMES_SCHEME_1["A"]
    new = SCHEME_1_TO_2.get(letter)
    if new is None:
        return "?", "unknown scheme-1 lane {!r}".format(letter)
    return new, LANE_NAMES[new]


def selftest() -> int:
    """Prove the resolver distinguishes the collision. Exit code is failure count."""
    failures = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append("{}: got {!r} want {!r}".format(label, got, want))

    # The collision itself: same letter, different meaning, decided by the stamp.
    check("pre-cutover B is the harness",
          resolve("B", "2026-07-29T12:00:00Z"), ("A", "claude-setup harness"))
    check("post-cutover B is the resume engine",
          resolve("B", "2026-07-31T12:00:00Z"), ("B", "resume / hiring engine"))

    # Every scheme-1 lane relabels to a live scheme-2 lane.
    check("C -> B", resolve("C", "2026-07-29T00:00:00Z")[0], "B")
    check("D -> C", resolve("D", "2026-07-29T00:00:00Z")[0], "C")
    check("E -> D", resolve("E", "2026-07-29T00:00:00Z")[0], "D")

    # Retired A does not become the harness lane.
    check("retired A stays distinguishable",
          resolve("A", "2026-07-28T00:00:00Z")[0], "RETIRED")

    # An undated row is history, not current. Getting this backwards would relabel
    # every loosely-stamped row in the ledgers.
    check("undated row is scheme 1", scheme_for(""), 1)
    check("cutover instant itself is scheme 2", scheme_for(SCHEME_2_CUTOVER), 2)

    # The two name tables must cover the same letters they claim to map.
    for old, new in SCHEME_1_TO_2.items():
        if old not in LANE_NAMES_SCHEME_1:
            failures.append("scheme-1 letter {!r} has no name".format(old))
        if new not in LANE_NAMES:
            failures.append("scheme-2 letter {!r} has no name".format(new))

    for line in failures:
        print("FAIL " + line)
    print("lanes selftest: {} checks failed".format(len(failures)))
    return len(failures)


if __name__ == "__main__":
    import sys

    sys.exit(1 if selftest() else 0)
