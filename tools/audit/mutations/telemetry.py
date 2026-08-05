"""Mutations for tools/telemetry/collect.py.

This component publishes to GitHub every 30 minutes under a systemd timer and had no
mutation spec and no test file. The 14 specs beside this one cover bus, cdp, codemap,
docmap, gate, panel, plain, refute, skilleval, snap, supply, timetravel and trycmd. The
one instrument that leaves the machine unattended was the one nobody had proved could
fail.

That gap was not theoretical. On 2026-08-05, measured against the live ledgers:

  52 of 516 notable events published with an EMPTY subject and no timestamp
  212 of 516 came from a git worktree of the same repo, counted a second time
  the selftest was GREEN through all of it

The selftest asserted per-source YIELD, which is a real check and caught a real class of
bug, and it says nothing about whether a carried row carries anything. A row that is
emitted and empty consumes a feed slot and reads as coverage, which is worse than a row
that is dropped.

WHAT THIS SPEC IS AIMED AT.

Three of the mutations below re-break the exact defects that shipped, at the field-name
level rather than at the function level, because that is how they occurred: nobody
deleted a check, somebody named one spelling of a field the ledger writes under two. A
function-level mutation would prove the selftest notices a missing function, which was
never in doubt. A field-name mutation proves it notices a WRONG one.

The rest defend the properties that make the feed trustworthy rather than merely
non-empty: that a worktree is not a repository, that an undated row cannot answer a
windowed question, and that fingerprint dedupe still collapses the same fact at two
timestamps. That last one is guarded in the negative: a well-meaning "add ts to the key"
fix would make every collision disappear and delete 160 intended collapses, so the test
asserts the collapses still happen.

NOTE ON ARGV. Every other spec in this directory uses ARGV = ["selftest"] positionally.
This target uses argparse with --selftest, and a positional would make argparse exit 2.
mutate.py treats a non-green baseline as an ABORT, so the run would report nothing rather
than reporting wrongly, but the spec would still prove nothing. The flag form is correct
here and the difference is deliberate.
"""

TARGET = "tools/telemetry/collect.py"
ARGV = ["--selftest"]

MUTATIONS = [
    # ---- the two defects that actually shipped, at the field-name level ----
    ("the lessons extractor forgets the older `date` and `incident` spellings",
     "the exact defect. lessons.jsonl carries `class` on 20 of 43 rows and `ts` on 25, "
     "so 22 lessons published as an id, a colon, and nothing. The rows were carried, "
     "counted by the yield assertion, and said nothing to the agent that read them",
     'first_of(r, "class", "lesson", "incident")',
     'first_of(r, "class")'),

    ("the claims extractor forgets `note` and `proposal_id`",
     "the same defect in the other ledger and it is worse there: claims.jsonl carries "
     "`scope` on 7 of 22 rows, so 30 claims published as 'lane B claimed:' with nothing "
     "after the colon. A claim with no scope is the one row another lane must read",
     'first_of(r, "scope", "note")',
     'first_of(r, "scope")'),

    ("a lessons row dated with `date` loses its timestamp",
     "an undated row used to pass every --since window forever, so the same blank rows "
     "appeared in all 12 published posts. They were not recent, they were permanent "
     "residents, and nothing in the output distinguished the two",
     'ts=_iso(first_of(r, "ts", "date"))',
     'ts=_iso(first_of(r, "ts"))'),

    # ---- the worktree rule, both directions ----
    ("a .git pointer file is read as a real repository",
     "212 of 516 notable events came from .wt-rules-sync, a worktree of claude-setup "
     "whose tracked ledgers are checked out twice. fingerprint() includes `repo` on "
     "purpose, because the same lesson in two repos is two facts, so no dedupe "
     "downstream is allowed to collapse them. The duplication is unfixable after this "
     "point",
     "    return dotgit.is_file()",
     "    return False"),

    ("every repository is treated as a worktree",
     "the opposite failure and the quieter one. Zero repos are swept, the collector "
     "reports 0 events, and 0 events from a collector looks exactly like a quiet period. "
     "This file's own docstring is about that ambiguity",
     "    return dotgit.is_file()",
     "    return True"),

    ("a skipped worktree is skipped silently",
     "a sweep that drops a tree with no trace is indistinguishable from a tree that went "
     "quiet. The whole reason --audit exists is that a silent omission reads as coverage",
     "            if is_worktree(child):\n                if skipped is not None:\n"
     "                    skipped.append(child.name)",
     "            if is_worktree(child):\n                if skipped is not None:\n"
     "                    pass"),

    # ---- the emptiness oracle itself ----
    ("the empty-subject DETECTOR stops detecting",
     "the check that would have caught the shipped defect. Without it the selftest is "
     "back to counting rows it never reads, which is the state that published 52 blanks "
     "over 12 posts while printing VERDICT ok.\n\n"
     "     Aimed at the detector rather than at the `if blank:` report beside it, and "
     "the reason is worth recording. Mutating the REPORT survived, and it is uncatchable "
     "by construction: the extractor fix emptied the corpus of blank rows, so a branch "
     "guarded on `if blank:` never executes and disabling it changes no observable "
     "behaviour. No test against a clean corpus can distinguish a report that would fire "
     "from one that cannot. The planted control in selftest() exists for exactly this "
     "reason and it reaches the detector, so the detector is where the mutation belongs.",
     "        if not body.strip():",
     "        if False:"),

    ("first_of accepts a whitespace-only field as a value",
     "a ledger that writes \"ts\": \"   \" is saying it does not know. Reading the "
     "placeholder as data means the populated fallback beside it is never consulted, "
     "which restores the blank rows through a different door. Aimed at the `if s:` guard "
     "rather than at the `not in (None, \"\")` test beside it, because those two overlap "
     "and breaking only the first is a no-op that would report as a survivor while "
     "proving nothing about the oracle",
     "            if s:\n                return s",
     "            if True:\n                return s"),

    # ---- the window ----
    ("an undated row passes every window again",
     "the fourth defect, and the one that made the other three permanent. A row with no "
     "timestamp cannot answer 'what happened in the last 24 hours', and letting it "
     "through means the feed's oldest unreadable rows are also its most frequent",
     "                if since:\n                    if not ev[\"ts\"]:\n"
     "                        undated_dropped += 1\n                        continue",
     "                if since and ev[\"ts\"]:\n                    if False:\n"
     "                        undated_dropped += 1\n                        continue"),

    # ---- attribution, which the feed's cross-repo claim rests on ----
    ("a row is attributed to the file it sits in rather than the repo it is about",
     "every hook writes to $CLAUDE_OS_DIR, so a session in new-recruit lands its rows in "
     "claude-setup's ledgers. Attributing by file location labels all of them "
     "claude-setup, and the cross-repo view collapses to one name while looking complete",
     '    for field in ("repo", "project", "project_path", "cwd"):',
     "    for field in ():"),
]
