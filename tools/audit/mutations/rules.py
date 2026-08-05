"""Mutations for tools/audit/rules_sync.py.

This file guards the rules that are loaded into every session in every project,
and it is the newest oracle in the estate: it landed on 2026-08-04 after a commit
framed as a "sync" ran from a degraded live tree into the good repo copy and took
986 lines out of 17 rule files. It arrived with a selftest and no mutation spec,
which by this repo's own four-layer standard leaves the last layer missing, the one
that proves the selftest can go red at all.

It also arrived with a defect of its own, and half of what is re-broken below exists
because of that defect rather than in spite of it. The first version returned FAIL
when `~/.claude/rules` was absent, so it turned the `rules` gate domain red on every
GitHub Actions run: a runner has no deployed harness and never will. That is
L-2026-07-31-g, a host-shaped default answering the wrong question on the other host,
logged by this repository on 2026-07-31 and shipped again on 2026-08-05.

The repair splits the file's two checks by what each one needs rather than by which
machine it is on. DRIFT needs a live tree and is reported as not run without one.
SHRINK needs only the payload and git history, so it runs everywhere and is the check
that would have caught the incident. The mutations below attack that split from both
sides, because it has two opposite failure modes and only one of them is loud:

  Too strict, and CI is red for a correct condition. That is the bug being fixed, and
  it announces itself on every run, which is why it survived only one day.

  Too lax, and CI is green because it stopped checking. An absent live tree that
  silently returns 0, or a shrink loop that quietly stops running when there is no
  live tree to intersect with, both produce a passing `rules` domain on a runner that
  verified nothing. Nobody would notice, because the output of a check that stopped
  looking and a check that looked and found nothing is the same word.

So the mutation that matters most here is not the removal of a rule. It is the
removal of the SENTENCE that says which rule did not run. A pass whose reduced scope
is invisible is worse than a fail, and the selftest asserts on the text for exactly
that reason.
"""

TARGET = "tools/audit/rules_sync.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- the incident this file was written for -------------------------
    ("the shrink floor drops below the ratio the incident produced",
     "boundary-contracts.md sat at 488 bytes of 5557, a ratio of 0.088. Any floor "
     "at or under that number reads the destroyed rule as healthy, so 2bb97a8 "
     "lands again and the one signal that survives when the content is gone stops "
     "being read. The threshold is set from the incident, not from taste, and the "
     "selftest checks it as arithmetic so it cannot drift quietly",
     "SHRINK_FLOOR = 0.60",
     "SHRINK_FLOOR = 0.05"),

    ("the shrink floor rises past the smallest legitimate trim",
     "the same commit trimmed no-emojis, no-mocks, task-verification and "
     "tdd-enforcement while keeping them above 0.9 of their maximum. A floor above "
     "that flags healthy rules, and an oracle that cries every run is one that gets "
     "waived and then deleted",
     "SHRINK_FLOOR = 0.60",
     "SHRINK_FLOOR = 0.95"),

    # ---- the host-shaped defect, in both directions ---------------------
    ("an absent live tree fails again, which is the defect this spec documents",
     "the original behaviour. Every CI run turns the rules domain red for a "
     "condition that is correct on a runner, and a domain that is permanently red "
     "for a reason nobody can act on gets waived, which removes the guard entirely. "
     "L-2026-07-31-g, shipped twice",
     "    live_present = LIVE.is_dir()",
     "    live_present = False if not LIVE.is_dir() else True\n"
     "    if not live_present:\n"
     "        raise SystemExit(1)"),

    ("the line naming the skipped check stops printing",
     "the pass survives and its reduced scope becomes invisible. `rules PASS` on a "
     "runner would then mean 'drift was never compared' while reading identically "
     "to 'drift was compared and agreed'. This is the quiet half of the failure and "
     "the reason the selftest asserts on the text rather than only on the exit code",
     '    if not live_present:\n        print("NOT RUN drift: no live rules directory at " + res["live_dir"] +',
     '    if not live_present and False:\n        print("NOT RUN drift: no live rules directory at " + res["live_dir"] +'),

    ("shrink goes back to iterating the intersection of payload and live",
     "the subtle one, and the shape the first version had. With no live tree the "
     "intersection is empty, so the loop body never runs, `shrunk` is always empty, "
     "and CI reports clean because it examined nothing. The check that would have "
     "caught the incident is precisely the check that stops running on the only host "
     "where nobody is watching",
     "    for name in sorted(payload_files):",
     "    for name in sorted(set(payload_files) & set(live_files)):"),

    ("an absent live tree reports every payload rule as undeployed",
     "22 FAIL lines on every CI run saying rules are not deployed to a machine that "
     "was never going to deploy them. Technically true, entirely useless, and it "
     "buries any real finding underneath itself. The empty-list branch exists to "
     "keep the report about defects rather than about the runner",
     "    only_payload = sorted(set(payload_files) - set(live_files)) if live_present else []",
     "    only_payload = sorted(set(payload_files) - set(live_files))"),

    # ---- the drift half, which is the check skills_sync already models ---
    ("a rule that differs between repo and live stops being reported",
     "an undeployed edit and a live-only edit both become silent. The repo copy and "
     "the copy every session actually loads drift apart with nothing measuring the "
     "gap, which is the state the estate was already in for rules before this file "
     "existed",
     '    for d in res["differing"]:',
     '    for d in []:'),

    ("a rule that is live but not tracked stops being reported",
     "it vanishes on a fresh machine, and the loss is invisible until somebody "
     "reinstalls and wonders why a rule stopped binding. Untracked-live is the "
     "direction that loses work permanently, unlike undeployed, which only delays it",
     '    for name in res["only_live"]:',
     '    for name in []:'),

    ("a truncated rule is counted but not reported",
     "the count line still says how many problems there are while the reader is "
     "never told which rule lost itself or what it shrank from. A number with no "
     "name attached cannot be acted on, and this is the one finding whose whole "
     "value is the file name",
     '    for s in res["shrunk"]:',
     '    for s in []:'),

    ("an empty live directory starts passing like an absent one",
     "the two are different facts and the difference is the entire point. Absent "
     "means not deployed here. Empty means deployed and then destroyed, which is "
     "the incident. Collapsing them makes the destroyed case report as the benign "
     "one",
     "    only_payload = sorted(set(payload_files) - set(live_files)) if live_present else []",
     "    only_payload = []"),
]
