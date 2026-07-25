"""Mutations for tools/skilleval/run.py.

This tool was written in response to a repository that shipped 40 eval cases and
never executed one, so a decorative selftest here would be a joke told at its own
expense. Every grader below is broken one at a time and the selftest must go red
on each.

Two entries deserve their names read twice. "the tie downgrade becomes a
switch-off" exists because ties were made non-fatal AFTER the real tree produced
one, which is exactly the shape of weakening an oracle to get a green -- so the
distinction between a strict loss and a tie has to be provably load-bearing in
both directions. And "a run that graded nothing reports PASS" guards the defect
this tool shipped with for one run: 47 skills, 0 fixtures, VERDICT PASS.
"""

TARGET = "tools/skilleval/run.py"
ARGV = ["selftest"]

MUTATIONS = [
    # --- the score itself, which every other grader is built on ---------------
    ("anchor_score stops measuring overlap and returns a constant",
     "every prompt scores alike, so separation and collision both become noise",
     "    return len(pw & words(description)) / float(len(pw))",
     "    return 0.5"),

    ("anchor_score normalises by the description instead of the prompt",
     "a long description outscores a precise one on every prompt it partly covers",
     "    return len(pw & words(description)) / float(len(pw))",
     "    dw = words(description)\n    return len(pw & dw) / float(len(dw) or 1)"),

    # --- intra-skill separation ------------------------------------------------
    ("the separation check stops comparing the weakest trigger to the strongest skip",
     "a description that routes a skip prompt better than a trigger prompt passes",
     "        if weakest[0] <= strongest[0]:",
     "        if False:"),

    ("the separation check compares the STRONGEST trigger instead of the weakest",
     "one well-worded trigger case covers for every badly-routed one beside it",
     "        ts = sorted(((anchor_score(c[\"prompt\"], desc), c[\"prompt\"]) for c in trig))",
     "        ts = sorted(((anchor_score(c[\"prompt\"], desc), c[\"prompt\"]) for c in trig),\n"
     "                    reverse=True)"),

    ("a trigger prompt sharing no word at all with the description stops being reported",
     "the strongest single signal of an unroutable skill goes silent",
     "            if score == 0.0:",
     "            if False:"),

    # --- fixture integrity: the just-my-skills defect --------------------------
    ("a fixture with no skip case stops failing",
     "an all-positive suite cannot fail, so it measures nothing and still reports PASS",
     "    if not skip:",
     "    if False:"),

    ("a fixture with no trigger case stops failing",
     "the suite cannot show the skill is reachable at all",
     "    if not trig:",
     "    if False:"),

    ("malformed cases are dropped silently instead of reported",
     "a typo in `expect` removes a case from the suite and nothing says so",
     "    if bad:",
     "    if False:"),

    ("an unparseable expect value is accepted as a trigger",
     "the fixture's own vocabulary stops being a contract",
     "or c.get(\"expect\") not in (\"trigger\", \"skip\")]",
     "]"),

    # --- structure -------------------------------------------------------------
    ("a frontmatter name that disagrees with its directory stops failing",
     "the skill is invoked under a name that does not resolve",
     "    elif fm[\"name\"] != name:",
     "    elif False:"),

    ("an emoji in a description stops failing",
     "the repo's no-decorative-emoji rule loses its only mechanical enforcement",
     "    for hit in EMOJI_RX.findall(desc):",
     "    for hit in []:"),

    ("a missing description stops failing",
     "a skill with no routing surface at all reports clean",
     "    if not desc.strip():",
     "    if False:"),

    ("a folded block scalar stops being read as a description",
     "ship-gate and every `description: >-` skill get reported as having none, "
     "which is a false finding and those cost more trust than a missed one",
     "        if val in (\">\", \">-\", \">+\", \"|\", \"|-\", \"|+\"):",
     "        if False:"),

    # --- coverage accounting ---------------------------------------------------
    ("a skill with no fixture reports PASS instead of UNCOVERED",
     "42 ungraded skills would read as 42 graded ones",
     "        row[\"status\"] = FAIL if row[\"problems\"] else UNCOVERED",
     "        row[\"status\"] = PASS"),

    ("a run that graded nothing reports PASS",
     "the exact defect this tool shipped with for one run: 47 skills, 0 fixtures, green",
     "    if not passed:",
     "    if False:"),

    # --- cross-skill collision -------------------------------------------------
    ("the cross-skill check stops looking for a rival",
     "the only grader that can see one description subsuming another goes silent",
     "            if rivals and rivals[0][0] >= mine:",
     "            if False:"),

    ("the cross-skill check scores a skill against itself",
     "every prompt ties with its own owner, so every real collision is buried",
     "                             if n != r[\"skill\"]), reverse=True)",
     "                             ), reverse=True)"),

    ("a strict loss is recorded as a tie",
     "the fatal half of the collision check is downgraded to a warning",
     "                    \"strict\": rivals[0][0] > mine,",
     "                    \"strict\": False,"),

    ("the tie downgrade becomes a switch-off",
     "--strict-ties stops enforcing anything, so downgrading ties was just deleting them",
     "    if failed or lost or (tied and strict_ties):",
     "    if failed or lost:"),

    ("a strict loss stops failing the run",
     "the collision check reports and never blocks",
     "    if failed or lost or (tied and strict_ties):",
     "    if failed or (tied and strict_ties):"),

    ("a red skill stops failing the run",
     "every grader above still prints and the exit code says clean",
     "    if failed or lost or (tied and strict_ties):",
     "    if lost or (tied and strict_ties):"),

    # --- the fixture reader ----------------------------------------------------
    ("a fixture that fails to parse is treated as absent",
     "a broken JSON file downgrades the skill to UNCOVERED instead of reporting the error",
     "                return [{\"_error\": \"{}: {}\".format(type(exc).__name__, exc)}], name",
     "                return [], name"),
]
