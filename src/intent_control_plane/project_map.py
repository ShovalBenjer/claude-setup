"""Project-awareness for the harness: map each repo so agents inherit its context.

Deterministic, read-only scan of a projects root. For every repo it surfaces the
dimensions an agent needs before touching it, and the ones that silently rot:
structure class, is-it-an-unmapped-LangGraph-project, repo -> DevOps pipeline ->
Azure resource, the test suites (so none stay "dark"), and whether CI actually gates.

Run: `python -m intent_control_plane.project_map [~/projects]`  (markdown + JSON).
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_SKIP = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache", ".ruff_cache", ".next", "dist", "out"}
_TEST_GLOBS = ("test_*.py", "*_test.py", "*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx", "*.bats")
_DEP_FILES = ("pyproject.toml", "requirements.txt", "requirements.in", "package.json", "uv.lock")
_AZ_KEYS = re.compile(
    r"(?i)(webAppName|appName|functionAppName|containerAppName|resourceGroup|"
    r"azureSubscription|acrName|registry|imageRepository)\s*[:=]\s*['\"]?([A-Za-z0-9._-]+)"
)


def _iter_files(root: Path) -> Iterator[Path]:
    """Yield files under root, pruning skip-dirs BEFORE descending (fast on big repos)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP]
        for name in filenames:
            yield Path(dirpath) / name


def _find_shallow(root: Path, names: set[str], depth: int = 2) -> bool:
    """True if any of `names` exists within `depth` levels (bounded, skip-dir aware)."""
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        d, lvl = stack.pop()
        try:
            for e in d.iterdir():
                if e.is_file() and e.name in names:
                    return True
                if e.is_dir() and lvl < depth and e.name not in _SKIP:
                    stack.append((e, lvl + 1))
        except OSError:
            pass
    return False


def is_agentic_langgraph(root: Path) -> bool:
    """True if the repo DECLARES langgraph/langchain in a dependency file (cheap, accurate)."""
    for dep in _DEP_FILES:
        f = root / dep
        if f.exists():
            try:
                if re.search(r"langgraph|langchain", f.read_text(encoding="utf-8", errors="ignore")):
                    return True
            except OSError:
                continue
    return False


def structure_class(root: Path) -> str:
    """Coarse repo shape, so the right structure standard applies."""
    if is_agentic_langgraph(root):
        return "agentic-langgraph"
    if _find_shallow(root, {"host.json", "function_app.py"}):
        return "azure-function-app"
    if (root / "hooks").is_dir() and (root / "pyproject.toml").exists():
        return "harness-tooling"
    names = {p.name for p in root.iterdir()} if root.is_dir() else set()
    if (root / "package.json").exists() or names & {"admin-spa", "frontend", "web"}:
        return "web-frontend"
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        return "python-service-or-lib"
    return "unclassified"


def azure_targets(root: Path) -> list[str]:
    """Azure resource names referenced by pipelines/bicep: the repo -> resource mapping."""
    found: set[str] = set()
    for p in _iter_files(root):
        if p.name.startswith("azure-pipelines") or p.suffix == ".bicep":
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for _, val in _AZ_KEYS.findall(text):
                if val and val not in {"true", "false"}:
                    found.add(val)
    return sorted(found)[:12]


def discover_test_suites(root: Path) -> dict[str, Any]:
    """Discover test files + runner in one walk, so no suite stays dark."""
    counts: dict[str, int] = {}
    for p in _iter_files(root):
        for glob in _TEST_GLOBS:
            if p.match(glob):
                counts[glob] = counts.get(glob, 0) + 1
                break
    runner = None
    pyproject = root / "pyproject.toml"
    package = root / "package.json"
    if pyproject.exists() and "pytest" in pyproject.read_text(errors="ignore"):
        runner = "pytest"
    elif package.exists() and '"test"' in package.read_text(errors="ignore"):
        runner = "bun/npm test"
    return {"files": sum(counts.values()), "by_pattern": counts, "runner": runner}


def ci_state(root: Path) -> dict[str, Any]:
    """Pipeline presence + whether gates are advisory (|| true) rather than blocking."""
    pipes = [p.name for p in root.glob("azure-pipelines*.y*ml")]
    advisory = False
    for name in pipes:
        try:
            if "|| true" in (root / name).read_text(errors="ignore"):
                advisory = True
        except OSError:
            pass
    return {"pipelines": pipes, "has_ci": bool(pipes), "advisory_gates": advisory}


