"""Async-purity panel check (issue #396).

Mechanism (Fluent Python 2e ch.21, "The All-or-Nothing Problem"): once a
codebase goes async, every I/O function on an async path must be an async
version or be delegated. A single blocking sync call (requests.get,
time.sleep, bare open()) silently blocks the whole event loop -- no
exception, just a loop that stops yielding.

Enforcement shape: deterministic AST check, hand-coded rules, zero LLM in
the hot path. Flags blocking sync calls inside `async def` bodies:

- requests.get/post/put/delete, time.sleep
- bare open() / file read-write without delegation

Exemptions (no false positives):
- calls routed through asyncio.to_thread / loop.run_in_executor
- allowlisted async facades (Motor-style: async API over a threaded core),
  allowlist by module name, explicit and reviewable
"""

import ast
import os

CHECK_ID = "async-purity"
PERSONA = "correctness"
SEVERITY = "medium"

# (module, attr) pairs for blocking sync calls.
BLOCKING_CALLS = {
    ("requests", "get"),
    ("requests", "post"),
    ("requests", "put"),
    ("requests", "delete"),
    ("requests", "patch"),
    ("requests", "head"),
    ("requests", "options"),
    ("time", "sleep"),
    ("os", "system"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("subprocess", "check_output"),
    ("subprocess", "check_call"),
}

# Bare builtin calls that block.
BLOCKING_BUILTINS = {"open", "input"}

# Async facades: async API over a threaded/sync core. Calls into these
# modules are exempt. Explicit and reviewable -- add a module here only
# with a review noting why its API is non-blocking.
ALLOWLIST_MODULES = {
    "motor",  # Motor: async MongoDB driver over a threaded core (ch.21 p.797)
}

# Call shapes that delegate to a thread: blocking calls nested inside
# these are exempt because they do not run on the event loop.
DELEGATING_CALLS = {
    ("asyncio", "to_thread"),
    ("to_thread",),  # from asyncio import to_thread
}


def _dotted(func: ast.AST) -> str:
    """Dotted name of a call target: requests.get, open, self.method."""
    if isinstance(func, ast.Attribute):
        value = func.value
        if isinstance(value, ast.Name):
            return "{}.{}".format(value.id, func.attr)
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _is_delegating(dotted: str) -> bool:
    parts = tuple(dotted.split("."))
    return parts in DELEGATING_CALLS or dotted.endswith(".run_in_executor")


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.in_async = 0
        self.in_delegated = 0
        self.findings: list[tuple[int, str]] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.in_async += 1
        self.generic_visit(node)
        self.in_async -= 1

    def visit_Call(self, node: ast.Call) -> None:
        dotted = _dotted(node.func)
        if _is_delegating(dotted):
            self.in_delegated += 1
            self.generic_visit(node)
            self.in_delegated -= 1
            return
        if self.in_async and not self.in_delegated:
            mod = dotted.split(".")[0] if dotted else ""
            if mod and mod not in ALLOWLIST_MODULES:
                blocking = (
                    dotted in {"{}.{}".format(m, a) for m, a in BLOCKING_CALLS}
                    or dotted in BLOCKING_BUILTINS
                )
                if blocking:
                    self.findings.append((node.lineno, dotted))
        self.generic_visit(node)


def check_tree(tree: ast.AST) -> list[tuple[int, str]]:
    """Blocking sync calls inside async def bodies.

    Returns [(lineno, dotted_name)] sorted by line. Pure function of the
    AST; stdlib only.
    """
    visitor = _Visitor()
    visitor.visit(tree)
    return sorted(visitor.findings)


def check_source(source: str) -> list[tuple[int, str]]:
    """Parse source and run the check. Syntax errors yield no findings
    (a file that does not parse is not this check's problem)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    return check_tree(tree)


WHY = (
    "a blocking sync call inside an async def blocks the whole event "
    "loop with no exception -- use an async client or delegate with "
    "asyncio.to_thread"
)


def findings_for_diff(
    reviewable_lines: list[dict], project_root: str
) -> list[dict]:
    """Panel findings for added lines only.

    `reviewable_lines` are {file, line, text} dicts already filtered by the
    panel's exemption rules. Files are read from `project_root` (the working
    tree holds the change under review); only violations on added lines are
    reported, so pre-existing problems never block a new change.
    """
    added_by_file: dict[str, set[int]] = {}
    for ln in reviewable_lines:
        path = ln["file"]
        if not path.endswith((".py", ".pyi")):
            continue
        added_by_file.setdefault(path, set()).add(ln["line"])

    findings: list[dict] = []
    for rel_path, added_lines in sorted(added_by_file.items()):
        full = os.path.join(project_root, rel_path)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except OSError:
            continue
        src_lines = source.splitlines()
        for lineno, dotted in check_source(source):
            if lineno not in added_lines:
                continue
            snippet = (
                src_lines[lineno - 1].strip()[:160]
                if 0 < lineno <= len(src_lines)
                else dotted
            )
            findings.append(
                {
                    "persona": PERSONA,
                    "check": CHECK_ID,
                    "severity": SEVERITY,
                    "file": rel_path,
                    "line": lineno,
                    "why": WHY,
                    "snippet": snippet,
                    "source": "local",
                }
            )
    return findings
