"""Mutations for tools/refute/refute.py.

The refutation engine is the file with the least excuse for unfalsified checks,
and it shipped two exit-0-while-checking-nothing defects of its own, both found on
2026-07-25 while registering unrelated claims:

  - `--only C-019,C-020` matched none of 20 claims, printed the empty-ledger
    sentence, and exited 0.
  - a BROKEN verifier (timeout, missing command, unknown shell) was printed as
    "not a pass" and then left out of the exit code, so breaking a command was the
    cheapest way to make this tool quiet.

Every mutation below re-breaks one of those, or breaks a verdict rule that would
otherwise let a claim pass without evidence.
"""

TARGET = "tools/refute/refute.py"
ARGV = ["selftest"]

MUTATIONS = [
    ("a filter that matched nothing exits 0 again",
     "the original defect: a caller asking for specific claims silently gets none",
     '        return 2\n    if not claims:',
     '        return 0\n    if not claims:'),

    ("matched-nothing falls through to the empty-ledger branch",
     "two different facts print the same sentence, as they used to",
     'if not claims and total:',
     'if False:'),

    ("the matched-nothing message stops naming the count and the match rule",
     "the caller is told nothing was checked but not how to fix the filter",
     '        print("--only is a SUBSTRING match on id, claim text, or tag; it is not a "\n              "list. Try one id, or a tag.", file=sys.stderr)',
     '        pass'),

    ("the filter stops filtering",
     "--only one-id would check the whole ledger, so a targeted run is a lie",
     '        claims = [\n            c for c in claims\n            if q in str(c.get("id", "")).lower()\n            or q in str(c.get("claim", "")).lower()\n            or q in str(c.get("tag", "")).lower()\n        ]',
     '        claims = list(claims)'),

    ("broken verifiers stop counting toward the exit code",
     "an unrunnable command reads as success, rewarding breakage over repair",
     '    countable = refuted if getattr(a, "allow_broken", False) else refuted + broken\n    return min(countable, 125)',
     '    countable = refuted\n    return min(countable, 125)'),

    ("the exit code is hardcoded to success",
     "the table still prints REFUTED and every caller sees green",
     '    return min(countable, 125)',
     '    return 0'),

    ("a claim with no verify command is treated as holding",
     "a wish with no checker becomes indistinguishable from a verified claim",
     '        return BROKEN, -1, "no verify command on this claim"',
     '        return HELD, 0, "no verify command on this claim"'),

    ("a timed-out verifier is treated as holding",
     "the slowest way to pass is to hang, which is also the easiest",
     '        return BROKEN, -1, f"verifier timed out after {timeout}s"',
     '        return HELD, 0, f"verifier timed out after {timeout}s"'),

    ("an unknown shell is treated as holding",
     "a typo in the shell field silently converts a claim into a pass",
     '        return BROKEN, -1, f"unknown shell {shell!r}"',
     '        return HELD, 0, f"unknown shell {shell!r}"'),

    ("expect=fail stops inverting",
     "every absence claim flips verdict, so the wrong half of the ledger passes",
     '    ok = (p.returncode == 0) if expect == "pass" else (p.returncode != 0)',
     '    ok = (p.returncode == 0)'),

    ("--allow-broken stops being honoured",
     "the named hatch is a no-op, so a caller who needs it edits the file instead",
     '            if getattr(a, "allow_broken", False):\n                print("--allow-broken: not counting them, as asked.")',
     '            pass'),

    ("an unparseable ledger line aborts the whole run",
     "one torn append takes every other claim down with it",
     '        try:\n            rec = json.loads(line)\n        except json.JSONDecodeError as e:\n            print(f"claims-verify.jsonl:{n}: unparseable, skipped ({e})", file=sys.stderr)\n            continue',
     '        rec = json.loads(line)'),
]
