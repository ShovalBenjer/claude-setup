# -*- coding: utf-8 -*-
"""Blast-radius grapher (Claude OS L5/L6, PRD #16). Builds a Python intra-repo
import graph (ast, no deps) and, given a changed file, reports the modules that
import it transitively — the blast radius. Feeds PR-review fanout: a wide radius
=> more reviewers.

Usage:
  blast_radius.py <repo_dir>                 # print graph summary
  blast_radius.py <repo_dir> --changed a.py  # print blast radius of a.py
"""
import argparse
import ast
import os
import pathlib
import sys
from collections import defaultdict


def module_name(root, path):
    rel = os.path.relpath(path, root).replace("\\", "/")
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else rel


def build(root):
    root = os.path.abspath(root)
    files = [str(p) for p in pathlib.Path(root).rglob("*.py")
             if ".venv" not in str(p) and "__pycache__" not in str(p) and "node_modules" not in str(p)]
    mods = {module_name(root, f): f for f in files}
    local_tops = {m.split(".")[0] for m in mods}
    # basename -> list of full module names (for sys.path.insert style imports)
    by_basename = defaultdict(list)
    for m in mods:
        by_basename[m.rsplit(".", 1)[-1]].append(m)
    imports = defaultdict(set)
    for m, f in mods.items():
        try:
            tree = ast.parse(pathlib.Path(f).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        m_dir = os.path.dirname(f)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                matched = None
                base = n.split(".")[0]
                if base in local_tops:
                    for cand in mods:
                        if cand == n or cand.endswith("." + n):
                            matched = cand
                            break
                if not matched and n in by_basename:
                    candidates = by_basename[n]
                    # prefer sibling (same directory) over distant match
                    for cand in candidates:
                        if os.path.dirname(mods[cand]) == m_dir:
                            matched = cand
                            break
                    if not matched:
                        matched = candidates[0]
                if matched and matched != m:
                    imports[m].add(matched)
    return mods, imports


def reverse_deps(imports, target_mod):
    """Modules that import target_mod transitively."""
    rev = defaultdict(set)
    for m, deps in imports.items():
        for d in deps:
            rev[d].add(m)
    seen, stack = set(), [target_mod]
    while stack:
        cur = stack.pop()
        for importer in rev.get(cur, ()):
            if importer not in seen:
                seen.add(importer); stack.append(importer)
    return seen


def selftest():
    import tempfile
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        pathlib.Path(td, "lib.py").write_text("X = 1\n")
        pathlib.Path(td, "core.py").write_text("import lib\n")
        pathlib.Path(td, "app.py").write_text("import core\n")
        mods, imports = build(td)
        ok = len(mods) == 3 and sum(len(v) for v in imports.values()) == 2
        print("[{}] 3-module chain has 2 edges".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1
        radius = reverse_deps(imports, "lib")
        ok = radius == {"core", "app"}
        print("[{}] blast radius of lib is core + app, got {}".format(
            "ok  " if ok else "FAIL", radius))
        rc |= 0 if ok else 1
        radius = reverse_deps(imports, "app")
        ok = len(radius) == 0
        print("[{}] blast radius of leaf (app) is empty".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1
        pathlib.Path(td, "sub").mkdir()
        pathlib.Path(td, "sub", "deep.py").write_text("import lib\n")
        mods, imports = build(td)
        ok = "sub.deep" in mods and "lib" in imports.get("sub.deep", set())
        print("[{}] subdirectory import resolves by basename".format("ok  " if ok else "FAIL"))
        rc |= 0 if ok else 1
    print("VERDICT: {}".format("blast_radius selftest passed" if rc == 0 else "FAILURES above"))
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?")
    ap.add_argument("--changed")
    ap.add_argument("command", nargs="?")
    a = ap.parse_args()
    if a.command == "selftest" or (a.repo == "selftest"):
        sys.exit(selftest())
    if not a.repo:
        ap.print_help()
        sys.exit(2)
    mods, imports = build(a.repo)
    edges = sum(len(v) for v in imports.values())
    print(f"modules: {len(mods)} | import edges: {edges}")
    if a.changed:
        tgt = module_name(os.path.abspath(a.repo), os.path.abspath(a.changed))
        radius = reverse_deps(imports, tgt)
        print(f"blast radius of {tgt}: {len(radius)} module(s)")
        for m in sorted(radius):
            print(f"  <- {m}")
        if len(radius) >= 3:
            print("WIDE radius -> fan out more reviewers (PR-fabric signal).")
    else:
        top = sorted(imports.items(), key=lambda kv: -len(kv[1]))[:5]
        for m, deps in top:
            print(f"  {m} imports {len(deps)} local module(s)")


if __name__ == "__main__":
    main()
