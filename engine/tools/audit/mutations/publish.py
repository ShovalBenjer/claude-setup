"""Mutations for tools/telemetry/publish.py.

The sibling spec `telemetry.py` covers the collector. This one covers the half that
actually reaches GitHub, and it exists because moving the publishing surface exposed a
selftest assertion that had been self-satisfying since the file was written.

THE SELF-SATISFYING CHECK, recorded because it is the interesting part.

publish.py's safety property is that nothing posts without an explicit flag and an
explicit target. It was asserted like this:

    src = Path(__file__).read_text(encoding="utf-8")
    if "args.post and args.issue" not in src:
        failures.append("the post path is not gated on BOTH --post and --issue")

`src` is the file's own text, and the assertion LINE contains the literal it searches
for. So the check found itself and passed, and would have kept passing with the real
gate deleted. A source-parsing oracle that reads a flat string over its own body cannot
distinguish the code from the assertion about the code. It is the same defect class as
L-2026-07-29-d, where panel.py matched a dangerous call quoted inside a comment
explaining why it is not used, arriving here from the opposite direction.

It is now read from main()'s AST, so the assertion lives in a different function node
and cannot see itself. The first two mutations below break the gate in the two ways that
matter and would BOTH have survived the old form.

WHAT ELSE IS DEFENDED. The cursor is the feed's memory: it advances only on a successful
post, and it is per-surface so that a migration does not repost 130 already-published
items into a brand new discussion. The throttle must run before the ledger walk, because
a timer firing every 30 minutes should not pay a ten-ledger sweep to discover it had
nothing to do. And a fingerprint must stay timestamp-independent, because 160 collapses
in the live corpus depend on it.
"""

TARGET = "engine/tools/telemetry/publish.py"
ARGV = ["--selftest"]

MUTATIONS = [
    # ---- the gate the old check could not see ----
    ("the post path stops requiring a resolved sink",
     "a run with --post and no target would take the posting branch, call post() on "
     "nothing, and report success. The old substring assertion passed through exactly "
     "this because it was matching its own source line rather than the gate",
     "    if args.post and sink is not None:",
     "    if args.post:"),

    ("the post path stops requiring --post at all",
     "every dry run becomes a real post. This is the mutation that most obviously must "
     "be caught and it too survived the substring form, which is the whole argument for "
     "reading the AST",
     "    if args.post and sink is not None:",
     "    if sink is not None:"),

    ("a local post() reappears beside the sinks",
     "a second path to GitHub that no --sink flag governs. The surface choice stops "
     "being explicit, and during a migration the retired surface keeps receiving posts "
     "from a caller nobody remembers",
     "def bootstrap(owner: str, repo: str, title: str) -> int:",
     "def post(issue, body):\n    return 0, ''\n\n\n"
     "def bootstrap(owner: str, repo: str, title: str) -> int:"),

    # ---- the cursor, which is the feed's memory ----
    ("the cursor advances even when the post failed",
     "the items are marked published and the post never happened, so they are lost "
     "permanently. A failed post must be retried, which is the only reason the cursor "
     "is written after the return code is checked rather than before",
     "        if rc == 0:\n            write_cursor({fingerprint(e) for e in shown}, cursor)",
     "        if True:\n            write_cursor({fingerprint(e) for e in shown}, cursor)"),

    ("every sink shares one cursor again",
     "the migration reposts up to 25 already-published items into the brand new surface, "
     "which is the worst possible first impression for a feed whose measured problem is "
     "that nobody reads it. It also makes the throttle global, so a post to one surface "
     "suppresses a post to the other",
     '    return CURSOR if sink_name == "issue" else STATE / "telemetry-published-{}.txt".format(sink_name)',
     "    return CURSOR"),

    ("seeding a cursor also posts",
     "--seed-cursor-from exists to make the first discussion post genuinely new material. "
     "If it posts as well, the operator's one preparatory step becomes the thing it was "
     "meant to prevent",
     '        print("seeded {} with {} fingerprint(s) from {} ({} were already there). "\n'
     '              "NOTHING was posted.".format(cursor.name, len(incoming - already), src.name,\n'
     "                                           len(already & incoming)))\n        return 0",
     '        print("seeded {} with {} fingerprint(s) from {} ({} were already there). "\n'
     '              "NOTHING was posted.".format(cursor.name, len(incoming - already), src.name,\n'
     "                                           len(already & incoming)))"),

    # ---- ordering and volume ----
    ("the throttle runs after the ledger walk",
     "the timer fires every 30 minutes and pays a ten-ledger sweep across every repo "
     "before discovering it was throttled. The cost this ordering exists to avoid is "
     "the entire reason the throttle is not simply a check at the end",
     "    if args.throttle:\n        age = minutes_since_last_post(cursor)",
     "    events, _ = collect.collect(collect.parse_since(args.since))\n"
     "    if args.throttle:\n        age = minutes_since_last_post(cursor)"),

    ("trace-level volume reaches the feed",
     "7000 of 7029 gate rows are PASS. Publishing them buries every alert on the first "
     "post, which is the death the cap and the severity split both exist to prevent",
     "    fresh = [e for e in events\n"
     "             if e[\"severity\"] in (collect.ALERT, collect.NOTE)\n"
     "             and fingerprint(e) not in seen]",
     "    fresh = [e for e in events if fingerprint(e) not in seen]"),

    ("a truncated post stops saying how much it dropped",
     "the reader believes they have seen everything. A cap that is invisible is a lie "
     "about coverage, and this feed's cap is 25 against windows that routinely hold "
     "hundreds",
     "    if dropped:",
     "    if False:"),

    # ---- dedupe ----
    ("the fingerprint starts including the timestamp",
     "the plausible-looking fix for a duplicate-looking feed, and it deletes the "
     "guarantee. 160 collapses in the live corpus are the same fact re-read on a later "
     "run. Keying on ts reposts every standing alert forever, which is what taught the "
     "reader to skim the bus into uselessness",
     '    key = "|".join(str(ev.get(k, "")) for k in ("repo", "source", "kind", "subject", "ref"))',
     '    key = "|".join(str(ev.get(k, "")) for k in ("repo", "source", "kind", "subject", "ref", "ts"))'),
]
