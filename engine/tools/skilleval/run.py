# -*- coding: utf-8 -*-
"""Grade skill routing fixtures instead of just writing them.

Why this exists. `Master0fFate/just-my-skills` ships `evals.json` (12 cases) and
`trigger-evals.json` (28 cases) that look exactly like a test suite, and nothing
in that repository reads or grades either file. Forty written assertions, zero
executions. Measured here 2026-07-25: this tree has 47 skills, 47 SKILL.md files,
and zero eval fixtures at all. So the gap is symmetric, and ours is the cheaper
one to close -- they need a runner, we need fixtures, and a runner that grades
nothing is the same inert artifact wearing the other hat.

What this measures, stated honestly. Real skill selection is done by a model
reading descriptions, and this runner does not simulate that. It measures a
weaker, fully mechanical property of the description text:

    can this description lexically separate the prompts its own author says must
    route to it from the prompts the author says must not?

That is a lower bound, not a prediction. Passing does not prove the model will
route correctly. Failing does prove something concrete: the description shares
more vocabulary with a prompt that must be skipped than with one that must
trigger, so the model is being asked to route on cues the text does not carry.
Every score printed is reproducible from the two strings, with no model call, no
network, and no cost -- which is what lets this run in CI.

Vocabulary matches tools/gate/gate.py on purpose: PASS, FAIL, UNCOVERED. A skill
with no fixture is UNCOVERED and counted out loud, never silently skipped.

Usage:
    python tools/skilleval/run.py scan  [--root payload/dot-claude/skills] [--strict]
    python tools/skilleval/run.py selftest
"""
import argparse
import json
import os
import re
import sys
import tempfile

PASS = "PASS"
FAIL = "FAIL"
UNCOVERED = "UNCOVERED"

FIXTURE_NAMES = ("routing-evals.json", "evals.json", "trigger-evals.json")

# Emoji and pictographs. The repo rule is that decorative emoji do not appear in
# documentation or user-facing copy, and a skill description is read by both a
# model and a human, so it is user-facing copy.
EMOJI_RX = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U0001F000-\U0001F2FF" "☀-➿"
    "️" "⬀-⯿" "]")

# Deliberately small and boring. A long stopword list would quietly become the
# thing being tested, and every word dropped here weakens the separation signal,
# so this holds only words that carry no routing information in any prompt.
STOP = set("""
a an the and or but if then than that this these those there here is are was were
be been being am do does did doing done have has had having will would shall
should can could may might must of in on at to for from with without by as into
over under about it its i me my we our you your he she they them his her their
not no nor so such very just also too only own same how what when where which who
whom why all any both each few more most other some own s t don now d ll m o re ve
y please help need want get got make made use used using
""".split())

WORD_RX = re.compile(r"[a-z][a-z0-9'\-]{2,}")


def words(text: str) -> set:
    return set(w for w in WORD_RX.findall((text or "").lower()) if w not in STOP)


def anchor_score(prompt: str, description: str) -> float:
    """Fraction of the prompt's content words the description also uses.

    Normalised by the prompt, not by the description, on purpose: a long
    description would otherwise score every prompt highly just by covering more
    vocabulary, which is the opposite of discriminating.
    """
    pw = words(prompt)
    if not pw:
        return 0.0
    return len(pw & words(description)) / float(len(pw))


