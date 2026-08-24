"""Make public repositories say only things that are true.

Not a cleanup of weak work. Old coursework sitting beside recent infrastructure
is a trajectory and worth keeping visible. What is worth removing is any claim
the code does not support, because a reviewer who opens one and finds it false
stops trusting the rest.

Verified 2026-07-27, each with the command that decided it:

  JSQ-SLQ        `![Build Status](.../build-passing-brightgreen)` is a hardcoded
                 shields.io image, not a workflow badge. The repo's only workflow
                 is Claude Code Review with ZERO runs, so nothing builds.
                 `![License](.../license-MIT-...)` while `gh api` reports
                 license: NONE and no LICENSE blob exists.

  next.py-...    repo topics include `nextjs`; the repo is one 6.6 KB Python file
                 and "next.py" refers to the next() builtin.

Fixes, per repo: delete the claim, or make it true. Never hide the repo.

    python fix_false_claims.py            # show the diff it would make
    python fix_false_claims.py --apply
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

OWNER = "ShovalBenjer"

MIT = """MIT License

Copyright (c) 2026 Shoval Benjer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

FAKE_BUILD_BADGE = "![Build Status](https://img.shields.io/badge/build-passing-brightgreen)\n"


def gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def get_file(repo: str, path: str) -> tuple[str, str] | None:
    rc, out = gh("api", f"repos/{OWNER}/{repo}/contents/{path}")
    if rc != 0:
        return None
    d = json.loads(out)
    return base64.b64decode(d["content"]).decode("utf-8", "replace"), d["sha"]


def put_file(repo: str, path: str, text: str, message: str,
             sha: str | None, branch: str) -> tuple[int, str]:
    args = ["api", "-X", "PUT", f"repos/{OWNER}/{repo}/contents/{path}",
            "-f", f"message={message}",
            "-f", "content=" + base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "-f", f"branch={branch}"]
    if sha:
        args += ["-f", f"sha={sha}"]
    return gh(*args)


def fix_jsq(apply: bool) -> int:
    repo = "JSQ-SLQ"
    rc, branch = gh("api", f"repos/{OWNER}/{repo}", "--jq", ".default_branch")
    got = get_file(repo, "README.md")
    if not got:
        print(f"  {repo}: README unreadable")
        return 1
    text, sha = got

    has_badge = FAKE_BUILD_BADGE in text
    has_lic = get_file(repo, "LICENSE") is not None
    print(f"  {repo}  branch={branch}")
    print(f"     fake build badge present : {has_badge}")
    print(f"     LICENSE present          : {has_lic}  (badge claims MIT)")

    if not apply:
        return 0

    rc_all = 0
    if not has_lic:
        r, out = put_file(repo, "LICENSE", MIT,
                          "Add MIT LICENSE\n\nThe README has claimed an MIT badge "
                          "with no LICENSE file behind it. Making the claim true "
                          "rather than removing the badge.",
                          None, branch)
        print("     LICENSE: " + ("added" if r == 0 else "FAILED " + out[:120]))
        rc_all |= r
    if has_badge:
        new = text.replace(FAKE_BUILD_BADGE, "")
        r, out = put_file(repo, "README.md", new,
                          "Remove the false build-passing badge\n\nIt was a "
                          "hardcoded shields.io image, not a workflow status "
                          "badge. The only workflow here is Claude Code Review "
                          "and it has zero runs, so nothing builds. A green badge "
                          "over no build is the kind of claim that makes a "
                          "reviewer distrust everything else in the repo.",
                          sha, branch)
        print("     build badge: " + ("removed" if r == 0 else "FAILED " + out[:120]))
        rc_all |= r
    return rc_all


def fix_topics(apply: bool) -> int:
    repo = "next.py-solution-campusil"
    rc, out = gh("api", f"repos/{OWNER}/{repo}/topics",
                 "-H", "Accept: application/vnd.github+json", "--jq", ".names")
    if rc != 0:
        print(f"  {repo}: topics unreadable: {out[:120]}")
        return 1
    topics = json.loads(out)
    keep = [t for t in topics if t != "nextjs"]
    print(f"  {repo}")
    print(f"     topics now : {topics}")
    print(f"     topics after: {keep}")
    if not apply or keep == topics:
        return 0
    args = ["api", "-X", "PUT", f"repos/{OWNER}/{repo}/topics",
            "-H", "Accept: application/vnd.github+json"]
    for t in keep:
        args += ["-f", f"names[]={t}"]
    r, out = gh(*args)
    print("     " + ("nextjs topic removed" if r == 0 else "FAILED " + out[:150]))
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rc = fix_jsq(a.apply) | fix_topics(a.apply)
    if not a.apply:
        print("\nPLAN ONLY. Re-run with --apply.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
