"""Mutations for tools/timetravel/snapshot.py.

snapshot.py answers one kind of question: what did this ledger say at that
moment. Every guarantee it makes is therefore about ORDERING and about CONTENT
ADDRESSING, and both classes fail silently. A reconstruction that returns the
wrong version returns a plausible file, not an error; a blob store that stops
noticing corruption prints the same VERDICT line it printed when it was working.
There is no user-visible symptom for either, which is why the selftest is the
only thing standing between this tool and confident wrong answers, and why the
selftest had no mutation control until now.

Three of the guarantees below were not designed in, they were MEASURED into
existence on this tool's first real run on 2026-07-30, and each one is a
regression somebody has already lived through once:

  - two `snap` calls in one shell pipeline both stamped 20:57:38Z, so resolve_at
    could not order them and `log` could not say which content came first. That
    is why now_utc() carries milliseconds and why next_ts() exists at all.
  - a ts copied out of `log` into `at` raised ValueError, which makes the two
    verbs unusable together and is precisely the workflow the tool exists for.
  - a prefix match that forgot to anchor pulled 171 paths and 7.4 MB of docs
    into a store meant for ledgers.

Reverting a measured fix is the cheapest regression there is: it looks like
simplification, and the comment explaining why it was wrong stays in the file
directly above the code that no longer does it.

The last mutation is aimed somewhere the selftest did not previously reach.
`verify` is the only check that a blob still hashes to its own name, and content
addressing is this tool's entire dedupe and integrity claim; a corrupt blob that
verify no longer reports is a wrong answer to `at --content` with a hash printed
beside it. If that mutation survives, the survivor is the finding.
"""

TARGET = "engine/tools/timetravel/snapshot.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- ordering is the product ----------------------------------------
    ("timestamps go back to second resolution",
     "the measured 2026-07-30 defect, restored: two snapshots in the same second "
     "are unorderable, so resolve_at picks arbitrarily between two different "
     "contents and `log` cannot say which came first. A tool whose whole job is "
     "ordering cannot have a resolution coarser than the rate it is called at",
     '    return datetime.datetime.now(datetime.timezone.utc).isoformat(\n'
     '        timespec="milliseconds").replace("+00:00", "Z")',
     '    return datetime.datetime.now(datetime.timezone.utc).isoformat(\n'
     '        timespec="seconds").replace("+00:00", "Z")'),

    ("the monotonicity guard is removed",
     "a backwards clock, a manual clock change, or two writers in one millisecond "
     "then write a row that sorts BEFORE the row already on disk. The manifest is "
     "append-only, so nothing later can repair it: every `at` answer that crosses "
     "that row is wrong from then on",
     '    if candidate > last:\n        return candidate',
     '    if True:\n        return candidate'),

    ("the collision nudge moves the stamp by zero milliseconds",
     "the guard still fires, still looks like it did something, and produces a "
     "duplicate stamp anyway. This is the version that survives a code review of "
     "the previous mutation",
     '    dt += datetime.timedelta(milliseconds=1)',
     '    dt += datetime.timedelta(milliseconds=0)'),

    ("a bare date means the END of that day",
     "`at 2026-07-30` would answer with bytes written 23 hours later. Every "
     "reconstruction from a bare date is then off by up to a day, in the direction "
     "that shows the operator content that did not exist when they were asking",
     '                      ("%Y-%m-%d", "T00:00:00")):',
     '                      ("%Y-%m-%d", "T23:59:59")):'),

    ("an unparseable instant silently means now",
     "a typo in a date becomes an answer about the present, which is the one "
     "moment the operator can already see. Returning current state in response to "
     "a question about the past is the worst possible failure for this tool "
     "because the output is well-formed and confident",
     '    raise ValueError("cannot read {!r} as an instant; try 2026-07-30T12:00".format(text))',
     '    return now_utc()'),

    ("resolve_at returns the NEAREST snapshot instead of the last at-or-before",
     "the docstring's own warning: a later snapshot is evidence about a later "
     "moment. Nearest-neighbour passes a naive test, and answers questions about "
     "any moment before the first snapshot with bytes that did not exist yet",
     '        if ts and ts <= when and (best is None or ts > best["ts"]):',
     '        if ts and (best is None or ts > best["ts"]):'),

    ("an unchanged file counts as a new version on every run",
     "an hourly snapshotter would report 24 versions a day of a file nobody "
     "touched. The log stops distinguishing a change from a confirmation, which is "
     "the only distinction it makes",
     '        if out and out[-1].get("digest") == digest:',
     '        if False:'),

    ("a deleted path is logged as unchanged rather than DELETED",
     "a ledger that vanished reads as a ledger that stayed the same. The one event "
     "worth alerting on becomes the absence of an event",
     '            if out and out[-1].get("digest") is not None:',
     '            if False:'),

    ("the window's lower endpoint becomes the snapshot in effect at its UPPER end",
     "a change made between `lo` and the next run then falls out of the window "
     "that contains it, so `changed` reports nothing moved during exactly the "
     "period somebody is investigating because something moved",
     '    a = resolve_at(rows, lo)',
     '    a = resolve_at(rows, hi)'),

    # ---- content addressing ---------------------------------------------
    ("a corrupt blob stops being reported by verify",
     "content addressing is this tool's integrity claim: a blob is trusted "
     "BECAUSE its name is its hash. Drop the comparison and `at --content` prints "
     "whatever the file now holds with a digest beside it that no longer describes "
     "it, while verify keeps printing 0 corrupt",
     '        if sha256_bytes(open(bp, "rb").read()) != digest:\n            corrupt.append(digest)',
     '        if False:\n            corrupt.append(digest)'),
]
