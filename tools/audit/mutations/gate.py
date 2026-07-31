"""Mutations for tools/gate/gate.py.

gate.py is the file with the strongest claim in this estate and, until
2026-07-27, the least evidence for it. It decides whether anything may be called
done, and it had no mutation spec, so the sentence in its own header, "a domain
counts as covered only when a command exits zero", was itself uncovered.

Its module docstring states the rule this spec defends:

    "There is no state in which the gate passes because nobody got round to
     configuring a check, because that is exactly the state the setup was
     already in."

and, on waivers:

    "An expired waiver is a failure, not a skip, because a permanent waiver is
     just a disabled check with better manners."

Each mutation below turns one of those sentences back into a lie. Everything
here targets a guard the selftest already exercises, so a survivor means the
selftest is decorative rather than that the mutation is uninteresting.
"""

TARGET = "tools/gate/gate.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- waiver expiry --------------------------------------------------
    ("an expired waiver stops being expired",
     "the exact 'disabled check with better manners' the docstring warns about: "
     "every waiver becomes permanent and no domain ever comes back",
     'return datetime.date.fromisoformat(until) < datetime.date.today()',
     'return False'),

    ("an unparseable until-date is treated as live rather than expired",
     "fail-open on a malformed date makes `until: soon` a permanent waiver, so "
     "the cheapest way to disable a domain forever is to typo the date",
     '    except Exception:\n        return True',
     '    except Exception:\n        return False'),

    ("a waiver expiring today reads as already expired",
     "`until` is inclusive, so the last day is a working day. Making the "
     "comparison <= fails a project on the morning of the deadline, which is "
     "exactly when someone is depending on the waiver they wrote",
     'return datetime.date.fromisoformat(until) < datetime.date.today()',
     'return datetime.date.fromisoformat(until) <= datetime.date.today()'),

    ("a far-future date is treated as expired",
     "inverting the comparison makes every live waiver read as expired, which "
     "fails a correct project and is how a gate stops being run at all",
     'return datetime.date.fromisoformat(until) < datetime.date.today()',
     'return datetime.date.fromisoformat(until) > datetime.date.today()'),
]

# Two mutations were removed on 2026-07-27 after they SURVIVED for the wrong
# reason. Both edited a message string rather than a branch:
#
#   "no test script found; a project with no tests cannot pass this gate" -> shorter text
#   "a leftover artifact is refreshed, not trusted, got {}"               -> reworded
#
# Neither changes behaviour, so neither could ever fail a selftest, and recording
# them as UNGUARDED would have blamed gate.py for a defect in this file. A
# mutation that cannot change an outcome is not evidence of a missing check; it is
# a badly written mutation. Kept here as a note because the distinction is easy to
# lose and expensive to relearn.
