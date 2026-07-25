"""Tests for schema.connect: the connection lifecycle 24 call sites depend on.

`with sqlite3.connect(...) as conn:` is the language's best-known sqlite trap. That
context manager is a TRANSACTION manager: it commits on a clean exit and rolls back
on an exception, and it never closes the handle. Every one of the 24
`with connect(base_dir) as conn:` sites in this package read as if they released the
database and none of them did.

On Linux the leak is invisible, because unlink succeeds on an open file. On Windows
it holds the file and the directory will not delete, which is how it was finally
caught: two tests in test_local_alpha.py failed in TEARDOWN, on `beads.db` and
`intent.db`, with WinError 32. A defect that only shows up as a cleanup error on one
platform is still a defect on both, so the checks below assert the connection is
CLOSED rather than asserting a directory can be removed, and fail everywhere.
"""
from __future__ import annotations

import sqlite3

import pytest

from intent_control_plane.schema import base_paths, connect, initialize


def _closed(conn: sqlite3.Connection) -> bool:
    """True when the handle is released. There is no public `conn.closed`."""
    try:
        conn.execute("select 1")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_with_block_closes_the_connection(tmp_path):
    initialize(tmp_path)
    with connect(tmp_path) as conn:
        conn.execute("select 1")
    assert _closed(conn), "the with-block returned without releasing the database file"


def test_with_block_still_commits_on_a_clean_exit(tmp_path):
    # Closing must not cost the commit-on-success half. Every call site above relies on
    # it, and a connection that closes without committing would silently discard writes
    # instead of merely leaking a handle, which is the worse of the two failures.
    initialize(tmp_path)
    with connect(tmp_path) as conn:
        conn.execute("create table probe (v text)")
        conn.execute("insert into probe values ('kept')")
    with connect(tmp_path) as conn:
        # row_factory is sqlite3.Row, and a Row does not compare equal to a tuple, so
        # read the column by name rather than comparing raw rows.
        assert [r["v"] for r in conn.execute("select v from probe")] == ["kept"]


def test_with_block_still_rolls_back_on_an_exception_and_closes(tmp_path):
    # And the rollback half, which is the reason the transaction manager was being used
    # in the first place. The close has to happen on the error path too, or the leak
    # simply moves to wherever the code raises.
    initialize(tmp_path)
    with connect(tmp_path) as conn:
        conn.execute("create table probe (v text)")
    escaped = None
    # Combined rather than nested (ruff SIM117), and the order is the one that matters:
    # connect() is the inner manager, so it rolls back and closes BEFORE pytest.raises
    # sees the exception.
    with pytest.raises(RuntimeError), connect(tmp_path) as conn:
        escaped = conn
        conn.execute("insert into probe values ('discarded')")
        raise RuntimeError("caller failed mid-transaction")
    assert _closed(escaped), "the error path leaked the handle the success path releases"
    with connect(tmp_path) as conn:
        assert [r["v"] for r in conn.execute("select v from probe")] == []


def test_a_bare_connect_is_still_the_callers_to_close(tmp_path):
    # transitions.py:106 takes a bare connection, drives BEGIN IMMEDIATE / COMMIT by
    # hand, and closes it in a finally. Auto-closing must stay tied to the with-block:
    # if connect() closed eagerly by any other means, that site would lose its
    # transaction mid-flight. This pins the boundary so a later "simplification" of
    # connect() cannot quietly cross it.
    initialize(tmp_path)
    conn = connect(tmp_path)
    try:
        assert not _closed(conn)
    finally:
        conn.close()
    assert _closed(conn)


def test_connect_keeps_the_row_factory(tmp_path):
    # Callers index rows by column name (`row["to_state"]`). A factory swapped out while
    # changing the connection type turns every one of those into a TypeError.
    initialize(tmp_path)
    with connect(tmp_path) as conn:
        conn.execute("create table probe (v text)")
        conn.execute("insert into probe values ('named')")
        row = conn.execute("select v from probe").fetchone()
        assert row["v"] == "named"


def test_connect_opens_the_path_base_paths_declares(tmp_path):
    initialize(tmp_path)
    assert base_paths(tmp_path)["db"].exists()
