"""Regression oracles for the prompt-capture slice (spec 2026-07-29 section 4.2).

Written before the patches they cover, so each one starts red. What they pin down:

- `ledger_append` returns a byte offset that seeks to the row it wrote, not a line
  number counted by reading the whole file. The line count was both O(file) per turn,
  which makes a 587-row backfill quadratic, and a lost update: two writers each read
  N and each return N+1, so two events cite one location and one of them is a lie.
- The offset survives concurrent writers. This is the property the line counter could
  not have, and it is asserted by seeking to each returned offset and checking the row
  found there is the row that offset was handed out for.
- `connect()` sets WAL and a non-zero busy timeout. SQLite's default busy timeout is
  0, so a second concurrent writer raises immediately, and the capture hook's blanket
  `except` would swallow it. Two sessions prompting in the same second would lose one
  prompt silently, which is the original complaint reintroduced by the fix for it.
- `capture` accepts `--metadata`. Until it does, the literal `{}` in the insert blocks
  every field the slice needs: prompt_id, message_uuid, parents, text_sha, seq.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest import TestCase

from intent_control_plane.cli import capture, ledger_append
from intent_control_plane.schema import base_paths, connect, initialize


def _event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": "user_prompt",
        "timestamp_utc": "2026-07-29T00:00:00Z",
        "actor": "shoval",
        "raw_text": "unicode payload: \u05e9\u05dc\u05d5\u05dd \u4e16\u754c",
    }


def _row_at(ledger: Path, offset: int) -> dict[str, object]:
    """Read exactly the row that starts at `offset`, as a byte offset into the file."""
    with ledger.open("rb") as handle:
        handle.seek(offset)
        return json.loads(handle.readline().decode("utf-8"))


class LedgerOffsetTests(TestCase):
    def test_returned_ref_is_a_byte_offset_seeking_to_its_own_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)
            ledger = base_paths(base_dir)["ledger"]

            refs = [ledger_append(base_dir, _event(f"evt_{i}")) for i in range(5)]

            for i, ref in enumerate(refs):
                offset = int(ref.rsplit(":", 1)[1])
                self.assertEqual(_row_at(ledger, offset)["event_id"], f"evt_{i}")

    def test_offset_is_the_start_of_the_row_not_its_end(self) -> None:
        """`tell()` after a write names the END of the row. Citing it reads the NEXT row."""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)
            ledger = base_paths(base_dir)["ledger"]

            first = ledger_append(base_dir, _event("evt_first"))
            self.assertEqual(int(first.rsplit(":", 1)[1]), 0)
            self.assertEqual(_row_at(ledger, 0)["event_id"], "evt_first")

    def test_offsets_are_byte_exact_for_non_ascii_rows(self) -> None:
        """A row of Hebrew and CJK is longer in bytes than in characters.

        Text mode on Windows also rewrites \\n as \\r\\n, so an offset computed from the
        length of the string rather than of the encoded bytes drifts by one byte per
        preceding row. This test fails on either mistake.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)
            ledger = base_paths(base_dir)["ledger"]

            refs = [ledger_append(base_dir, _event(f"evt_{i}")) for i in range(4)]
            offsets = [int(r.rsplit(":", 1)[1]) for r in refs]

            self.assertEqual(sorted(offsets), offsets)
            self.assertEqual(len(set(offsets)), len(offsets))
            for i, offset in enumerate(offsets):
                self.assertEqual(_row_at(ledger, offset)["event_id"], f"evt_{i}")
            # The last offset plus its row must account for the whole file.
            self.assertEqual(ledger.stat().st_size, offsets[-1] + len(
                (json.dumps(_event("evt_3"), sort_keys=True) + "\n").encode("utf-8")
            ))

    def test_concurrent_appends_each_get_their_own_offset(self) -> None:
        """The property the line counter could not hold: no two writers cite one row."""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)
            ledger = base_paths(base_dir)["ledger"]
            writers = 24

            with ThreadPoolExecutor(max_workers=8) as pool:
                refs = list(pool.map(
                    lambda i: ledger_append(base_dir, _event(f"evt_{i}")),
                    range(writers),
                ))

            offsets = [int(r.rsplit(":", 1)[1]) for r in refs]
            self.assertEqual(len(set(offsets)), writers, "two writers cited one offset")

            # Every offset must resolve to the row it was handed out for.
            for i, offset in enumerate(offsets):
                self.assertEqual(_row_at(ledger, offset)["event_id"], f"evt_{i}")

            with ledger.open("rb") as handle:
                self.assertEqual(len(handle.read().splitlines()), writers)


