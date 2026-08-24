#!/usr/bin/env python3
"""Row 6 of the agentic repo standard: a repository owes a GitHub Project.

The other five rows of docs/standards/agentic-repo-standard.md are facts about
files, and `.alint.yml` checks them directly. This one is a fact about GitHub,
so it is reached through `gh` and wired back into alint as a `command` rule.

The interesting design constraint is failure mode. A checker that errors when
`gh` is missing turns an offline clone into a lint failure, and a lint that
fails for reasons unrelated to the repository is a lint people stop running. So
absence of `gh`, absence of a remote, and an unauthenticated `gh` all report
SKIP and exit 0. Only a repository that demonstrably has a GitHub remote AND a
reachable API AND no linked project fails.

The inverse mistake is worse and is guarded by the selftest: a checker that
exits 0 on every input is indistinguishable from one that works. Every SKIP
path below is asserted to be a SKIP and every FAIL path to be a FAIL.

  python tools/audit/repo_project.py check      exit 1 if a project is owed
  python tools/audit/repo_project.py selftest   plant one defect per guarantee
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

# The operator's cross-repository board, confirmed by `gh project list --owner
# ShovalBenjer` on 2026-07-31. Per-repository projects feed this one; they do
# not replace it.
ZION_OWNER = "ShovalBenjer"
ZION_NUMBER = 3

SKIP, PASS, FAIL = "SKIP", "PASS", "FAIL"

# github.com/<owner>/<repo>, over https, ssh, and git protocol forms, with the
# optional .git suffix. Anchored at the host so a remote merely mentioning
# "github.com" in a path segment does not match.
REMOTE_RE = re.compile(
    r"(?:https://|git://|ssh://git@|git@)github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?$"
)


def parse_remote(url: str):
    """Return (owner, repo) for a GitHub remote, or None for anything else.

    Returning None rather than raising is deliberate: a repository on Azure
    DevOps or with no remote at all is not in violation of a GitHub rule, and
    the caller turns None into SKIP.
    """
    if not url:
        return None
    m = REMOTE_RE.match(url.strip())
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    if not owner or not repo:
        return None
    return owner, repo


def verdict(remote: str, gh_present: bool, gh_ok: bool, projects) -> tuple:
    """Pure decision function. Every branch is exercised by the selftest.

    `projects` is the decoded list of linked projects, or None when it could not
    be determined. None and [] must not collapse: "we could not look" and "we
    looked and there are none" are different claims, and only the second is a
    finding.
    """
    parsed = parse_remote(remote)
    if parsed is None:
        return SKIP, "no GitHub remote; row 6 does not apply"
    owner, repo = parsed
    if not gh_present:
        return SKIP, "gh is not installed; cannot reach the Projects API"
    if not gh_ok:
        return SKIP, "gh is unauthenticated; cannot reach the Projects API"
    if projects is None:
        return SKIP, "the Projects API did not answer"
    if len(projects) == 0:
        return FAIL, "{}/{} has a GitHub remote and no linked Project".format(owner, repo)
    names = ", ".join(str(p.get("title", "?")) for p in projects)
    return PASS, "{}/{} is linked to: {}".format(owner, repo, names)


def _run(args, timeout=30):
    """Return (rc, stdout) and never raise. A checker that dies on a missing
    binary is a checker that reports nothing about the repository.

    `encoding` is pinned to utf-8 with replacement. Without it Python decodes
    child output using the machine's ANSI codepage, which on this operator's
    Windows box is cp1255 (Hebrew). Measured 2026-07-31: `gh auth status` prints
    a U+2713 check mark, cp1255 has no mapping for that byte, and the decode
    raised inside subprocess's reader thread. The rule then reported the
    repository as unauthenticated when gh was in fact logged in, which is the
    exact failure this module's SKIP paths exist to avoid, arriving by a route
    nobody would guess from the rule name.
    """
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout
    except (OSError, ValueError, subprocess.SubprocessError):
        return 127, ""


def cmd_check(_args) -> int:
    rc, remote = _run(["git", "remote", "get-url", "origin"])
    remote = remote if rc == 0 else ""

    gh_rc, _ = _run(["gh", "--version"])
    gh_present = gh_rc == 0
    gh_ok = False
    projects = None
    if gh_present:
        auth_rc, _ = _run(["gh", "auth", "status"])
        gh_ok = auth_rc == 0
    if gh_ok:
        parsed = parse_remote(remote)
        if parsed:
            owner, repo = parsed
            q_rc, out = _run(
                ["gh", "project", "list", "--owner", owner, "--format", "json"], timeout=60
            )
            if q_rc == 0:
                try:
                    projects = json.loads(out).get("projects", [])
                except (ValueError, AttributeError):
                    projects = None

    state, why = verdict(remote, gh_present, gh_ok, projects)
    print("{} {}".format(state, why))
    if state == PASS:
        print("      board of record: Zion, project {} under {}".format(ZION_NUMBER, ZION_OWNER))
    return 1 if state == FAIL else 0


def cmd_selftest(_args) -> int:
    """Plant one defect per guarantee and prove each is caught.

    Every assertion is over a pure function. Nothing here touches git, gh, the
    filesystem, or the network, so this verb is safe to run anywhere, which is
    what lets tools/audit/mutate.py run it.
    """
    rc = 0

    def ok(cond: bool, what: str, detail: str = "") -> None:
        nonlocal rc
        print(("[ok]   " if cond else "[FAIL] ") + what
              + ("  <- {}".format(detail) if not cond and detail else ""))
        if not cond:
            rc = 1

    # parse_remote: the four remote spellings must all resolve to the same pair,
    # because a repo that fails the rule over https and skips it over ssh is a
    # rule that reports on the clone command, not on the repository.
    for url in ("https://github.com/ShovalBenjer/claude-setup.git",
                "https://github.com/ShovalBenjer/claude-setup",
                "git@github.com:ShovalBenjer/claude-setup.git",
                "ssh://git@github.com/ShovalBenjer/claude-setup.git"):
        ok(parse_remote(url) == ("ShovalBenjer", "claude-setup"),
           "remote parses identically over {}".format(url.split(":")[0]), repr(parse_remote(url)))

    # A non-GitHub host must not be coerced into a GitHub owner/repo. This is
    # the estate's real case: several repositories sit on Azure DevOps.
    for url in ("https://dev.azure.com/org/proj/_git/repo",
                "https://gitlab.com/owner/repo.git",
                "https://notgithub.com/a/b", ""):
        ok(parse_remote(url) is None, "a non-GitHub remote does not parse: {!r}".format(url),
           repr(parse_remote(url)))

    # verdict(): the three SKIP paths. Each exists so that an environment
    # problem is never reported as a repository problem.
    gh_remote = "https://github.com/ShovalBenjer/claude-setup.git"
    ok(verdict("", True, True, [])[0] == SKIP, "no remote skips rather than fails")
    ok(verdict(gh_remote, False, False, None)[0] == SKIP, "missing gh skips rather than fails")
    ok(verdict(gh_remote, True, False, None)[0] == SKIP, "unauthenticated gh skips")

    # The distinction the whole module turns on. If these two ever agree, an API
    # outage starts filing violations against every repository at once.
    unknown = verdict(gh_remote, True, True, None)
    empty = verdict(gh_remote, True, True, [])
    ok(unknown[0] == SKIP, "an unanswered API is SKIP, not a finding", unknown[0])
    ok(empty[0] == FAIL, "zero linked projects IS a finding", empty[0])
    ok(unknown[0] != empty[0],
       "'could not look' and 'looked and found none' do not collapse")

    # A passing repository must name the board it found. A PASS that names
    # nothing cannot be distinguished from a PASS that matched the wrong owner.
    good = verdict(gh_remote, True, True, [{"title": "Zion", "number": 3}])
    ok(good[0] == PASS, "a linked project passes", good[0])
    ok("Zion" in good[1], "a passing verdict names the board it found", good[1])

    # The failure message must name the repository. "no project" with no subject
    # is unactionable in a 31-repository sweep.
    ok("claude-setup" in empty[1], "a failing verdict names the repository", empty[1])

    print("\nVERDICT: {}".format(
        "every planted defect is caught" if rc == 0
        else "repo_project selftest has failures above"))
    return rc


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("check", "selftest"):
        print(__doc__)
        return 2
    return {"check": cmd_check, "selftest": cmd_selftest}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
