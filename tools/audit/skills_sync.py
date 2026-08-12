#!/usr/bin/env python3
"""Measure drift between the committed skills tree and the live one, both ways.

Why this is a check and not a one-off copy. On 2026-07-25 `dot-claude/skills` and
`~/.claude/skills` each held 30 directories, which looks like a synced pair and is
not one: 17 were repo-only and 17 were live-only. Both halves are failures and
they fail differently.

  repo-only  A skill that is committed and not deployed is invisible. No running
             session can invoke it or read it, so the procedure it documents is
             not part of the system no matter how good it is. `ship-gate` was in
             this bucket, which means the mandatory pre-done procedure could be
             enforced by a Stop hook while being unreadable by the agent the hook
             was blocking.

  live-only  A skill that is deployed and not committed exists in exactly one
             place on one machine. It is not reviewable, not diffable, and gone
             with the directory. `pointers.py` cannot see it either, because that
             scans the repo.

  drift      Same name both sides, different bytes. Whichever side someone reads
             is a coin flip, and the repo copy is the one that gets reviewed.

  squatting  An entry in a skills tree that is a FILE where a directory belongs,
             holding one dead path. `dot-claude/skills` has 30 real directories
             and 33 of these, which is why an entry count of 63 was ever read as
             63 skills. The first version of this checker listed directories and
             so was blind to all 33: they had to be found by hand, which is the
             precise failure this file exists to stop. Reported and FAILING.

Hollow skills are called out rather than counted as gaps. A skill whose whole
body is a path to a WSL file that is not on this machine is worse deployed than
absent: a name in the skill listing is a promise that something is behind it.
Deploying one converts a silent absence into a silent no-op, which is the failure
mode this whole subsystem exists to stop. So they are reported as HOLLOW and
excluded from the deployable set.

A squatter is not the same as an empty name, and the difference decides the
repair. Every one of the 33 had its real content in a sibling tree, 10 of them
live and running. So the report names, per squatter, which tree actually holds
the body, and the fix is to replace the file with that directory rather than to
write a skill from nothing.

Exit codes: 0 clean, 1 drift found, 2 could not run.

  python tools/audit/skills_sync.py check
  python tools/audit/skills_sync.py check --strict     # hollow also fails
  python tools/audit/skills_sync.py deploy --dry-run   # what would be copied
  python tools/audit/skills_sync.py deploy --apply     # repo -> live, real only
  python tools/audit/skills_sync.py import --apply     # live-only -> repo
  python tools/audit/skills_sync.py selftest
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# A path that only exists under WSL or under the retired codex tree. A body whose
# only content is one of these is a pointer to nowhere on this machine.
DEAD_PATH = re.compile(r"(/home/[A-Za-z0-9_.-]+|~/\.codex/|/mnt/[a-z]/)")

POINTER_MAX_LINES = 3
THIN_MAX_LINES = 40


def setup_root():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def repo_skills(root=None):
    return os.path.join(root or setup_root(), "dot-claude", "skills")


def live_skills():
    return os.path.join(os.environ.get("CLAUDE_LIVE_HOME") or os.path.expanduser("~"),
                        ".claude", "skills")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_frontmatter(txt):
    if txt.startswith("---"):
        end = txt.find("\n---", 3)
        if end != -1:
            return txt[end + 4:]
    return txt


def classify(skill_md):
    """real | thin | pointer, plus the body line count and any dead paths.

    A pointer is judged by content, not size: three lines or fewer, or a short
    body whose substance is a path that does not resolve here.
    """
    try:
        txt = open(skill_md, encoding="utf-8", errors="replace").read()
    except OSError:
        return "unreadable", 0, []
    body = strip_frontmatter(txt)
    lines = [l for l in body.splitlines() if l.strip()]
    n = len(lines)
    dead = sorted(set(DEAD_PATH.findall(body)))
    if n <= POINTER_MAX_LINES:
        return "pointer", n, dead
    if n < THIN_MAX_LINES and dead:
        return "pointer", n, dead
    if n < THIN_MAX_LINES:
        return "thin", n, dead
    return "real", n, dead


def listdirs(base):
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))


def listfiles(base):
    """Entries that are files. In a skills tree every one of these is a defect."""
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isfile(os.path.join(base, d)) and not d.startswith("."))


# Trees that may hold the real body of a name that is only a pointer file in
# dot-claude/skills. Order is preference: what actually runs, then the generic
# agents tree, then the codex tree.
def sibling_trees(root):
    home = os.environ.get("CLAUDE_LIVE_HOME") or os.path.expanduser("~")
    return [
        ("LIVE", os.path.join(home, ".claude", "skills")),
        ("dot-agents", os.path.join(root, "dot-agents", "skills")),
        ("dot-codex", os.path.join(root, "dot-codex", "skills")),
    ]


def locate_body(name, root, skip=None):
    """Every sibling tree holding a SKILL.md for this name, with its condition.

    Returns (label, lines, state) where state is one of:

      usable   real or thin procedure with no dead path. Copy it.
      deadpath a body with real procedure that names a path off this machine.
               Copying it moves the rot, so the repair is copy plus a path fix.
      hollow   three lines or fewer. The name is a pointer here too, so this
               tree is another link in the chain, not the end of it.

    An earlier version returned only the usable ones, so the caller rendered
    every other case as NOWHERE. That was wrong in the module's own terms: it
    reported 7 names as needing to be written from scratch when `dot-codex` held
    20 to 28 lines of procedure for each, contaminated only by a `/home/shovalbe`
    path. Absence and unusability call for different repairs, so a report that
    prints one word for both cannot be acted on.
    """
    found = []
    for label, base in sibling_trees(root):
        if skip and label in skip:
            continue
        md = os.path.join(base, name, "SKILL.md")
        if not os.path.exists(md):
            continue
        kind, n, dead = classify(md)
        if n <= POINTER_MAX_LINES:
            state = "hollow"
        elif dead:
            state = "deadpath"
        else:
            state = "usable"
        found.append((label, n, state))
    # Best candidate first, so the preference order in the report is the order a
    # person should try. Tree order breaks ties.
    rank = {"usable": 0, "deadpath": 1, "hollow": 2}
    return sorted(found, key=lambda r: rank[r[2]])


def render_body(where):
    """The `body lives in:` column. NOWHERE means no SKILL.md in any tree."""
    if not where:
        return "NOWHERE"
    note = {"usable": "", "deadpath": ", dead path", "hollow": ", hollow"}
    return ", ".join("{}({} lines{})".format(l, n, note[st]) for l, n, st in where)


def usable(where):
    return [r for r in where if r[2] == "usable"]


def survey(repo_base, live_base, root=None):
    """Everything the report and the deploy both need, computed once."""
    root = root or setup_root()
    r, l = set(listdirs(repo_base)), set(listdirs(live_base))
    out = {"repo_only": [], "live_only": [], "drift": [], "same": [],
           "eol_only": [],
           "hollow_repo": [], "hollow_live": [], "no_manifest": [],
           "squat_repo": [], "squat_live": []}

    # Files where directories belong, on either side. Recorded with the tree that
    # holds the real body, because that is what turns a report into a repair.
    for side, base, key in (("repo", repo_base, "squat_repo"),
                            ("live", live_base, "squat_live")):
        for name in listfiles(base):
            p = os.path.join(base, name)
            try:
                head = open(p, encoding="utf-8", errors="replace").read(400).strip()
            except OSError:
                head = ""
            first = head.splitlines()[0] if head else ""
            dead = bool(DEAD_PATH.search(head))
            skip = ["LIVE"] if side == "live" else None
            out[key].append((name, os.path.getsize(p), first, dead,
                             locate_body(name, root, skip=skip)))

    for name in sorted(r - l):
        md = os.path.join(repo_base, name, "SKILL.md")
        if not os.path.exists(md):
            out["no_manifest"].append((name, "repo"))
            continue
        kind, n, dead = classify(md)
        row = (name, kind, n, dead)
        (out["hollow_repo"] if kind == "pointer" else out["repo_only"]).append(row)

    for name in sorted(l - r):
        md = os.path.join(live_base, name, "SKILL.md")
        if not os.path.exists(md):
            out["no_manifest"].append((name, "live"))
            continue
        kind, n, dead = classify(md)
        row = (name, kind, n, dead)
        (out["hollow_live"] if kind == "pointer" else out["live_only"]).append(row)

    for name in sorted(r & l):
        a = os.path.join(repo_base, name, "SKILL.md")
        b = os.path.join(live_base, name, "SKILL.md")
        if not (os.path.exists(a) and os.path.exists(b)):
            out["no_manifest"].append((name, "both-sides"))
            continue
        if sha(a) == sha(b):
            out["same"].append(name)
        elif text_sha(a) == text_sha(b):
            # Character-identical, byte-different: the live tree is written by
            # Windows and the repo by WSL. Its own bucket rather than drift,
            # because no human decision exists here, and rather than "same",
            # because the asymmetry is real and hiding it is how it comes back.
            out["eol_only"].append((name, os.path.getsize(a), os.path.getsize(b)))
        else:
            out["drift"].append((name, os.path.getsize(a), os.path.getsize(b)))
    return out


def text_sha(path):
    """Hash of the file's characters, with line endings normalised.

    Deliberately narrow. It collapses CRLF to LF and nothing else, so a trailing
    space, a changed word or a reordered section still hashes differently. The
    only equivalence asserted is the one the two host operating systems create.
    """
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def report(s, repo_base, live_base, strict=False):
    print("repo: {}".format(repo_base))
    print("live: {}".format(live_base))
    print()
    print("in sync (same bytes): {}".format(len(s["same"])))

    def block(title, rows, why):
        if not rows:
            return
        print()
        print("{} ({})".format(title, len(rows)))
        print("  " + why)
        for row in sorted(rows, key=lambda x: -x[2] if len(x) > 2 and isinstance(x[2], int) else 0):
            name, kind, n = row[0], row[1], row[2]
            dead = ("  dead-path: " + ",".join(row[3])) if len(row) > 3 and row[3] else ""
            print("    {:<28} {:<8} {:>4} body lines{}".format(name, kind, n, dead))

    block("COMMITTED BUT NOT DEPLOYED", s["repo_only"],
          "no session can invoke or read these")
    block("DEPLOYED BUT NOT COMMITTED", s["live_only"],
          "exist on one machine only, in no commit, unreviewable")
    block("HOLLOW, repo side", s["hollow_repo"],
          "deploying these would publish a name with nothing behind it")
    block("HOLLOW, live side", s["hollow_live"],
          "already published with nothing behind them; a session can invoke these and get nothing")

    if s["drift"]:
        print()
        print("SAME NAME, DIFFERENT BYTES ({})".format(len(s["drift"])))
        print("  whichever side someone reads is a coin flip")
        for name, a, b in s["drift"]:
            print("    {:<28} repo {}b   live {}b".format(name, a, b))

    for side, key in (("repo", "squat_repo"), ("live", "squat_live")):
        rows = s[key]
        if not rows:
            continue
        print()
        print("A FILE WHERE A SKILL DIRECTORY BELONGS, {} side ({})".format(side, len(rows)))
        print("  these are why an entry count is not a skill count")
        for name, size, first, dead, where in sorted(rows):
            print("    {:<28} {:>4}b  body lives in: {}".format(
                name, size, render_body(where)))
            print("        contains: {}{}".format(first[:88],
                                                  "   [dead path]" if dead else ""))

    if s["eol_only"]:
        print()
        print("LINE ENDINGS ONLY ({})".format(len(s["eol_only"])))
        print("  character-identical; no decision to make, but the trees are not byte-equal")
        for name, a, b in s["eol_only"]:
            print("    {:<28} repo {}b   live {}b".format(name, a, b))

    if s["no_manifest"]:
        print()
        print("NO SKILL.md ({})".format(len(s["no_manifest"])))
        for name, side in s["no_manifest"]:
            print("    {:<28} {}".format(name, side))

    bad = (len(s["repo_only"]) + len(s["live_only"]) + len(s["drift"])
           + len(s["no_manifest"]) + len(s["squat_repo"]) + len(s["squat_live"]))
    if strict:
        bad += len(s["hollow_repo"]) + len(s["hollow_live"])
    print()
    if bad:
        print("DRIFT: {} item(s) need a decision".format(bad))
    else:
        print("CLEAN: repo and live agree on every substantive skill")
    return 1 if bad else 0


def copy_skill(src_dir, dst_dir):
    """Replace whatever is at dst_dir with a copy of src_dir.

    The isfile branch is the squatting case: a 38-byte pointer file holding the
    name. copytree would raise FileExistsError on it, so an import that did not
    handle this would fail on exactly the 10 names that most needed importing.
    """
    if os.path.isdir(dst_dir):
        shutil.rmtree(dst_dir)
    elif os.path.isfile(dst_dir):
        os.remove(dst_dir)
    shutil.copytree(src_dir, dst_dir)


def cmd_deploy(a):
    repo_base, live_base = repo_skills(), live_skills()
    s = survey(repo_base, live_base)
    todo = [r[0] for r in s["repo_only"]]
    drift = [r[0] for r in s["drift"]] if a.include_drift else []
    if not todo and not drift:
        print("nothing to deploy")
        return 0
    print("deploy repo -> live, {} new + {} overwrite".format(len(todo), len(drift)))
    for name in todo:
        print("  new       {}".format(name))
    for name in drift:
        print("  overwrite {}".format(name))
    if s["hollow_repo"]:
        print("  skipped {} hollow: {}".format(
            len(s["hollow_repo"]), ", ".join(r[0] for r in s["hollow_repo"])))
    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply.")
        return 0
    for name in todo + drift:
        copy_skill(os.path.join(repo_base, name), os.path.join(live_base, name))
    # Re-survey from disk rather than asserting on what we think we wrote.
    s2 = survey(repo_base, live_base)
    still = [r[0] for r in s2["repo_only"]] + [r[0] for r in s2["drift"]]
    remaining = [n for n in (todo + drift) if n in still]
    if remaining:
        print("\nFAILED: still not in sync after copy: {}".format(", ".join(remaining)))
        return 1
    print("\nverified from disk: {} skill(s) now match live".format(len(todo + drift)))
    return 0


def cmd_import(a):
    repo_base, live_base = repo_skills(), live_skills()
    s = survey(repo_base, live_base)
    todo = [r[0] for r in s["live_only"]]
    if not todo:
        print("nothing to import")
        return 0
    squatters = {r[0] for r in s["squat_repo"]}
    print("import live -> repo, {} skill(s)".format(len(todo)))
    for name in todo:
        note = "  (replaces a squatting pointer file)" if name in squatters else ""
        print("  {}{}".format(name, note))
    left = sorted(squatters - set(todo))
    if left:
        print()
        print("{} squatting pointer file(s) this import does NOT resolve, because".format(len(left)))
        print("no live directory holds their body. Each needs a decision, not a copy.")
        print("The repair differs by what the sibling trees actually hold:")
        print("  usable      copy that tree's directory over the pointer file")
        print("  dead path   real procedure naming a path off this machine: copy AND fix")
        print("  hollow      a pointer there too, so this name has no body anywhere")
        print("  NOWHERE     no SKILL.md in any tree; writing one is authoring, not repair")
        for name, size, first, dead, where in sorted(s["squat_repo"]):
            if name not in left:
                continue
            print("  {:<28} body lives in: {}".format(name, render_body(where)))
    if s["hollow_live"]:
        print("  skipped {} hollow: {}".format(
            len(s["hollow_live"]), ", ".join(r[0] for r in s["hollow_live"])))
    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply.")
        return 0
    for name in todo:
        copy_skill(os.path.join(live_base, name), os.path.join(repo_base, name))
    s2 = survey(repo_base, live_base)
    still = [r[0] for r in s2["live_only"]]
    remaining = [n for n in todo if n in still]
    if remaining:
        print("\nFAILED: still live-only after copy: {}".format(", ".join(remaining)))
        return 1
    print("\nverified from disk: {} skill(s) now in the repo".format(len(todo)))
    print("they are UNCOMMITTED. git add + commit is a separate, human step.")
    return 0


def cmd_check(a):
    repo_base, live_base = repo_skills(), live_skills()
    if not os.path.isdir(repo_base):
        print("cannot run: no repo skills tree at {}".format(repo_base))
        return 2
    if not os.path.isdir(live_base):
        print("cannot run: no live skills tree at {}".format(live_base))
        return 2
    return report(survey(repo_base, live_base), repo_base, live_base, strict=a.strict)


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
FRONT = "---\nname: {}\ndescription: planted\n---\n\n"


def write_skill(base, name, body):
    d = os.path.join(base, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(FRONT.format(name) + body)
    return d


def real_body(tag="x"):
    return "# Real\n\n" + "\n".join("line {} about {}".format(i, tag) for i in range(60))


def cmd_selftest(a):
    """Plant every case, including the ones that must NOT fire.

    A checker that can only report drift carries no more information than one
    that can only report clean, which is the hooks_exist.py failure: it reported
    success having examined zero hooks. So there is a planted all-clean case and
    a planted hollow case that must be excluded from the deployable set.
    """
    fails = []

    def ok(msg):
        print("[ok  ] " + msg)

    def bad(msg):
        print("[FAIL] " + msg)
        fails.append(msg)

    def check(cond, msg):
        ok(msg) if cond else bad(msg)

    tmp = tempfile.mkdtemp(prefix="skills-sync-")
    try:
        # --- case 1: a genuinely clean pair reports clean --------------------
        r1 = os.path.join(tmp, "c1", "repo")
        l1 = os.path.join(tmp, "c1", "live")
        for base in (r1, l1):
            write_skill(base, "alpha", real_body())
        s = survey(r1, l1)
        check(s["same"] == ["alpha"] and not s["repo_only"] and not s["live_only"]
              and not s["drift"], "a clean pair reports clean, so a pass carries information")

        # --- case 2: repo-only real skill is a gap --------------------------
        r2 = os.path.join(tmp, "c2", "repo")
        l2 = os.path.join(tmp, "c2", "live")
        os.makedirs(l2, exist_ok=True)
        write_skill(r2, "beta", real_body())
        s = survey(r2, l2)
        check([x[0] for x in s["repo_only"]] == ["beta"],
              "a committed-but-undeployed real skill is reported")

        # --- case 3: live-only real skill is also a gap ---------------------
        r3 = os.path.join(tmp, "c3", "repo")
        l3 = os.path.join(tmp, "c3", "live")
        os.makedirs(r3, exist_ok=True)
        write_skill(l3, "gamma", real_body())
        s = survey(r3, l3)
        check([x[0] for x in s["live_only"]] == ["gamma"],
              "a deployed-but-uncommitted skill is reported, not silently accepted")

        # --- case 4: same name different bytes is drift ----------------------
        r4 = os.path.join(tmp, "c4", "repo")
        l4 = os.path.join(tmp, "c4", "live")
        write_skill(r4, "delta", real_body("repo side"))
        write_skill(l4, "delta", real_body("live side, differs"))
        s = survey(r4, l4)
        check([x[0] for x in s["drift"]] == ["delta"],
              "same name with different bytes is drift, not in-sync")

        # --- case 5: byte-identical is NOT drift ----------------------------
        r5 = os.path.join(tmp, "c5", "repo")
        l5 = os.path.join(tmp, "c5", "live")
        write_skill(r5, "eps", real_body("same"))
        write_skill(l5, "eps", real_body("same"))
        s = survey(r5, l5)
        check(not s["drift"] and s["same"] == ["eps"],
              "byte-identical copies are not reported as drift")

        # --- case 6: a hollow pointer is HOLLOW, not deployable -------------
        r6 = os.path.join(tmp, "c6", "repo")
        l6 = os.path.join(tmp, "c6", "live")
        os.makedirs(l6, exist_ok=True)
        write_skill(r6, "zeta", "/home/shovalbe/.codex/hooks/zeta.sh\n")
        s = survey(r6, l6)
        check(not s["repo_only"] and [x[0] for x in s["hollow_repo"]] == ["zeta"],
              "a one-line dead-path skill is HOLLOW, excluded from the deployable set")

        # --- case 7: a short but self-contained skill is thin, not hollow ---
        r7 = os.path.join(tmp, "c7", "repo")
        l7 = os.path.join(tmp, "c7", "live")
        os.makedirs(l7, exist_ok=True)
        write_skill(r7, "eta", "# Eta\n\n" + "\n".join(
            "step {}".format(i) for i in range(12)))
        s = survey(r7, l7)
        check([x[0] for x in s["repo_only"]] == ["eta"] and s["repo_only"][0][1] == "thin",
              "a short skill with real content is thin and still deployable")

        # --- case 8: a directory with no SKILL.md is reported, not skipped --
        r8 = os.path.join(tmp, "c8", "repo")
        l8 = os.path.join(tmp, "c8", "live")
        os.makedirs(os.path.join(r8, "theta"), exist_ok=True)
        os.makedirs(l8, exist_ok=True)
        s = survey(r8, l8)
        check(s["no_manifest"] == [("theta", "repo")],
              "a skill directory with no SKILL.md is reported")

        # --- case 9: exit code is 1 on drift and 0 on clean -----------------
        class A:
            strict = False
        r9 = os.path.join(tmp, "c9", "repo")
        l9 = os.path.join(tmp, "c9", "live")
        write_skill(r9, "iota", real_body("same"))
        write_skill(l9, "iota", real_body("same"))
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            clean_rc = report(survey(r9, l9), r9, l9)
            write_skill(r9, "kappa", real_body())
            dirty_rc = report(survey(r9, l9), r9, l9)
        check(clean_rc == 0 and dirty_rc == 1,
              "exit 0 on clean, exit 1 on drift")

        # --- case 10: hollow only fails under --strict ----------------------
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lax = report(survey(r6, l6), r6, l6, strict=False)
            strict = report(survey(r6, l6), r6, l6, strict=True)
        check(lax == 0 and strict == 1,
              "hollow passes by default and fails under --strict")

        # --- case 11: a FILE where a directory belongs is caught ------------
        # The regression case. The first version listed directories only and was
        # blind to 33 of these in the real tree.
        r11 = os.path.join(tmp, "c11", "repo")
        l11 = os.path.join(tmp, "c11", "live")
        os.makedirs(r11, exist_ok=True)
        os.makedirs(l11, exist_ok=True)
        with open(os.path.join(r11, "lambda"), "w", encoding="utf-8") as fh:
            fh.write("/home/shovalbe/.codex/skills/lambda\n")
        s = survey(r11, l11, root=tmp)
        check([x[0] for x in s["squat_repo"]] == ["lambda"] and s["squat_repo"][0][3] is True,
              "a file where a skill directory belongs is caught, and its dead path flagged")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report(survey(r11, l11, root=tmp), r11, l11)
        check(rc == 1, "a squatting file alone is enough to fail the check")

        # --- case 12: the squatter's real body is located -------------------
        # A squatter whose body exists elsewhere is a repair; one whose body
        # exists nowhere is a deletion. The report must tell them apart.
        root12 = os.path.join(tmp, "c12")
        r12 = os.path.join(root12, "dot-claude", "skills")
        l12 = os.path.join(root12, "live")
        os.makedirs(r12, exist_ok=True)
        os.makedirs(l12, exist_ok=True)
        write_skill(os.path.join(root12, "dot-codex", "skills"), "mu", real_body())
        for n in ("mu", "nu"):
            with open(os.path.join(r12, n), "w", encoding="utf-8") as fh:
                fh.write("/home/shovalbe/.codex/skills/{}\n".format(n))
        s = survey(r12, l12, root=root12)
        by = {x[0]: x[4] for x in s["squat_repo"]}
        check([l for l, _, _ in by.get("mu", [])] == ["dot-codex"] and by.get("nu") == [],
              "the tree holding a squatter's real body is named, and NOWHERE is distinguished")

        # --- case 12b: a body that exists but is unusable is not NOWHERE ----
        # The regression this case pins: locate_body used to drop any candidate
        # classify() called a pointer, so the report printed NOWHERE for a name
        # with 20-plus lines of procedure in dot-codex that merely named a
        # /home/shovalbe path. Copying that moves the rot, so it must not read as
        # usable either. Three states, three repairs, three renderings.
        root12b = os.path.join(tmp, "c12b")
        r12b = os.path.join(root12b, "dot-claude", "skills")
        l12b = os.path.join(root12b, "live")
        sib = os.path.join(root12b, "dot-codex", "skills")
        os.makedirs(r12b, exist_ok=True)
        os.makedirs(l12b, exist_ok=True)
        # real procedure, but one line names a path that is not on this machine
        write_skill(sib, "rho", real_body() + "\nSee /home/shovalbe/.codex/x.md\n")
        write_skill(sib, "sigma", "one line only\n")          # hollow there too
        write_skill(sib, "tau", real_body())                  # clean
        for n in ("rho", "sigma", "tau", "upsilon"):
            with open(os.path.join(r12b, n), "w", encoding="utf-8") as fh:
                fh.write("/home/shovalbe/.codex/skills/{}\n".format(n))
        by = {x[0]: x[4] for x in survey(r12b, l12b, root=root12b)["squat_repo"]}
        states = {k: [st for _, _, st in v] for k, v in by.items()}
        check(states == {"rho": ["deadpath"], "sigma": ["hollow"],
                         "tau": ["usable"], "upsilon": []},
              "a body that exists but is unusable is distinguished from no body at all")
        check(render_body(by["rho"]).endswith(", dead path)")
              and render_body(by["sigma"]).endswith(", hollow)")
              and render_body(by["upsilon"]) == "NOWHERE"
              and "," not in render_body(by["tau"]),
              "each state renders differently, so the report names the repair")
        check([r[0] for r in usable(by["rho"])] == []
              and [r[0] for r in usable(by["tau"])] == ["dot-codex"],
              "usable() refuses a contaminated body, so no caller can auto-copy rot")
        # Preference order: a clean body must outrank a contaminated one for the
        # same name, or the report tells a person to try the worse tree first.
        write_skill(os.path.join(root12b, "dot-agents", "skills"), "rho", real_body())
        by2 = {x[0]: x[4] for x in survey(r12b, l12b, root=root12b)["squat_repo"]}
        check([st for _, _, st in by2["rho"]] == ["usable", "deadpath"],
              "a clean body outranks a contaminated one for the same name")

        # --- case 13: import replaces a squatting file, not just a dir ------
        # copytree raises FileExistsError on a file, so without the isfile branch
        # this would fail on exactly the names that most need importing.
        root13 = os.path.join(tmp, "c13")
        r13 = os.path.join(root13, "repo")
        l13 = os.path.join(root13, "live")
        os.makedirs(r13, exist_ok=True)
        write_skill(l13, "xi", real_body("live body"))
        with open(os.path.join(r13, "xi"), "w", encoding="utf-8") as fh:
            fh.write("/home/shovalbe/.codex/skills/xi\n")
        copy_skill(os.path.join(l13, "xi"), os.path.join(r13, "xi"))
        s = survey(r13, l13, root=root13)
        check(os.path.isdir(os.path.join(r13, "xi")) and not s["squat_repo"]
              and s["same"] == ["xi"],
              "importing over a squatting file leaves a real directory in sync")

        # --- case 14: CRLF-vs-LF is not drift, and is not silence either -----
        # Measured 2026-08-05: of the 21 repo-vs-live pairs in the live 55, FOUR
        # differ only in line endings. The live tree is written by Windows and the
        # repo by WSL, so a byte hash reports a file that is character-identical as
        # needing a decision. That is the allowed-list-from-a-sample failure this
        # repo has now logged three times: the oracle rejects a legitimate form.
        #
        # Both halves matter. Counting it as drift inflates the number a gate would
        # enforce. Counting it as "same" hides a real deployment asymmetry. So it
        # gets its own bucket, and this case pins BOTH: eol_only is populated, and
        # drift stays empty, and a genuine content change still lands in drift.
        root14 = os.path.join(tmp, "c14")
        r14 = os.path.join(root14, "repo")
        l14 = os.path.join(root14, "live")
        write_skill(r14, "omicron", real_body("shared"))
        write_skill(l14, "omicron", real_body("shared"))
        p14 = os.path.join(l14, "omicron", "SKILL.md")
        with open(p14, "rb") as fh:
            lf = fh.read()
        with open(p14, "wb") as fh:                       # same characters, CRLF
            fh.write(lf.replace(b"\n", b"\r\n"))
        s = survey(r14, l14, root=root14)
        check(lf != open(p14, "rb").read(),
              "the CRLF fixture really does differ in bytes")
        check([x[0] for x in s.get("eol_only", [])] == ["omicron"]
              and not s["drift"] and s["same"] == [],
              "a CRLF/LF pair is reported as line-endings-only, not as drift")

        write_skill(l14, "pi", real_body("live text"))
        write_skill(r14, "pi", real_body("repo text"))
        s = survey(r14, l14, root=root14)
        check([x[0] for x in s["drift"]] == ["pi"],
              "a real content difference is still drift after the EOL fix")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fails:
        print("{} check(s) FAILED".format(len(fails)))
        return 1
    print("all checks passed")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("check")
    c.add_argument("--strict", action="store_true",
                   help="hollow skills also fail")
    c.set_defaults(fn=cmd_check)

    d = sub.add_parser("deploy")
    d.add_argument("--apply", action="store_true")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--include-drift", action="store_true",
                   help="also overwrite live copies that differ from the repo")
    d.set_defaults(fn=cmd_deploy)

    i = sub.add_parser("import")
    i.add_argument("--apply", action="store_true")
    i.add_argument("--dry-run", action="store_true")
    i.set_defaults(fn=cmd_import)

    s = sub.add_parser("selftest")
    s.set_defaults(fn=cmd_selftest)

    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
