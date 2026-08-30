#!/usr/bin/env python3
"""Verify state/*.jsonl ledgers are only ever appended to, never rewritten.

WHY THIS EXISTS

The convention that `state/*.jsonl` files are append-only ledgers is written
in AGENTS.md and assumed by the bus hash-chain, the gate ledger, and every
lessons/claims row. Nothing checked it. EXT-1 (TODO.md, 2026-08-17): a
grep-level audit that closes that gap, following the same pattern the
deepseek-harness comparison names (docs/analysis/2026-08-17-external-landscape
-comparison.md): the request log is append-only and reconstructible;
corrections are rows, never rewrites.

WHAT IT CHECKS

1. Static scan: every writer under tools/ and dot-claude/hooks that opens a
   path matching state/*.jsonl is inspected for a truncating mode ("w", "w+",
   "x", or a bare open() default-write) or a seek(0) + truncate() pattern.
   Only "a" / "a+" (append) modes are allowed for a jsonl ledger path.
2. History check: for every TRACKED state/*.jsonl file, the working-tree line
   count must be >= the line count at HEAD. A ledger can only grow or stay the
   same between HEAD and the working tree; a smaller count means a row was
   removed, which is only legitimate as an explicit, reviewed commit (this
   check runs on the working tree, so a committed shrink is visible in that
   commit's diff, not silently passed here).

WHAT IT DOES NOT DO

It cannot prove an in-place row EDIT that keeps the same line count (e.g. sed
-i rewriting line 3 without adding or removing lines). That needs a content
hash per line kept elsewhere, which is future work, not this oracle's job.
This is a coverage gap, not a false confidence: it is stated here so nobody
reads a PASS as "no row was ever altered."
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HIGH, MED = "high", "medium"
SEV_ORDER = {HIGH: 2, MED: 1}

# A writer that touches a state/*.jsonl path. Matches open(...) calls and
# Path(...).write_text/open wrappers naming a literal state/...jsonl target.
STATE_JSONL = re.compile(r"""state[/\\][^"'\s]*\.jsonl""")

# open(<path>, "w"...) / "w+" / "x" / "x+": any of these truncate or refuse
# to append, so any one of them against a state/*.jsonl path is a finding.
TRUNCATING_OPEN = re.compile(
    r"""open\s*\([^)]*?["'](?P<mode>w\+?|x\+?)["']"""
)

# Path(...).write_text(...) always truncates; there is no append mode for it.
WRITE_TEXT = re.compile(r"""\.write_text\s*\(""")

# seek(0) followed (within a short window) by truncate() is the manual
# rewrite-in-place idiom this check also has to catch even when the file was
# opened in "r+" (which is not truncating on open() itself).
SEEK_TRUNCATE = re.compile(r"""seek\s*\(\s*0\s*\)[\s\S]{0,200}?truncate\s*\(""")

SCAN_ROOTS = ("tools", "dot-claude/hooks")
SCAN_SUFFIXES = (".py", ".sh")

# This oracle's own source is exempt from its own scan: its docstring and
# regex literals name state/*.jsonl and the very patterns ("w", seek+truncate)
# it exists to detect, which are data describing the check, not a writer.
SELF_EXEMPT = {"tools/audit/append_only.py"}


def _iter_source_files(project: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = project / root_name
        if not root.is_dir():
            continue
        files.extend(
            path for path in root.rglob("*")
            if (path.is_file() and path.suffix in SCAN_SUFFIXES
                and path.relative_to(project).as_posix() not in SELF_EXEMPT))
    return files


def scan_static(project: Path) -> list[dict]:
    """Find writers that open a state/*.jsonl path in a truncating mode."""
    findings: list[dict] = []
    for path in _iter_source_files(project):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not STATE_JSONL.search(text):
            continue
        rel = path.relative_to(project).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not STATE_JSONL.search(line) and not SEEK_TRUNCATE.search(text):
                continue
            m = TRUNCATING_OPEN.search(line)
            if m and STATE_JSONL.search(line):
                findings.append({
                    "file": rel, "line": lineno, "kind": "truncating-open",
                    "mode": m.group("mode"), "severity": HIGH,
                    "note": "open() on a state/*.jsonl path uses mode "
                            f"'{m.group('mode')}', which truncates or "
                            "refuses to append.",
                })
            if WRITE_TEXT.search(line) and STATE_JSONL.search(line):
                findings.append({
                    "file": rel, "line": lineno, "kind": "write-text",
                    "mode": "write_text", "severity": HIGH,
                    "note": "write_text() on a state/*.jsonl path always "
                            "truncates; there is no append form.",
                })
        # seek(0)+truncate() is checked file-wide since the two calls can be
        # several lines apart (e.g. across a `with` block).
        for m in SEEK_TRUNCATE.finditer(text):
            window_start = text.rfind("\n", 0, m.start())
            lineno = text.count("\n", 0, m.start()) + 1
            window = text[max(0, m.start() - 400):m.end()]
            if STATE_JSONL.search(window):
                findings.append({
                    "file": rel, "line": lineno, "kind": "seek-truncate",
                    "mode": "seek(0)+truncate()", "severity": HIGH,
                    "note": "seek(0) followed by truncate() near a "
                            "state/*.jsonl path is a manual rewrite-in-place.",
                })
    return findings


def run_git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=15, check=False,
    )


