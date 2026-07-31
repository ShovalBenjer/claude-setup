"""Mutations for tools/docmap/docmap.py.

docmap became a REQUIRED gate domain on 2026-07-31, six days after it was written. For
those six days it ran clean on every invocation and nothing called it, which is the same
shape as a hook that cannot fire: indistinguishable from working right up until someone
checks. Declaring the domain caught 11 undeclared documents on its first enforced run.

A domain is only as good as its oracle, and an oracle is only as good as the proof it can
fail. These re-break the guarantees a reader of DOCMAP.md depends on: that a status is
DERIVED rather than assumed, that the residue registry is actually consulted, that the
generated map is compared against what the documents imply, and that the undeclared count
is real.

The first version of this spec is worth recording because the runner rejected it. Three of
its five patterns matched nothing, because they were written against function names I
guessed (`load_registry`, `tracked_markdown`, `check`) rather than names I read
(`read_registry`, `tracked_docs`, `evaluate`). A mutation whose pattern does not match is
reported UNGUARDED and proves nothing, which is the same defect class the tool exists to
catch, one level up. Every string below was verified to appear exactly once before this
file was written.
"""

TARGET = "tools/docmap/docmap.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- status derivation, the thing the domain exists for ---------------
    ("an undeclared document is defaulted to a status instead of reported",
     "the single guarantee the domain rests on. If a document with no derivable status "
     "reads as fine, the map claims coverage it does not have, and the 11 caught on the "
     "first enforced run would have stayed invisible for another six days",
     'def status_for(',
     'def status_for_unused('),

    ("the residue registry is never read",
     "docs/doc-status.txt holds the statuses that cannot be derived from a document or "
     "its class. Ignoring it turns 44 declared documents into undeclared ones",
     'def read_registry(',
     'def read_registry_unused('),

    # ---- the inline Status form, a defect that already happened once ------
    ("the inline `Status: X` form stops matching",
     "15 of 17 ADRs use the inline form rather than a line of its own. This exact defect "
     "already occurred via a literal 0x08 byte written into the raw string, and reported "
     "6 ADRs as UNDECLARED while every one of them declared a status",
     'STATUS_INLINE = re.compile(r"\\bstatus',
     'STATUS_INLINE = re.compile(r"\\bNEVERMATCHES'),

    ("the multiline Status line stops matching",
     "the other form. Between them these two regexes are the whole derivation path for a "
     "document that declares its own state",
     'STATUS_LINE = re.compile(r"^[-*\\s]*\\**status',
     'STATUS_LINE = re.compile(r"^[-*\\s]*\\**NEVERMATCHES'),

    # ---- classification gates which rules apply --------------------------
    ("every document is classified the same way",
     "class determines which statuses are derivable at all, so collapsing it makes the "
     "ALWAYS table apply to documents it was never written for",
     'def classify(',
     'def classify_unused('),

    # ---- the empty-scan class --------------------------------------------
    ("the document scan returns nothing",
     "an empty scan and a fully-declared corpus print the same success line unless the "
     "count is asserted. This is the check-that-examined-nothing class, already found in "
     "this repository in a gate fingerprint, a test cleanup and a deployed hook",
     'def tracked_docs(',
     'def tracked_docs_unused('),

    # ---- render and parse round trip -------------------------------------
    ("the generated map is no longer compared against the documents",
     "evaluate() is what makes DOCMAP.md a projection rather than a wish. Without it a "
     "hand edit stops reading as drift",
     'def evaluate(',
     'def evaluate_unused('),

    ("problems are computed but never surfaced",
     "the function that turns state into the list a caller acts on. If it returns nothing "
     "the check exits zero on a broken corpus, which is the worst possible direction",
     'def problems(',
     'def problems_unused('),
]
