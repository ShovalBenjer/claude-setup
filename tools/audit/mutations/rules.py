"""Mutations for tools/audit/rules_sync.py.

This file guards the rules loaded into every session in every project. It landed on
2026-08-04 after a commit framed as a "sync" ran from a degraded live tree into the
good repo copy and took 986 lines out of 17 rule files, and it was corrected on
2026-08-05 after it turned the Ship gate red on every GitHub runner by asking whether
the repo matched a deployment that cannot exist there.

Both of those are behaviour changes to an oracle, and neither arrived with the layer
this repository requires last: a mutation that proves the selftest can go red at all.
By the contract-oracle-selftest-mutation standard the file has been running with its
fourth layer missing since the day it was written, through one incident and one
correction, which is precisely the window where an oracle is most likely to have been
weakened rather than strengthened.

WHAT THIS SPEC IS AIMED AT, which is not the loud failure.

The correction has two opposite failure modes and only one announces itself:

  Too strict. FAIL with no live tree, red on every runner, waived within days. That
  was the bug, it was visible on every single run, and it survived exactly one day.

  Too lax. A pass on a runner that verified nothing. The drift half is legitimately
  skipped there, so the SHRINK half is the entire remaining assertion, and if it
  quietly stops running the output is unchanged: "rules clean (shrink only)" is
  printed by the clean path whether the loop examined 22 rules or zero. Nobody would
  notice, because a check that stopped looking and a check that looked and found
  nothing say the same word.

That second mode is the one this spec exists for. `scan()` keeps the shrink loop alive
with no live tree by seeding `live_files` from `payload_files`, which reads like a
defensive convenience and is in fact load-bearing: delete it and the intersection the
loop iterates is empty. The selftest asserts the string "shrink" appears in the output,
and that string is in the clean message itself, so it holds either way.

The threshold is mutated in both directions for the same reason. Dropping it below the
ratio the incident produced re-admits the incident. Raising it past the smallest
legitimate trim in the same commit turns the oracle into one that fires on correct
input, and an oracle that cries every run is one that gets waived and then deleted.
Only the first of those was pinned.
"""

TARGET = "tools/audit/rules_sync.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- the incident, from both sides of the threshold ------------------
    ("the shrink floor drops below the ratio the incident produced",
     "boundary-contracts.md sat at 488 bytes of 5557, a ratio of 0.088. Any floor at "
     "or under that reads the destroyed rule as healthy, so 2bb97a8 lands again and "
     "the one signal that survives when the content is gone stops being read",
     "SHRINK_FLOOR = 0.60",
     "SHRINK_FLOOR = 0.05"),

    ("the shrink floor rises past the smallest legitimate trim",
     "the same commit trimmed no-emojis, no-mocks, task-verification and "
     "tdd-enforcement while keeping them above 0.9 of their maximum. A floor above "
     "that reports healthy rules as damage every run, and the fix a reader reaches "
     "for is a waiver on the domain rather than a correction to the number",
     "SHRINK_FLOOR = 0.60",
     "SHRINK_FLOOR = 0.95"),

    # ---- the quiet half of the CI correction -----------------------------
    ("the shrink loop stops running when there is no live tree",
     "the vacuous pass, and the reason this spec was written. With the seeding line "
     "gone the intersection is empty on a runner, so the loop body never executes, "
     "`shrunk` is always empty and the domain reports clean having examined nothing. "
     "The output is byte-identical to a real pass, and the runner is the one host "
     "where no human is reading",
     "    if not LIVE.is_dir():\n        live_files = dict(payload_files)",
     "    if not LIVE.is_dir():\n        pass"),

    ("an absent live tree fails again, which is the bug this file was corrected for",
     "the original behaviour. Every CI run turns the rules domain red for a condition "
     "that is correct on a runner, and a domain permanently red for a reason nobody "
     "can act on gets waived, which removes the guard entirely. L-2026-07-31-g",
     '    live_present = Path(res["live_dir"]).is_dir()',
     '    live_present = Path(res["live_dir"]).is_dir()\n'
     '    if not live_present:\n'
     '        print("FAIL live rules directory does not exist: " + res["live_dir"])\n'
     '        return 1'),

    ("the line naming the skipped half stops printing",
     "the pass survives and its reduced scope becomes invisible. `rules PASS` on a "
     "runner would then mean 'drift was never compared' while reading identically to "
     "'drift was compared and agreed'. The skip has to be stated or the domain is "
     "quietly checking half of what its name implies",
     '        print("SKIP drift: no live rules tree at {} (expected on CI). The deployment "',
     '        print("" "no live rules tree at {} (expected on CI). The deployment "'),

    # ---- the drift half, which is what skills_sync already models --------
    ("a rule that differs between repo and live stops being reported",
     "an undeployed edit and a live-only edit both go silent. The repo copy and the "
     "copy every session actually loads drift apart with nothing measuring the gap, "
     "which is the state the estate was in for rules before this file existed",
     "        for d in res[\"differing\"]:",
     "        for d in []:"),

    ("a rule that is live but not tracked stops being reported",
     "it vanishes on a fresh machine, and the loss is invisible until somebody "
     "reinstalls and wonders why a rule stopped binding. Untracked-live is the "
     "direction that loses work permanently, unlike undeployed, which only delays it",
     "        for name in res[\"only_live\"]:",
     "        for name in []:"),

    ("a rule in the repo but not deployed stops being reported",
     "every session is missing it and nothing says so. This is also the empty-live-"
     "directory case, which is a deployment that was destroyed rather than one that "
     "was never made, and it is the shape the 2bb97a8 damage would take if the sync "
     "had deleted files instead of truncating them",
     "        for name in res[\"only_payload\"]:",
     "        for name in []:"),

    ("a truncated rule is counted but never named",
     "the count line still says how many problems there are while the reader is never "
     "told which rule lost itself or what it shrank from. A number with no name "
     "attached cannot be acted on, and this is the one finding whose whole value is "
     "the file name",
     '    for s in res["shrunk"]:',
     '    for s in []:'),

    ("problems are counted and the command still exits zero",
     "every FAIL line above still prints and the gate reads exit 0, so the domain "
     "goes green while its own output describes the failure. Worse than silence, "
     "because the evidence is right there and the verdict contradicts it",
     "    if problems:\n        print(\"\\n{} problem(s) across {} rule(s)\".format(problems, res[\"counted\"]))\n        return 1",
     "    if problems:\n        print(\"\\n{} problem(s) across {} rule(s)\".format(problems, res[\"counted\"]))\n        return 0"),
]
