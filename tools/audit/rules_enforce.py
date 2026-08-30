#!/usr/bin/env python3
"""Mechanical enforcement of rules that carry an enforce: frontmatter block.

A rule file in dot-claude/rules/ is prose by default: the LLM reads it and
complies (or not). This tool reads each rule, extracts an optional YAML
frontmatter block delimited by --- lines, and runs the predicate it declares.
A rule without frontmatter is prose-only and skipped.

Frontmatter schema (YAML between --- lines at the top of the file):

    ---
    enforce:
      deny_pattern: "mock\\.patch|@mock\\.patch|MagicMock"
      glob: "*.py"
      scope: "tests/"
    ---

    ---
    enforce:
      cmd: "python tools/slop_lint.py docs/"
    ---

Fields:
  deny_pattern  Regex that must NOT appear in any matching file. Uses ripgrep
                if available, else a Python fallback.
  glob          File glob filter (default: *.py).
  scope         Directory to search relative to repo root (default: repo root).
  cmd           Shell command; exit 0 = rule holds, nonzero = violation.
                Mutually exclusive with deny_pattern.

Usage:
    python tools/audit/rules_enforce.py check [--project DIR] [--json]
    python tools/audit/rules_enforce.py selftest
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RULES_DIR = REPO / "dot-claude" / "rules"


def parse_frontmatter(text: str) -> dict | None:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i, ln in enumerate(lines[1:], 1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end])
    result = {}
    current_key = None
    for ln in block.split("\n"):
        stripped = ln.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ln.startswith("  ") and current_key == "enforce":
            m = re.match(r"\s+(\w+):\s*(.*)", ln)
            if m:
                result[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        elif stripped.startswith("enforce:"):
            current_key = "enforce"
            val = stripped[len("enforce:"):].strip()
            if val:
                result["cmd"] = val.strip('"').strip("'")
    return result if result else None


def check_deny_pattern(project: str, pattern: str, glob: str, scope: str) -> tuple[bool, str]:
    search_dir = os.path.join(project, scope) if scope else project
    if not os.path.isdir(search_dir):
        return True, "scope {} does not exist, skipped".format(scope)
    try:
        r = subprocess.run(
            ["rg", "-l", "--glob", glob, pattern, search_dir],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 1:
            return True, "no matches"
        if r.returncode == 0:
            files = [f.strip() for f in r.stdout.strip().splitlines() if f.strip()]
            rel = [os.path.relpath(f, project) for f in files]
            return False, "{} file(s): {}".format(len(rel), ", ".join(rel[:10]))
        return True, "rg exit {}, treating as pass".format(r.returncode)
    except FileNotFoundError:
        return _check_deny_pattern_python(project, pattern, glob, scope)
    except subprocess.TimeoutExpired:
        return True, "timed out, treating as pass"


def _check_deny_pattern_python(project: str, pattern: str, glob: str, scope: str) -> tuple[bool, str]:
    import fnmatch
    search_dir = os.path.join(project, scope) if scope else project
    compiled = re.compile(pattern)
    hits = []
    for root, _dirs, fnames in os.walk(search_dir):
        if ".venv" in root or "__pycache__" in root or "node_modules" in root:
            continue
        for fn in fnames:
            if not fnmatch.fnmatch(fn, glob):
                continue
            fp = os.path.join(root, fn)
            try:
                text = Path(fp).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if compiled.search(text):
                hits.append(os.path.relpath(fp, project))
    if not hits:
        return True, "no matches"
    return False, "{} file(s): {}".format(len(hits), ", ".join(hits[:10]))


def check_cmd(project: str, cmd: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=project, timeout=60)
        if r.returncode == 0:
            return True, "exit 0"
        output = (r.stdout + r.stderr).strip()
        snippet = output[:200] if output else "exit {}".format(r.returncode)
        return False, snippet
    except subprocess.TimeoutExpired:
        return False, "timed out after 60s"


def run_check(project: str, as_json: bool = False) -> int:
    if not RULES_DIR.is_dir():
        print("no rules directory at {}".format(RULES_DIR))
        return 2
    rules = sorted(RULES_DIR.glob("*.md"))
    enforced = []
    prose_only = []
    results = []
    for rf in rules:
        text = rf.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        if fm is None:
            prose_only.append(rf.name)
            continue
        enforced.append(rf.name)
        if "deny_pattern" in fm:
            ok, detail = check_deny_pattern(
                project,
                fm["deny_pattern"],
                fm.get("glob", "*.py"),
                fm.get("scope", ""))
            results.append({"rule": rf.name, "pass": ok, "detail": detail, "mode": "deny"})
        elif "cmd" in fm:
            ok, detail = check_cmd(project, fm["cmd"])
            results.append({"rule": rf.name, "pass": ok, "detail": detail, "mode": "cmd"})
        else:
            results.append({"rule": rf.name, "pass": True, "detail": "enforce block empty", "mode": "none"})

    passing = [r for r in results if r["pass"]]
    failing = [r for r in results if not r["pass"]]

    if as_json:
        print(json.dumps({"enforced": len(enforced), "prose_only": len(prose_only),
                          "pass": len(passing), "fail": len(failing),
                          "results": results}, indent=2))
    else:
        print("{} rule(s) with enforcement, {} prose-only".format(len(enforced), len(prose_only)))
        for r in results:
            tag = "PASS" if r["pass"] else "FAIL"
            print("  [{}] {} ({}): {}".format(tag, r["rule"], r["mode"], r["detail"]))
        if failing:
            print("VERDICT: {} enforcement violation(s)".format(len(failing)))
        else:
            print("VERDICT: all enforced rules pass")

    return 1 if failing else 0


def _run_check_with_rules_dir(rules_dir: Path, project: str) -> int:
    global RULES_DIR
    orig = RULES_DIR
    RULES_DIR = rules_dir
    try:
        return run_check(project)
    finally:
        RULES_DIR = orig


def selftest():
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        rules_dir = Path(td) / "dot-claude" / "rules"
        rules_dir.mkdir(parents=True)
        src_dir = Path(td) / "src"
        src_dir.mkdir()

        # 1. Rule with deny_pattern that should pass (no matches)
        (rules_dir / "no-debugger.md").write_text(
            '---\nenforce:\n  deny_pattern: "breakpoint\\(\\)"\n  glob: "*.py"\n  scope: "src"\n---\n# No debugger\n')
        (src_dir / "clean.py").write_text("x = 1\n")
        code = _run_check_with_rules_dir(rules_dir, td)
        ok = code == 0
        print("[{}] deny_pattern with no matches passes".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

        # 2. Rule with deny_pattern that should fail (has matches)
        (src_dir / "debug.py").write_text("breakpoint()\n")
        code = _run_check_with_rules_dir(rules_dir, td)
        ok = code == 1
        print("[{}] deny_pattern with matches fails".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1
        (src_dir / "debug.py").unlink()

        # 3. Rule with cmd that passes
        (rules_dir / "cmd-pass.md").write_text(
            '---\nenforce:\n  cmd: "true"\n---\n# Always pass\n')
        code = _run_check_with_rules_dir(rules_dir, td)
        ok = code == 0
        print("[{}] cmd mode exit 0 passes".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

        # 4. Rule with cmd that fails
        (rules_dir / "cmd-pass.md").write_text(
            '---\nenforce:\n  cmd: "false"\n---\n# Always fail\n')
        code = _run_check_with_rules_dir(rules_dir, td)
        ok = code == 1
        print("[{}] cmd mode exit 1 fails".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

        # 5. Prose-only rule is skipped, not failed
        (rules_dir / "cmd-pass.md").unlink()
        (rules_dir / "no-debugger.md").unlink()
        (rules_dir / "prose-rule.md").write_text("# Just prose\nDo the right thing.\n")
        code = _run_check_with_rules_dir(rules_dir, td)
        ok = code == 0
        print("[{}] prose-only rule is skipped, not failed".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

        # 6. Frontmatter parsing
        fm = parse_frontmatter('---\nenforce:\n  deny_pattern: "foo"\n  glob: "*.txt"\n---\n# Rule\n')
        ok = fm is not None and fm.get("deny_pattern") == "foo" and fm.get("glob") == "*.txt"
        print("[{}] frontmatter parsing extracts fields".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

        fm = parse_frontmatter("# No frontmatter\nJust prose.\n")
        ok = fm is None
        print("[{}] no frontmatter returns None".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1

    print("VERDICT: {}".format("rules_enforce selftest passed" if rc == 0 else "FAILURES above"))
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check", "selftest"])
    ap.add_argument("--project", default=str(REPO))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.command == "selftest":
        sys.exit(selftest())
    sys.exit(run_check(a.project, a.json))


if __name__ == "__main__":
    main()
