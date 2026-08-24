#!/usr/bin/env python3
"""The seven verifiers that used PowerShell built-ins, rewritten to run on both hosts.

Why one file and not seven: each of these is two to five lines of logic, and the
PowerShell they replaced was doing nothing Python cannot do on either platform.
Seven near-empty modules would be seven more things to keep in sync. The subcommand
is the claim id, so `state/claims-verify.jsonl` still names exactly what it runs and
a reader can go from a ledger row to the code in one hop.

What was actually wrong with the originals, measured 2026-07-31 on WSL: every one of
them named `$env:USERPROFILE\\claude-setup` or `$env:USERPROFILE\\.claude`. The first
is the WINDOWS clone, which is a different working tree from the one under WSL, so
even with pwsh installed these would have verified the wrong repository. The second
does not exist on Linux at all. So this is not only a shell-portability fix; two of
the seven were pointed at the wrong tree and would have reported on a checkout the
session was not editing.

Anchoring rule used here: the repository is found from THIS FILE's own location, not
from a home directory. A verifier that resolves its target through $HOME checks
whichever clone happens to be under that home, which is the defect above.

Every check prints why it failed. A bare nonzero exit tells the reader a claim died
and nothing about what killed it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HOME = Path.home()


def _fail(msg: str) -> int:
    print(msg)
    return 1


def c002_bus_tracked() -> int:
    """tools/bus/bus.py survives a fresh clone."""
    return _tracked("tools/bus/bus.py")


def c010_refute_tracked() -> int:
    """refute.py survives a fresh clone. A checker that is not in git checks
    nothing for anyone who clones."""
    return _tracked("tools/refute/refute.py")


def _tracked(rel: str) -> int:
    p = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return _fail("%s is untracked: it would not survive a fresh clone" % rel)
    return 0


def c004_agents_on_disk() -> int:
    """At least 23 agent definitions are deployed live."""
    d = HOME / ".claude" / "agents"
    n = len(list(d.glob("*.md"))) if d.is_dir() else 0
    print("agents on disk: %d (%s)" % (n, d))
    return 0 if n >= 23 else _fail("fewer than the 23 imported agents are deployed")


def c005_deploy_script_present() -> int:
    """The repo carries the script that deploys it. Without one, drift between the
    committed payload and the live config is unmanaged rather than merely large."""
    p = ROOT / "payload" / "dot-claude" / "bin" / "deploy-setup.sh"
    if not p.is_file():
        return _fail("payload/dot-claude/bin/deploy-setup.sh absent: repo-to-live drift is unmanaged")
    return 0


def c006_skills_free_of_foreign_home() -> int:
    """No deployed skill still references /home/shovalbe, a path from a different
    machine. Such a skill is a dead pointer that fails open and reports nothing."""
    return _absent_pattern(sorted((HOME / ".claude" / "skills").rglob("*.md")),
                           "/home/shovalbe", "skill files still reference /home/shovalbe")


def c007_global_claude_md_not_routing_to_codex() -> int:
    """ADR-0007 removed Codex. A global CLAUDE.md still naming it as the executor is
    prose that contradicts an accepted decision, which is what ADR-0005 forbids."""
    p = HOME / ".claude" / "CLAUDE.md"
    if not p.is_file():
        print("no ~/.claude/CLAUDE.md on this host; nothing routes to Codex here")
        return 0
    return _absent_pattern([p], "Codex is the executor",
                           "global CLAUDE.md still routes execution to Codex")


def c009_cdp_docs_not_pinned_to_another_machine() -> int:
    """The /cdp docs must not name C:\\Users\\shoval.be, which is a different
    machine's profile."""
    root = HOME / ".claude"
    files = sorted(root.rglob("cdp.md")) if root.is_dir() else []
    return _absent_pattern(files, "shoval.be",
                           "cdp docs reference a different machine's profile")


def _absent_pattern(files, needle: str, msg: str) -> int:
    hits = []
    for f in files:
        try:
            if needle in f.read_text(encoding="utf-8", errors="replace"):
                hits.append(f)
        except OSError:
            continue
    if hits:
        print("%d %s" % (len(hits), msg))
        for h in hits[:5]:
            print("  %s" % h)
        return 1
    print("checked %d file(s), no match for %r" % (len(files), needle))
    return 0


CHECKS = {
    "C-002": c002_bus_tracked,
    "C-004": c004_agents_on_disk,
    "C-005": c005_deploy_script_present,
    "C-006": c006_skills_free_of_foreign_home,
    "C-007": c007_global_claude_md_not_routing_to_codex,
    "C-009": c009_cdp_docs_not_pinned_to_another_machine,
    "C-010": c010_refute_tracked,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in CHECKS:
        print("usage: portable_claims.py <%s>" % "|".join(sorted(CHECKS)), file=sys.stderr)
        return 2
    return CHECKS[argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