def scan_history(project: Path) -> list[dict]:
    """A tracked state/*.jsonl file must not have fewer lines than at HEAD."""
    findings: list[dict] = []
    ls = run_git(project, "ls-files", "state/*.jsonl")
    if ls.returncode != 0:
        return findings
    for rel in (line.strip() for line in ls.stdout.splitlines() if line.strip()):
        working = project / rel
        if not working.is_file():
            continue
        head = run_git(project, "show", f"HEAD:{rel}")
        if head.returncode != 0:
            continue  # not committed yet, nothing to compare
        head_lines = len([ln for ln in head.stdout.splitlines() if ln.strip()])
        try:
            working_lines = len([
                ln for ln in working.read_text(encoding="utf-8", errors="replace")
                .splitlines() if ln.strip()
            ])
        except OSError:
            continue
        if working_lines < head_lines:
            findings.append({
                "file": rel, "line": 0, "kind": "shrunk-ledger",
                "mode": "history", "severity": HIGH,
                "note": f"{rel} has {working_lines} lines in the working tree "
                        f"but {head_lines} at HEAD; a ledger must only grow.",
            })
    return findings


def report(findings: list[dict]) -> None:
    if not findings:
        print("No append-only violations found.")
        return
    for f in findings:
        print(f"  [{f['severity'].upper():6}] {f['file']}:{f['line']}  "
              f"{f['kind']} ({f['mode']})  {f['note']}")


def cmd_check(a: argparse.Namespace) -> int:
    project = Path(a.project).resolve()
    findings = scan_static(project) + (scan_history(project) if not a.no_history else [])
    report(findings)
    worst = max([SEV_ORDER[f["severity"]] for f in findings], default=0)
    verdict = "PASS" if worst == 0 else "FAIL"
    print(f"\nVERDICT: {verdict} ({len(findings)} finding(s))")
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
        (project / "tools" / "audit").mkdir(parents=True)
        (project / "state").mkdir()

        # a real append-only writer: must NOT be reported
        (project / "tools" / "audit" / "good_writer.py").write_text(
            'with open("state/lessons.jsonl", "a") as f:\n    f.write(row)\n',
            encoding="utf-8",
        )

        # a planted truncating writer: must go red
        bad = project / "tools" / "audit" / "bad_writer.py"
        bad.write_text(
            'def rewrite():\n'
            '    with open("state/lessons.jsonl", "w") as f:\n'
            '        f.write(rebuilt)\n',
            encoding="utf-8",
        )

        # a planted seek+truncate rewrite: must also go red
        bad2 = project / "tools" / "audit" / "bad_writer2.py"
        bad2.write_text(
            'def patch():\n'
            '    f = open("state/claims.jsonl", "r+")\n'
            '    f.seek(0)\n'
            '    f.truncate()\n'
            '    f.write(new_content)\n',
            encoding="utf-8",
        )

        findings = scan_static(project)
        kinds = {f["kind"] for f in findings}
        files_hit = {f["file"] for f in findings}

        check("a truncating open() on a ledger is caught",
              any("bad_writer.py" in f for f in files_hit) and "truncating-open" in kinds,
              json.dumps(findings, indent=1))
        check("a seek(0)+truncate() rewrite is caught",
              any("bad_writer2.py" in f for f in files_hit) and "seek-truncate" in kinds,
              json.dumps(findings, indent=1))
        check("an append-mode writer is left alone",
              not any("good_writer.py" in f for f in files_hit),
              json.dumps(findings, indent=1))

        args = argparse.Namespace(project=str(project), no_history=True)
        check("cmd_check fails when a truncating writer is present",
              cmd_check(args) == 1)

        bad.unlink()
        bad2.unlink()
        args = argparse.Namespace(project=str(project), no_history=True)
        check("cmd_check passes once truncating writers are removed",
              cmd_check(args) == 0)

    # history check: run against THIS repo's own git history as a smoke,
    # since a synthetic git repo is unnecessary ceremony for one comparison.
    real_project = Path(__file__).resolve().parents[2]
    history_findings = scan_history(real_project)
    check("history check runs clean against this repo's tracked ledgers",
          history_findings == [], json.dumps(history_findings, indent=1))

    print("\nVERDICT: {}".format(
        "planted truncating writers are detected and real writers are left alone"
        if rc == 0 else "selftest has failures above"))
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="scan for append-only violations")
    p_check.add_argument("--project", default=".")
    p_check.add_argument("--no-history", action="store_true",
                          help="skip the git-history line-count comparison")
    p_check.set_defaults(func=cmd_check)

    p_self = sub.add_parser("selftest", help="plant violations, verify detection")
    p_self.set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