def python_imports(source: str) -> list[str]:
    """Pure: imported module paths from Python source.

    Absolute imports keep their dotted path (`import a.b` and `from a.b import c` -> 'a.b').
    Relative imports keep their leading dots so a caller can tell they are package-internal
    (`from .core import x` -> '.core', `from . import core` -> '.core', `from ..pkg import x`
    -> '..pkg'). Returns [] on a syntax error rather than raising, so one unparseable file
    never aborts a whole-repo scan.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            if node.module:
                mods.append(prefix + node.module)
            elif node.level:
                mods.extend(prefix + alias.name for alias in node.names)
    return mods


def python_import_graph(root: Path) -> dict[str, Any]:
    """Internal Python import graph for a repo: module count, internal edges, and the hub.

    A real ast-parsed graph, not a regex classifier. An import is 'internal' when it is
    relative, or its top component names a local package (a dir with __init__.py); matching
    the top component to a package (not just any basename) stops a stdlib import from being
    miscounted when a local file happens to share the name. The edge target is the module's
    last component. The hub is the local module with the highest internal in-degree: the
    architectural center an agent should read first. Bounded (parses at most 2000 files, with
    the cap applied during the walk so a huge repo is never fully materialized).
    """
    py_paths: list[Path] = []
    top_packages: set[str] = set()
    local_stems: set[str] = set()
    for p in _iter_files(root):
        if p.suffix != ".py":
            continue
        if len(py_paths) < 2000:
            py_paths.append(p)
        if p.name == "__init__.py":
            top_packages.add(p.parent.name)
        else:
            local_stems.add(p.stem)
    indegree: dict[str, int] = {}
    edges = 0
    modules = 0
    for p in py_paths:
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        modules += 1
        for mod in python_imports(src):
            relative = mod.startswith(".")
            clean = mod.lstrip(".")
            if not clean:
                continue
            top = clean.split(".")[0]
            last = clean.split(".")[-1]
            if (relative or top in top_packages) and last in local_stems:
                indegree[last] = indegree.get(last, 0) + 1
                edges += 1
    hub = max(indegree, key=lambda name: indegree[name]) if indegree else None
    return {
        "py_modules": modules,
        "internal_import_edges": edges,
        "hub_module": hub,
        "hub_indegree": indegree[hub] if hub else 0,
    }


def _git(root: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=8)
        return r.stdout.strip()
    except Exception:
        return ""


def scan_repo(root: Path) -> dict[str, Any]:
    """One project's full context record, plus its silently-rotting gaps."""
    remote = _git(root, "remote", "get-url", "origin")
    tests = discover_test_suites(root)
    ci = ci_state(root)
    cls = structure_class(root)
    az = azure_targets(root)
    gaps = []
    if cls == "agentic-langgraph" and not (root / "docs" / "adr").exists():
        gaps.append("langgraph project, no docs/adr (unmapped)")
    if tests["files"] == 0:
        gaps.append("no test suite found (dark)")
    if ci["has_ci"] and ci["advisory_gates"]:
        gaps.append("CI gates advisory (|| true)")
    if not ci["has_ci"]:
        gaps.append("no CI pipeline")
    if az and not ci["has_ci"]:
        gaps.append("azure resources but no pipeline")
    return {
        "name": root.name, "class": cls,
        "branch": _git(root, "branch", "--show-current"),
        "remote": remote.rsplit("/", 1)[-1] if remote else "",
        "azure_targets": az, "tests": tests, "ci": ci,
        "imports": python_import_graph(root), "gaps": gaps,
    }


def scan_projects(root: Path) -> list[dict[str, Any]]:
    return [scan_repo(d) for d in sorted(root.iterdir()) if d.is_dir() and (d / ".git").exists()]


def render_markdown(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Project Map",
        "",
        "| Project | Class | Tests | CI | Azure | Hub | Gaps |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        az = ", ".join(r["azure_targets"][:3]) or "-"
        ci = "advisory" if r["ci"]["advisory_gates"] else ("gated" if r["ci"]["has_ci"] else "none")
        imports = r.get("imports", {})
        hub = imports.get("hub_module")
        hub_cell = f"{hub} ({imports.get('hub_indegree', 0)})" if hub else "-"
        lines.append(
            f"| {r['name']} | {r['class']} | {r['tests']['files']} ({r['tests']['runner'] or '-'}) "
            f"| {ci} | {az} | {hub_cell} | {'; '.join(r['gaps']) or 'ok'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]).expanduser() if args else Path.home() / "projects"
    records = scan_projects(root)
    print(render_markdown(records))
    print(json.dumps({"root": str(root), "count": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