def frontmatter(path: str) -> tuple[dict, str]:
    """The YAML-ish head of a SKILL.md, parsed only as far as this needs.

    Deliberately not a YAML parser: the only keys that matter are scalar, and
    pulling in a dependency to read two lines would make this un-runnable in the
    stdlib-only CI it is meant for. A quoted value keeps its quotes stripped;
    anything structured is left as raw text and treated as unparsed.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        body = fh.read()
    if not body.startswith("---"):
        return {}, body
    end = body.find("\n---", 3)
    if end < 0:
        return {}, body
    head, rest = body[3:end], body[end + 4:]
    out = {}
    lines = head.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        i += 1
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            # A folded or literal block scalar. dot-claude/skills/ship-gate really
            # uses `description: >-`, and treating that as an empty value made the
            # tool report a missing description on a skill that has a long one.
            # Reporting a defect that is not there costs more trust than missing one.
            got = []
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in " \t"):
                got.append(lines[i].strip())
                i += 1
            joiner = "\n" if val.startswith("|") else " "
            val = joiner.join(x for x in got if x).strip()
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out, rest


def load_cases(skill_dir: str) -> tuple[list, str]:
    for name in FIXTURE_NAMES:
        p = os.path.join(skill_dir, name)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (ValueError, OSError) as exc:
                return [{"_error": "{}: {}".format(type(exc).__name__, exc)}], name
            cases = raw.get("cases") if isinstance(raw, dict) else raw
            return (cases if isinstance(cases, list) else []), name
    return [], ""


def grade(skill_dir: str) -> dict:
    """One skill, every grader. Returns a row, never raises on bad input."""
    name = os.path.basename(skill_dir.rstrip("/\\"))
    row = {"skill": name, "status": PASS, "problems": [], "notes": [], "cases": 0}
    md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(md):
        row["status"] = FAIL
        row["problems"].append("no SKILL.md")
        return row

    fm, _ = frontmatter(md)
    desc = fm.get("description", "")
    row["desc"] = desc

    # 1. Structure. A description is the entire routing surface, so an absent or
    #    empty one is not a style problem, it is a skill that cannot be selected.
    if not fm:
        row["problems"].append("no frontmatter block")
    if not fm.get("name"):
        row["problems"].append("frontmatter has no name")
    elif fm["name"] != name:
        row["problems"].append("frontmatter name {!r} != directory {!r}".format(
            fm["name"], name))
    if not desc.strip():
        row["problems"].append("frontmatter has no description, so nothing can route to it")
    for hit in EMOJI_RX.findall(desc):
        row["problems"].append("emoji {!r} in description".format(hit))

    cases, fixture = load_cases(skill_dir)
    if not cases:
        row["status"] = FAIL if row["problems"] else UNCOVERED
        if not fixture:
            row["notes"].append("no routing fixture")
        else:
            row["notes"].append("{} present but held no cases".format(fixture))
        return row
    row["fixture"] = fixture

    # A file that did not parse is its own failure and gets its own sentence. It was
    # folded into the malformed-case count below at first, which told the operator
    # that one case had a bad `expect` value when the truth was that no case had been
    # read at all. A wrong diagnosis sends someone to the wrong line.
    err = [c for c in cases if isinstance(c, dict) and "_error" in c]
    if err:
        row["problems"].append("{} did not parse, so not one case was read: {}".format(
            fixture, str(err[0]["_error"])[:160]))
        cases = [c for c in cases if c not in err]

    bad = [c for c in cases if not isinstance(c, dict)
           or not c.get("prompt") or c.get("expect") not in ("trigger", "skip")]
    if bad:
        row["problems"].append(
            "{} of {} case(s) malformed: each needs a non-empty `prompt` and "
            "`expect` of exactly \"trigger\" or \"skip\"".format(len(bad), len(cases)))
        cases = [c for c in cases if c not in bad]

    trig = [c for c in cases if c.get("expect") == "trigger"]
    skip = [c for c in cases if c.get("expect") == "skip"]
    row["cases"] = len(trig) + len(skip)
    row["triggers"] = [c["prompt"] for c in trig]

    # 2. Fixture integrity. This is the defect worth importing from
    #    just-my-skills: a suite with no negative case cannot fail, so it cannot
    #    tell you anything. Same for no positive case.
    if not trig:
        row["problems"].append("no `trigger` case, so the fixture cannot show the skill is reachable")
    if not skip:
        row["problems"].append("no `skip` case, so the fixture cannot fail and measures nothing")

    # 3. Separation. Every prompt that must route here has to be more anchored in
    #    the description than every prompt that must not.
    if trig and skip:
        ts = sorted(((anchor_score(c["prompt"], desc), c["prompt"]) for c in trig))
        ss = sorted(((anchor_score(c["prompt"], desc), c["prompt"]) for c in skip),
                    reverse=True)
        weakest, strongest = ts[0], ss[0]
        row["margin"] = round(weakest[0] - strongest[0], 4)
        if weakest[0] <= strongest[0]:
            row["problems"].append(
                "the description does not separate the fixture: a skip prompt scores "
                "{:.2f} and the weakest trigger prompt scores {:.2f}\n"
                "        skip:    {}\n        trigger: {}".format(
                    strongest[0], weakest[0], strongest[1][:110], weakest[1][:110]))
        for score, prompt in ts:
            if score == 0.0:
                row["problems"].append(
                    "a trigger prompt shares no content word with the description, so "
                    "nothing in the text can route it: {}".format(prompt[:110]))

    if row["problems"]:
        row["status"] = FAIL
    return row


def cross_check(rows: list) -> list:
    """Does some other skill's description outrank the owner of a trigger prompt?

    The intra-skill grader above can only ask whether a description separates its
    own fixture. It is blind to the failure that actually happens in a library
    this size: two descriptions competing for the same prompt. Measured live on
    this tree, `gws-gmail` describes itself as "Send, read, and manage email",
    which lexically contains everything `gws-gmail-read` and `gws-gmail-triage`
    say about themselves, so a read prompt anchors at least as well in the parent
    as in the sibling that owns it.

    Scored against every description in the corpus, including skills with no
    fixture of their own -- a rival does not need a fixture to steal a prompt.

    There is deliberately no per-case escape hatch. When the overlap is real, the
    honest fix is to narrow the broader description, which is an improvement to
    the routing surface. An `expected_rivals` opt-out would have turned every
    finding here into a one-line silence.
    """
    corpus = [(r["skill"], r.get("desc", "")) for r in rows if r.get("desc", "").strip()]
    out = []
    for r in rows:
        for prompt in r.get("triggers", []):
            mine = anchor_score(prompt, r.get("desc", ""))
            rivals = sorted(((anchor_score(prompt, d), n) for n, d in corpus
                             if n != r["skill"]), reverse=True)
            if rivals and rivals[0][0] >= mine:
                tied = [n for s, n in rivals if s == rivals[0][0]]
                out.append({
                    "owner": r["skill"], "prompt": prompt, "mine": round(mine, 2),
                    "rival_score": round(rivals[0][0], 2), "rivals": tied[:4],
                    # A rival that strictly outranks the owner is a real finding.
                    # An exact tie is a weak one, and the reason is arithmetic, not
                    # charity: the score is a ratio over a handful of content words,
                    # so its value space is small-denominator fractions and two
                    # descriptions land on the same rung often, by construction.
                    # They are reported separately so the strong signal is not
                    # buried under the noisy one; --strict-ties makes both fatal.
                    "strict": rivals[0][0] > mine,
                })
    return out


def scan(root: str, strict: bool, strict_ties: bool = False) -> int:
    if not os.path.isdir(root):
        print("no such skills root: {}".format(root))
        return 2
    dirs = sorted(os.path.join(root, d) for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)))
    rows = [grade(d) for d in dirs]
    failed = [r for r in rows if r["status"] == FAIL]
    uncovered = [r for r in rows if r["status"] == UNCOVERED]
    passed = [r for r in rows if r["status"] == PASS]

    for r in failed:
        print("\n  {:<28} FAIL   ({} case(s))".format(r["skill"], r["cases"]))
        for p in r["problems"]:
            print("      - {}".format(p))
    for r in passed:
        print("\n  {:<28} PASS   {} case(s), margin {}".format(
            r["skill"], r["cases"], r.get("margin", "n/a")))

    collisions = cross_check(rows)
    lost = [c for c in collisions if c["strict"]]
    tied = [c for c in collisions if not c["strict"]]
    for c in lost:
        print("\n  {:<28} OUTRANKED".format(c["owner"]))
        print("      prompt: {}".format(c["prompt"][:110]))
        print("      owner scores {:.2f} and {} scores {:.2f}, so the text routes it "
              "away from its owner".format(c["mine"], "/".join(c["rivals"]), c["rival_score"]))
    for c in tied:
        print("\n  {:<28} TIE (weak signal)".format(c["owner"]))
        print("      prompt: {}".format(c["prompt"][:110]))
        print("      owner and {} both score {:.2f}, so the two descriptions do not "
              "distinguish this prompt".format("/".join(c["rivals"]), c["mine"]))

    print("\n{} skill(s): {} pass, {} fail, {} uncovered, "
          "{} outranked, {} tied".format(
              len(rows), len(passed), len(failed), len(uncovered), len(lost), len(tied)))
    if uncovered:
        # Printed, never hidden. An uncovered skill is the honest majority state
        # of this tree today and the number is the backlog.
        print("  uncovered (no routing fixture): {}".format(
            ", ".join(r["skill"] for r in uncovered)))
    if failed or lost or (tied and strict_ties):
        print("\nVERDICT: FAIL")
        return 1
    if tied:
        print("\n  {} tie(s) above are reported and not fatal. Run with --strict-ties "
              "to enforce them.".format(len(tied)))
    if uncovered and strict:
        print("\nVERDICT: FAIL -- --strict was given and {} skill(s) have no fixture".format(
            len(uncovered)))
        return 1
    if not passed:
        # A green produced by grading nothing is the exact failure mode this tool
        # exists to catch, so it must not be reachable here either. Found on the
        # first real run against this tree: 47 skills, 0 fixtures, and the line
        # below said "PASS on 0 graded skill(s)".
        print("\nVERDICT: NOTHING GRADED -- {} skill(s) present and not one carries a "
              "fixture, so this run measured nothing".format(len(rows)))
        return 1
    print("\nVERDICT: PASS on {} graded skill(s); {} uncovered and counted".format(
        len(passed), len(uncovered)))
    return 0


def _mk(root: str, name: str, desc: str, cases) -> str:
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: {}\ndescription: \"{}\"\n---\n\nbody\n".format(name, desc))
    if cases is not None:
        with open(os.path.join(d, "routing-evals.json"), "w", encoding="utf-8") as fh:
            json.dump({"cases": cases}, fh)
    return d


def selftest() -> int:
    """Prove each grader discriminates, rather than that it runs.

    Every assertion below is a planted fault plus its clean twin. A grader that
    passes the clean case and fails the faulted one has detection power; one that
    passes both is decorative, which is the specific failure mode this whole tool
    was written in response to.
    """
    rc = 0

    def check(label, got, want):
        """Print one verdict.

        The failing marker is exactly `[FAIL]` because tools/audit/mutate.py reads
        that prefix to attribute a caught mutation to a named check. This printed
        `[MISS]` first, and the whole spec came back green with "WEAK SIGNAL" on
        every single line: nonzero exit, no check the harness could name. A selftest
        that fails in a vocabulary its own harness does not read is only half a test.
        """
        nonlocal rc
        ok = got == want
        print("[{}] {}{}".format(
            "ok  " if ok else "FAIL", label,
            "" if ok else "  <- got {!r} want {!r}".format(got, want)))
        if not ok:
            rc |= 1

    with tempfile.TemporaryDirectory() as td:
        good = [{"prompt": "sign the aws request with sigv4", "expect": "trigger"},
                {"prompt": "book a dentist appointment", "expect": "skip"}]
        d = _mk(td, "aws-signer", "Use when signing an aws request with sigv4.", good)
        check("a separating fixture passes", grade(d)["status"], PASS)

        # Separation, faulted: the skip prompt is the one the description covers.
        d = _mk(td, "aws-signer-2", "Use when signing an aws request with sigv4.",
                [{"prompt": "sigv4 aws request signing", "expect": "skip"},
                 {"prompt": "unrelated dentist booking", "expect": "trigger"}])
        r = grade(d)
        check("an inverted fixture fails", r["status"], FAIL)
        check("  and says which two prompts collided",
              any("does not separate" in p for p in r["problems"]), True)

        # A trigger prompt with no lexical anchor at all.
        d = _mk(td, "anchorless", "Use when signing an aws request with sigv4.",
                [{"prompt": "reticulate the splines", "expect": "trigger"},
                 {"prompt": "quiet unrelated errand", "expect": "skip"}])
        check("an unanchored trigger prompt fails",
              any("shares no content word" in p for p in grade(d)["problems"]), True)

        # Separation must compare the WEAKEST trigger, not the best one. Mutation
        # testing found this unguarded: every faulted fixture above held exactly one
        # trigger, so weakest and strongest were the same case and sorting the wrong
        # way was invisible. Here trigger B sits below the skip prompt while trigger
        # A sits above it, which is the ordinary shape of a real fixture that has one
        # well-worded example and one badly-worded one.
        d = _mk(td, "one-good-one-bad", "Use when signing an aws request with sigv4.",
                [{"prompt": "sigv4 aws request signing", "expect": "trigger"},
                 {"prompt": "sigv4 handshake", "expect": "trigger"},
                 {"prompt": "aws request for a dentist", "expect": "skip"}])
        check("a well-worded trigger does not cover for a badly-worded one beside it",
              any("does not separate" in p for p in grade(d)["problems"]), True)

        # Fixture integrity: the just-my-skills shape, all positives.
        d = _mk(td, "all-positive", "Use when signing an aws request with sigv4.",
                [{"prompt": "sign an aws request", "expect": "trigger"},
                 {"prompt": "sigv4 signing please", "expect": "trigger"}])
        check("an all-positive fixture fails as unfalsifiable",
              any("cannot fail" in p for p in grade(d)["problems"]), True)

        # And its mirror. Two halves of one rule are two behaviours, and the
        # all-negative half was unguarded until mutation testing said so.
        d = _mk(td, "all-negative", "Use when signing an aws request with sigv4.",
                [{"prompt": "book a dentist appointment", "expect": "skip"},
                 {"prompt": "resize an image", "expect": "skip"}])
        check("an all-negative fixture fails as unreachable",
              any("cannot show the skill is reachable" in p
                  for p in grade(d)["problems"]), True)

        # Malformed cases must be named, not silently dropped.
        d = _mk(td, "malformed", "Use when signing an aws request with sigv4.",
                [{"prompt": "sign an aws request", "expect": "yes"},
                 {"prompt": "dentist", "expect": "skip"}])
        check("a case with a bad expect value is reported",
              any("malformed" in p for p in grade(d)["problems"]), True)

        # Structure.
        d = _mk(td, "misnamed", "Use when signing an aws request with sigv4.", good)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: something-else\ndescription: \"x aws sigv4 signing\"\n---\n")
        check("a frontmatter name that disagrees with its directory fails",
              any("!= directory" in p for p in grade(d)["problems"]), True)

        d = _mk(td, "emojid", "Use when signing an aws sigv4 request \U0001F680", good)
        check("an emoji in the description fails the repo rule",
              any("emoji" in p for p in grade(d)["problems"]), True)

        # An empty description is not a style problem. It is a skill nothing can
        # route to, and it was unguarded here until mutation testing said so.
        d = _mk(td, "descless", "", good)
        check("an empty description fails, because nothing can route to it",
              any("no description" in p for p in grade(d)["problems"]), True)

        d = _mk(td, "nofixture", "Use when signing an aws request with sigv4.", None)
        check("a skill with no fixture is UNCOVERED, not PASS and not FAIL",
              grade(d)["status"], UNCOVERED)

    # The whole scan must be red while any skill is red, and that needs its own tree.
    # This check used to run against the shared faulted tree above, where eight
    # skills share one description: the tree was full of cross-skill losses, so scan
    # returned 1 through the collision branch no matter what the failure branch did,
    # and deleting `failed` from the verdict changed nothing observable. A fixture
    # rich enough to be convenient is rich enough to mask the thing it is testing.
    # Here: two disjoint vocabularies, no collision, no uncovered skill, and one
    # green skill so the NOTHING-GRADED branch cannot supply the exit code either.
    with tempfile.TemporaryDirectory() as tr:
        _mk(tr, "clean", "Use when signing an aws request with sigv4.",
            [{"prompt": "sign the aws request with sigv4", "expect": "trigger"},
             {"prompt": "knead the sourdough overnight", "expect": "skip"}])
        _mk(tr, "broken", "Bake bread: knead sourdough overnight \U0001F680",
            [{"prompt": "knead the sourdough overnight", "expect": "trigger"},
             {"prompt": "sign the aws request with sigv4", "expect": "skip"}])
        check("scan returns nonzero on a red skill alone, with no collision to lean on",
              scan(tr, False), 1)

    # A fixture that will not parse must be louder than a missing one, not quieter.
    with tempfile.TemporaryDirectory() as tb:
        d = _mk(tb, "brokenjson", "Use when signing an aws request with sigv4.",
                [{"prompt": "sign the aws request with sigv4", "expect": "trigger"},
                 {"prompt": "knead the sourdough", "expect": "skip"}])
        with open(os.path.join(d, "routing-evals.json"), "w", encoding="utf-8") as fh:
            fh.write('{"cases": [ this is not json ')
        r = grade(d)
        check("an unparseable fixture is FAIL, not the UNCOVERED of having none",
              r["status"], FAIL)
        check("  and the run says the file did not parse, not that a case was malformed",
              any("did not parse" in p for p in r["problems"]), True)

    # A folded block scalar is a description, not an absence. ship-gate uses one.
    with tempfile.TemporaryDirectory() as tf:
        d = os.path.join(tf, "folded")
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: folded\ndescription: >-\n  Use when signing an aws\n"
                     "  request with sigv4.\n---\n\nbody\n")
        check("a `description: >-` block scalar is read, not reported missing",
              any("no description" in p for p in grade(d)["problems"]), False)
        check("  and its folded text is what gets scored",
              anchor_score("signing an aws sigv4 request", grade(d)["desc"]) == 1.0, True)
        # No stemming, by choice: "sign" does not match "signing". Stemming would
        # raise every score toward each other and blunt the separation this whole
        # measure depends on, and it would make a failure harder to read back to
        # the two strings that caused it. The cost is real and is this assertion.
        check("  and an unstemmed near-miss scores below an exact match",
              anchor_score("sign an aws sigv4 request", grade(d)["desc"]) < 1.0, True)

    # Cross-skill collision, and its clean twin. This is the grader the intra-skill
    # pass cannot substitute for, so it needs its own planted fault.
    with tempfile.TemporaryDirectory() as tc:
        # The parent's description contains everything the child's does, which is
        # the live shape in dot-claude/skills: gws-gmail says "Send, read, and
        # manage email" and gws-gmail-read says "Read a message". The child still
        # separates its own fixture perfectly, so only the cross-check can see it.
        _mk(tc, "parent", "Gmail: send, read, manage a message or email thread.",
            [{"prompt": "send an email to the team", "expect": "trigger"},
             {"prompt": "resize this image", "expect": "skip"}])
        _mk(tc, "child", "Gmail: read a message.",
            [{"prompt": "read a message", "expect": "trigger"},
             {"prompt": "read the email thread", "expect": "trigger"},
             {"prompt": "resize this image", "expect": "skip"}])
        graded = [grade(os.path.join(tc, n)) for n in ("parent", "child")]
        check("  the subsumed child still passes its own intra-skill fixture",
              [g["status"] for g in graded], [PASS, PASS])
        cols = cross_check(graded)
        check("a description that subsumes a sibling is caught as a collision",
              sorted((c["owner"], c["rivals"][0], c["strict"]) for c in cols),
              [("child", "parent", False), ("child", "parent", True)])
        check("  and the whole scan goes red on a strict loss alone", scan(tc, False), 1)

    # The tie is deliberately weaker than the loss, so that difference needs its
    # own planted fault: a tree holding a tie and nothing else must stay green by
    # default and go red under --strict-ties. Without this pair, downgrading ties
    # would be indistinguishable from switching the check off.
    with tempfile.TemporaryDirectory() as tt:
        _mk(tt, "alpha", "Gmail: read a message.",
            [{"prompt": "read a message", "expect": "trigger"},
             {"prompt": "resize this image", "expect": "skip"}])
        _mk(tt, "beta", "Gmail: read a message quickly.",
            [{"prompt": "read a message quickly", "expect": "trigger"},
             {"prompt": "resize this image", "expect": "skip"}])
        check("a tie alone is reported but does not fail the run", scan(tt, False), 0)
        check("  and the same tie fails under --strict-ties", scan(tt, False, True), 1)

    # Grading nothing is not a pass.
    with tempfile.TemporaryDirectory() as tn:
        _mk(tn, "bare", "Use when signing an aws request with sigv4.", None)
        check("a tree where nothing has a fixture does not report PASS", scan(tn, False), 1)

    print("\nVERDICT: {}".format(
        "every grader discriminates" if rc == 0 else "skilleval selftest has failures above"))
    return rc


def main(argv) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="skilleval", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="grade every skill under a root")
    s.add_argument("--root", default=os.path.join("payload", "dot-claude", "skills"))
    s.add_argument("--strict", action="store_true",
                   help="also fail when a skill has no routing fixture")
    s.add_argument("--strict-ties", action="store_true",
                   help="also fail on an exact cross-skill tie, not only on a strict loss")
    sub.add_parser("selftest", help="prove each grader discriminates")
    a = ap.parse_args(argv)
    return selftest() if a.cmd == "selftest" else scan(a.root, a.strict, a.strict_ties)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
