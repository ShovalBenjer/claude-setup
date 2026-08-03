"""The bus append must write while holding the lock, asserted structurally.

WHY THIS IS AN AST TEST AND NOT A CONCURRENCY TEST, which is the whole point.

`mutate.py --spec bus` has two survivors, both about the lock in `append_row`:
"append_row stops taking the lock" and "the lock is released before the write
instead of after". Twelve of the other thirteen specs are at 0 survived, so this
is the one place the mutation control says the bus selftest cannot tell a locked
append from an unlocked one, on the hash-chained ledger `bus.py verify` polices.

The obvious fix is a test that races two writers. It would be worse than nothing
here. `append_row`'s own docstring says the lock exists because overlapping
writes "on Windows destroy whole rows"; on Linux an `O_APPEND` write below
PIPE_BUF is atomic, so two racing appends both land intact WITH THE LOCK
DELETED. The test would pass on this machine, pass in CI, and assert nothing.
That is L-2026-07-31-g exactly: a host-shaped oracle that silently answers a
different question on the other host.

So this asserts the STRUCTURE the docstring claims instead: the bytes go to disk
inside the `with file_lock(...)` block. It cannot prove the lock excludes anyone,
which no test on Linux can. It can prove nobody quietly moved the write out from
under it, which is what both surviving mutants do.
"""
import ast
import pathlib

import pytest

BUS_PY = pathlib.Path(__file__).resolve().parents[1] / "tools" / "bus" / "bus.py"


def _append_row() -> ast.FunctionDef:
    tree = ast.parse(BUS_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "append_row":
            return node
    pytest.fail("tools/bus/bus.py no longer defines append_row")


def _lock_blocks(fn: ast.FunctionDef) -> list[ast.With]:
    """Every `with file_lock(...)` statement in the function."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            call = item.context_expr
            if isinstance(call, ast.Call):
                name = call.func
                fname = getattr(name, "id", None) or getattr(name, "attr", None)
                if fname == "file_lock":
                    out.append(node)
    return out


def _writes(fn: ast.FunctionDef) -> list[ast.Call]:
    """Every `<something>.write(...)` call in the function."""
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "write"]


def test_append_row_takes_the_lock():
    """Kills the mutant 'append_row stops taking the lock'."""
    fn = _append_row()
    assert _lock_blocks(fn), (
        "append_row does not take file_lock at all. The hash-chained ledger is "
        "written without exclusion; on Windows overlapping appends destroy rows."
    )


def test_every_write_happens_inside_the_lock():
    """Kills the mutant 'the lock is released before the write instead of after'.

    A `with file_lock(...): pass` followed by the write leaves the lock block
    present, so the previous test still passes. This one is what notices.
    """
    fn = _append_row()
    locks = _lock_blocks(fn)
    assert locks, "no lock block; see test_append_row_takes_the_lock"

    inside = set()
    for lock in locks:
        for stmt in lock.body:
            for node in ast.walk(stmt):
                inside.add(id(node))

    writes = _writes(fn)
    assert writes, "append_row performs no write; the function has changed shape"

    outside = [w for w in writes if id(w) not in inside]
    assert not outside, (
        "append_row writes at line(s) %s outside the file_lock block. The lock "
        "must be held THROUGH the write, not merely acquired and released before "
        "it, or another writer can interleave between release and write."
        % sorted(w.lineno for w in outside)
    )


def test_the_oracle_can_go_red():
    """The structural check must reject code that moves the write out.

    Without this, a refactor that breaks _lock_blocks or _writes (a rename, a
    different call shape) would make both tests above pass vacuously on any
    input, which is the failure mode a structural oracle is most prone to.
    """
    mutated = ast.parse(
        "def append_row(rec):\n"
        "    with file_lock(BUS):\n"
        "        pass\n"
        "    with BUS.open('ab') as fh:\n"
        "        fh.write(payload)\n"
    )
    fn = next(n for n in ast.walk(mutated)
              if isinstance(n, ast.FunctionDef) and n.name == "append_row")

    locks = _lock_blocks(fn)
    assert locks, "helper failed to find the lock in the mutated sample"

    inside = set()
    for lock in locks:
        for stmt in lock.body:
            for node in ast.walk(stmt):
                inside.add(id(node))
    writes = _writes(fn)
    assert writes, "helper failed to find the write in the mutated sample"
    assert [w for w in writes if id(w) not in inside], (
        "the structural check accepted a write outside the lock, so it would "
        "not have caught the surviving mutant either"
    )
