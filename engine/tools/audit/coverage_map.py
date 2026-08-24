#!/usr/bin/env python3
"""Fail CLOSED on a top-level directory with no declared gate coverage.

WHY THIS EXISTS

External review (Agentica) independently converged on the DASH-1 finding this
audit already made: dashboard/ landed 39 source files and had zero domain
coverage in quality-contract.json or ship-gate.yml for two days before a
manual audit caught it. That is a class of gap, not a one-off: the same run
that built this checker found a SECOND live instance, nexus-engine-rs (a
second Rust crate, 8 #[test] functions, its own README documenting `cargo
test`, wired into nothing).

Every other coverage mechanism in this repo defaults to "unlisted is fine":
docs/prior-art/out-of-scope.txt says explicitly "a prefix not listed here is
IN scope" (meaning: audited by default). That default is correct for prior
art, where a missing record is a loud, individually-visible FAIL per
component. It is the wrong default for directory-level gate coverage, because
a whole new top-level tree can exist, compile, and pass its own local tests
forever without ANY of the fixed domains (build/unit/types/...) ever walking
into it, and nothing before this file said so out loud.

So this file inverts the default: docs/coverage-map.txt must carry a row for
EVERY top-level tracked directory. A directory with no row is UNKNOWN, and
UNKNOWN blocks the gate, exactly like gate.py's own UNCOVERED status for a
domain nobody configured (tools/gate/gate.py's own docstring: "there is no
state in which the gate passes because nobody got round to configuring a
check"). This is that same rule, one level up: applied to which DIRECTORIES a
domain even looks at, not just whether a domain's own command exits zero.

UNIT OF COVERAGE

Top-level only. dashboard/core, dashboard/web and dashboard/src-tauri are
three different toolchains under one directory and get ONE row, because the
failure this file exists to close is "a new top-level tree appears with zero
domains touching it", not "every subdirectory is individually accounted for"
(docs/dir-purpose.txt + codemap.py already own that finer granularity, and
duplicating it here would be a second copy of the same fact drifting on its
own schedule).

WHAT A ROW CAN SAY

  path | covered-by:<domain> | reason    domain must be a real quality-
                                          contract.json domain name; a typo is
                                          caught the same run it is written
  path | exempt | reason                 not source code, or a named,
                                          admitted gap (see nexus-engine-rs's
                                          row: an exemption can HONESTLY say
                                          "this is a known hole", which is
                                          different from silently passing)

WHAT THIS DOES NOT DO

It does not verify the covered-by claim is TRUE (that the named domain's cmd
actually reaches into that directory's files). It verifies the claim EXISTS
and names a real domain. A false "covered-by" row is a human writing a lie
into a file that is easy to read and easy to catch in review; a MISSING row
is a silent gap nobody has to lie to create, which is the higher-leverage
failure mode this checker targets first.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

COVERAGE_MAP_PATH = "docs/coverage-map.txt"
CONTRACT_PATH = "quality-contract.json"

# docs/ lives under knowledge/docs/ on disk since the 2026-08-24 top-level
# restructure. Unlike tools/map/codemap.py, this tool has no external test
# file asserting against a bare-docs synthetic fixture (its selftest below
# builds its own tempdir from scratch), so the constant itself is safe to
# repoint rather than needing a codemap.py-style fs_path() split.
COVERAGE_MAP_PATH = "knowledge/" + COVERAGE_MAP_PATH


def tracked_top_level_dirs(project: Path) -> list[str]:
    """Every top-level TRACKED directory, in git's own path encoding.

    Mirrors tools/map/codemap.py's tracked(): git ls-files -z, not newline
    splitting, so a path git would C-quote (a non-ASCII top-level name) does
    not arrive wrapped in literal quote characters and become a phantom
    entry nothing can ever satisfy. -z turns that quoting off at the source.
    """
    p = subprocess.run(
        ["git", "ls-files", "-z"], cwd=project, shell=False,
        capture_output=True, timeout=120,
    )
    if p.returncode != 0:
        return []
    out = p.stdout.decode("utf-8", "replace")
    tops: set[str] = set()
    for rel in (x for x in out.split("\0") if x):
        if "/" in rel:
            tops.add(rel.split("/", 1)[0])
    return sorted(tops)


def read_coverage_map(project: Path) -> dict[str, tuple[str, str, str]]:
    """path -> (kind, domain-or-empty, reason). kind is 'covered' or 'exempt'."""
    rows: dict[str, tuple[str, str, str]] = {}
    path = project / COVERAGE_MAP_PATH
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 3:
            continue
        entry_path, kind_field, reason = parts
        if not entry_path or not reason:
            continue
        if kind_field.startswith("covered-by:"):
            rows[entry_path] = ("covered", kind_field[len("covered-by:"):].strip(), reason)
        elif kind_field == "exempt":
            rows[entry_path] = ("exempt", "", reason)
        # any other kind_field is malformed and simply not recorded, so the
        # directory reads as having no row at all (fails closed, not silently
        # accepted as some third state).
    return rows


def read_contract_domains(project: Path) -> set[str]:
    path = project / CONTRACT_PATH
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return set()
    return set((data.get("domains") or {}).keys())


def evaluate(project: Path) -> dict:
    """Return {'ok': [...], 'undeclared': [...], 'bad_domain': [...]}."""
    tops = tracked_top_level_dirs(project)
    rows = read_coverage_map(project)
    domains = read_contract_domains(project)

    ok: list[dict] = []
    undeclared: list[str] = []
    bad_domain: list[dict] = []

    for d in tops:
        if d not in rows:
            undeclared.append(d)
            continue
        kind, domain, reason = rows[d]
        if kind == "covered" and domain not in domains:
            bad_domain.append({"path": d, "domain": domain, "reason": reason})
            continue
        ok.append({"path": d, "kind": kind, "domain": domain, "reason": reason})

    return {"ok": ok, "undeclared": undeclared, "bad_domain": bad_domain}


def cmd_check(a: argparse.Namespace) -> int:
    project = Path(a.project).resolve()
    result = evaluate(project)

    print(f"{len(result['ok'])} top-level director(y/ies) declared "
          f"({sum(1 for r in result['ok'] if r['kind'] == 'covered')} covered, "
          f"{sum(1 for r in result['ok'] if r['kind'] == 'exempt')} exempt)")

    if result["undeclared"]:
        print("\nUNDECLARED (no row in {}, fails closed):".format(COVERAGE_MAP_PATH))
        for d in result["undeclared"]:
            print(f"  [FAIL] {d}  -- add a 'covered-by:<domain>' or 'exempt' row")

    if result["bad_domain"]:
        print("\nBAD DOMAIN NAME (row names a domain not in {}):".format(CONTRACT_PATH))
        for r in result["bad_domain"]:
            print(f"  [FAIL] {r['path']}  covered-by:{r['domain']!r} -- no such domain")

    n_fail = len(result["undeclared"]) + len(result["bad_domain"])
    verdict = "PASS" if n_fail == 0 else "FAIL"
    print(f"\nVERDICT: {verdict} ({n_fail} undeclared/invalid top-level director(y/ies))")
    return 0 if verdict == "PASS" else 1


def cmd_selftest(_a: argparse.Namespace) -> int:
    rc = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal rc
        print("  {}  {}".format("ok  " if ok else "MISS", label))
        if detail and not ok:
            print("        " + detail[:400])
        if not ok:
            rc = 1

    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=project, check=True)

        (project / "covered_dir").mkdir()
        (project / "covered_dir" / "f.py").write_text("x = 1\n", encoding="utf-8")
        (project / "exempt_dir").mkdir()
        (project / "exempt_dir" / "notes.md").write_text("n\n", encoding="utf-8")
        (project / "fresh_uncovered_dir").mkdir()
        (project / "fresh_uncovered_dir" / "new_code.py").write_text("y = 2\n", encoding="utf-8")

        (project / CONTRACT_PATH).write_text(json.dumps({
            "domains": {"unit": {"required": True, "cmd": "true"}}
        }), encoding="utf-8")

        (project / "knowledge" / "docs").mkdir(parents=True)
        # knowledge/ itself becomes a tracked top-level directory the moment the
        # coverage map file is committed under it, so the fixture has to
        # declare knowledge too or the selftest would fail on an artifact of its
        # own setup rather than on the planted gap.
        (project / COVERAGE_MAP_PATH).write_text(
            "covered_dir | covered-by:unit | has real source, unit runs it\n"
            "exempt_dir | exempt | docs only, nothing to run\n"
            "knowledge | exempt | fixture bookkeeping, not part of the planted scenario\n",
            # fresh_uncovered_dir has NO row: this is the planted gap.
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project, check=True)

        result = evaluate(project)
        check("covered_dir resolves as covered",
              any(r["path"] == "covered_dir" and r["kind"] == "covered" for r in result["ok"]),
              json.dumps(result))
        check("exempt_dir resolves as exempt",
              any(r["path"] == "exempt_dir" and r["kind"] == "exempt" for r in result["ok"]),
              json.dumps(result))
        check("a fresh top-level directory with NO row is caught as undeclared "
              "(this is the fail-closed property: a brand-new tree like "
              "dashboard/ on the day it was created)",
              result["undeclared"] == ["fresh_uncovered_dir"], json.dumps(result))

        args = argparse.Namespace(project=str(project))
        check("cmd_check exits 1 while the undeclared directory exists",
              cmd_check(args) == 1)

        # now declare it and prove the check turns green
        with (project / COVERAGE_MAP_PATH).open("a", encoding="utf-8") as f:
            f.write("fresh_uncovered_dir | covered-by:unit | declared after the fact\n")
        args = argparse.Namespace(project=str(project))
        check("cmd_check exits 0 once every top-level directory has a row",
              cmd_check(args) == 0)

        # a row naming a domain that does not exist in the contract must also fail
        (project / COVERAGE_MAP_PATH).write_text(
            "covered_dir | covered-by:no_such_domain | typo'd domain name\n"
            "exempt_dir | exempt | fine\n"
            "fresh_uncovered_dir | exempt | fine\n"
            "knowledge | exempt | fixture bookkeeping\n",
            encoding="utf-8",
        )
        result2 = evaluate(project)
        check("a covered-by row naming a domain absent from quality-contract.json "
              "is caught, not silently trusted",
              any(r["path"] == "covered_dir" for r in result2["bad_domain"]),
              json.dumps(result2))

    print("\nVERDICT: {}".format(
        "a fresh undeclared top-level directory is caught and a declared one passes"
        if rc == 0 else "selftest has failures above"))
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="fail if any top-level directory is undeclared")
    p_check.add_argument("--project", default=".")
    p_check.set_defaults(func=cmd_check)

    p_self = sub.add_parser("selftest", help="plant an undeclared directory, verify detection")
    p_self.set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
