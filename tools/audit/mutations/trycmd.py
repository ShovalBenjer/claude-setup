"""Mutations for tools/trycmd/trycmd.py.

trycmd.py exists because five selftests in this repo assert on internal
functions and none of them executes its own command line. It closes that gap by
comparing real process output against a snapshot. Which makes it the component
with the sharpest version of the defect class this whole audit tool was built
for, and its own author flagged it as the strongest objection to the design:

  A SNAPSHOT SUITE THAT STOPS COMPARING STILL PRINTS `0 failed`.

Nothing about a vacuous pass is visible from the outside. The suite runs, the
commands really execute, the step count is unchanged, the exit code is zero, and
the only difference is that no assertion is being made. `overwrite` makes it
worse rather than better: it is the sanctioned way to replace every expectation
with whatever the code currently does, which is why upstream and this port both
keep it behind a mode a human has to type. The first two mutations below are
that objection made executable, aimed straight at check_step.

The rest defend the two things a snapshot runner is: a grammar and a matcher.

  GRAMMAR. `? failed` must not mean success, an absent `? ` line must mean exit
  zero rather than any-nonzero, a `> ` continuation must reach the argv, and
  `ignore` must actually skip. Each of those quietly widens what the suite
  accepts, and a widened expectation is indistinguishable from a passing test.

  MATCHER. `[..]` and `...` are load-bearing here for a stated reason: argparse
  wraps `--help` to a terminal width this repo does not control. A matcher that
  says yes to everything turns every expected block into decoration; a matcher
  that stops eliding turns a working suite red for a reason nobody can act on.
  Both are mutated, because over-matching and under-matching are different
  failures and only one of them gets noticed.

The stderr mutation belongs to the same family as the first two. This port
deliberately merges stderr into stdout, following upstream, because the literate
format has no way to express two streams. Dropping stderr silently means every
argparse usage message, every traceback, and every error path this suite exists
to pin is compared against an empty string.

TWO NOTES FROM THE FIRST RUN, 2026-07-31.

Three mutations survived. Two were real: check_step, which is where the whole
comparison happens, was asserted on by nothing at all, so the vacuous pass this
file's own author named as the strongest objection to the design was live and
unguarded. trycmd.py's selftest now calls check_step directly on a match, an
output mismatch and a wrong exit code, and both mutations are caught by name.

The third survivor was a badly written mutation, not a missing check, and it is
recorded here because the distinction is easy to lose. It flipped the trailing
`return False` of line_matches to `return True`. That statement is UNREACHABLE:
str.split always yields at least one section, and the final iteration of the loop
always returns through the `idx + 1 == len(sections)` arm. A mutation to dead
code can never change an outcome, so a survival there says nothing about the
selftest. It was replaced with the reachable form of the same regression,
short-circuiting the equality arm to True, which the matcher checks do catch.
"""

TARGET = "tools/trycmd/trycmd.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- the vacuous pass -----------------------------------------------
    ("the output comparison stops happening and every step reports green",
     "the objection the author of this file wrote down: a snapshot suite that "
     "stops comparing prints `0 failed` and looks exactly like one that passes. "
     "Steps still execute, so timing, exit codes and step counts are all "
     "unchanged; the only thing missing is the assertion",
     '    if normalized != step.expected:',
     '    if False:'),

    ("the exit-code comparison stops happening",
     "half of what a CLI contract is. A command that started exiting 1 on the "
     "happy path would keep passing as long as its text was unchanged, which is "
     "the usual shape of a broken argparse migration",
     '    elif code != step.status:',
     '    elif False:'),

    ("stderr is dropped instead of merged into the compared stream",
     "every error path in this suite is an argparse usage message or a traceback, "
     "and all of them arrive on stderr. Dropping it compares them against an empty "
     "string, so the error-handling cases pass by having nothing to say",
     '    merged = (proc.stdout or "") + (proc.stderr or "")',
     '    merged = (proc.stdout or "")'),

    # ---- the matcher ----------------------------------------------------
    ("the matcher says yes to every line",
     "every expected block becomes decoration. This is the vacuous pass again, one "
     "layer down, and it is reached by a single misplaced return",
     '    if actual == expected:\n        return True',
     '    if True:\n        return True'),

    ("the literal prefix before a wildcard stops being required",
     "`[..]` would match any line rather than any run of characters INSIDE a line "
     "with fixed text around it. The fixed text is the entire assertion; the "
     "wildcard is the part deliberately not asserted",
     '        if not actual.startswith(section):',
     '        if False:'),

    ("the wildcard token changes, so `[..]` is matched literally",
     "every existing case file still parses and still runs, and every line "
     "containing a wildcard now demands those four characters verbatim. A suite "
     "that fails for a reason nobody can act on gets deleted, not fixed",
     '    sections = expected.split("[..]")',
     '    sections = expected.split("[...]")'),

    ("a bare `...` line stops eliding",
     "the elision exists because argparse wraps --help to a terminal width this "
     "repo does not control. Without it a passing suite turns red on a machine "
     "with a different COLUMNS, which is how a check stops being run",
     '        if exp.strip() == "..." :',
     '        if False:'),

    # ---- the grammar ----------------------------------------------------
    ("`? failed` starts meaning success",
     "the declaration that a command MUST fail becomes a declaration that it must "
     "succeed. Every negative test in the suite inverts while continuing to pass, "
     "which is worse than deleting them",
     '    if raw == "failed":\n        return None',
     '    if raw == "failed":\n        return 0'),

    ("a step with no `? ` line expects any nonzero exit instead of success",
     "the default status governs almost every step in a suite, since only failing "
     "cases carry a `? ` line. Flipping it means the happy path is only asserted "
     "to be broken",
     '            status: int | None = 0',
     '            status: int | None = None'),

    ("a `> ` continuation line is dropped instead of extending argv",
     "the command that runs is then a prefix of the command that was written down, "
     "and the output it is compared against belongs to the full one. Every "
     "multi-line invocation silently tests something shorter",
     '            while i < n and lines[i].startswith("> "):',
     '            while False:'),

    ("the `ignore` attribute stops being honoured",
     "a block marked ignore is one somebody deliberately excluded, usually because "
     "it is environment-dependent. Running it anyway makes the suite fail for a "
     "documented reason, which trains the reader to ignore the whole tool",
     '        if lang not in FENCE_LANGS or "ignore" in attrs:',
     '        if lang not in FENCE_LANGS:'),
]