class ConnectPragmaTests(TestCase):
    def test_connect_sets_wal_and_a_non_zero_busy_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)

            with connect(base_dir) as conn:
                journal = conn.execute("pragma journal_mode").fetchone()[0]
                timeout = conn.execute("pragma busy_timeout").fetchone()[0]

            self.assertEqual(journal.lower(), "wal")
            self.assertGreaterEqual(timeout, 1000)

    def test_second_writer_waits_for_the_lock_instead_of_failing_instantly(self) -> None:
        """The timeout has to be honoured, not merely set.

        With busy_timeout 0 the contended insert raises `database is locked` in
        microseconds. Asserting only that it raises would pass either way, so this
        measures the elapsed time and requires the writer to have actually waited.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            initialize(base_dir)
            db = base_paths(base_dir)["db"]

            holder = sqlite3.connect(db)
            holder.isolation_level = None
            holder.execute("BEGIN IMMEDIATE")
            try:
                with connect(base_dir) as conn:
                    conn.execute("pragma busy_timeout = 400")
                    started = time.monotonic()
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute(
                            "insert into graph_edges (edge_id, source_id, target_id,"
                            " edge_type, created_at_utc) values (?,?,?,?,?)",
                            ("e1", "a", "b", "t", "2026-07-29T00:00:00Z"),
                        )
                    waited = time.monotonic() - started
                self.assertGreaterEqual(waited, 0.3, "busy_timeout was not honoured")
            finally:
                holder.rollback()
                holder.close()


class CaptureMetadataTests(TestCase):
    @staticmethod
    def _args(base_dir: Path, **over: object) -> argparse.Namespace:
        defaults: dict[str, object] = {
            "base_dir": base_dir,
            "event_type": "user_prompt",
            "session": "sess-1",
            "repo": "C:/Users/shova/claude-setup",
            "branch": "main",
            "bead": None,
            "workflow": None,
            "actor": "shoval",
            "authority": "raw_user_prompt",
            "text": "pick up",
            "metadata": None,
        }
        defaults.update(over)
        return argparse.Namespace(**defaults)

    def test_metadata_reaches_both_the_ledger_and_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            meta = {"text_sha": "9f2c", "seq": 41, "parents": ["evt_a", "PT-b"]}

            result = capture(self._args(base_dir, metadata=json.dumps(meta)))

            ledger = base_paths(base_dir)["ledger"]
            offset = int(result["raw_text_ref"].rsplit(":", 1)[1])
            self.assertEqual(_row_at(ledger, offset)["metadata"], meta)

            with closing(sqlite3.connect(base_paths(base_dir)["db"])) as conn:
                stored = conn.execute(
                    "select metadata_json from events where event_id = ?",
                    (result["event_id"],),
                ).fetchone()[0]
            self.assertEqual(json.loads(stored), meta)

    def test_absent_metadata_still_stores_an_empty_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"

            result = capture(self._args(base_dir))

            with closing(sqlite3.connect(base_paths(base_dir)["db"])) as conn:
                stored = conn.execute(
                    "select metadata_json from events where event_id = ?",
                    (result["event_id"],),
                ).fetchone()[0]
            self.assertEqual(json.loads(stored), {})

    def test_malformed_metadata_is_rejected_not_stored_as_a_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / ".intent"
            with self.assertRaises((SystemExit, ValueError, json.JSONDecodeError)):
                capture(self._args(base_dir, metadata="{not json"))
