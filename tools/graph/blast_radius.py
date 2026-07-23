# -*- coding: utf-8 -*-
"""Blast-radius grapher (Claude OS L5/L6, PRD #16). Builds a Python intra-repo
import graph (ast, no deps) and, given a changed file, reports the modules that
import it transitively — the blast radius. Feeds PR-review fanout: a wide radius
=> more reviewers.

Usage:
  blast_radius.py <repo_dir>                 # print graph summary
  blast_radius.py <repo_dir> --changed a.py  # print blast radius of a.py
"""
import ast, os, sys, argparse, pathlib
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
    # edges: module -> set(local modules it imports)
    imports = defaultdict(set)
    for m, f in mods.items():
        try:
            tree = ast.parse(pathlib.Path(f).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n.split(".")[0] in local_tops:
                    # match to the closest known local module
                    for cand in mods:
                        if cand == n or cand.endswith("." + n) or cand.split(".")[-1] == n.split(".")[-1]:
                            imports[m].add(cand)
                            break
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--changed")
    a = ap.parse_args()
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
