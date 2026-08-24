"""Oracle for tools/intent/tickets.py: the prompt-ticket ledger.

This file exists because the module it covers shipped through a green gate with no
test at all. The `unit` domain runs `pytest tests/`, and a new module under `tools/`
that nobody imports from `tests/` is invisible to it. A gate that passes on untested
code is not lying, it is answering a narrower question than it appears to, which is
the failure class this repository keeps recording.

What is pinned here, and why each one is a property rather than an example:

  - Ticket identity is content-derived and reproducible. If it were not, replaying
    the ledger would mint new ids and nothing could cite a ticket across a rebuild.
  - The chain covers the ticket's CONTENT. The reason this module exists at all is
    that bus.py's CHAIN_FIELDS covers three of a ticket row's keys, so a hash built
    against it would go on verifying after `state` or `text_sha` was edited.
  - The lifecycle is an allow-list. The deny-list it replaces accepted any edge
    nobody had thought to forbid, including CAPTURED straight to CLOSED_VERIFIED.
  - No prompt text reaches the git-tracked file. That is the whole basis on which
    this ledger is allowed to be committed, so it is asserted rather than assumed.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TICKETS_PATH = ROOT / "tools" / "intent" / "tickets.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("tickets_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


tickets = _load(TICKETS_PATH)

PROMPT = "pick up"
OTHER = "analyse the last prompts for this week"


def _append(path: Path, *, ticket: str, prompt_sha: str, state: str = "CAPTURED",
            session: str = "sess-1", ts: str = "2026-07-29T12:00:00Z") -> dict:
    return tickets.append_chained(
        ticket=ticket, ts=ts, session=session, repo="claude-setup",
        branch="main", prompt_sha=prompt_sha, state=state, path=path,
    )


class TicketIdentityTests(unittest.TestCase):
    def test_id_is_reproducible_from_content_alone(self) -> None:
        sha = tickets.text_sha(PROMPT)
        first = tickets.ticket_id("sess-1", sha, 0)
        again = tickets.ticket_id("sess-1", sha, 0)
        self.assertEqual(first, again)
        self.assertTrue(first.startswith("PT-"))
        self.assertEqual(len(first), 15)
        int(first[3:], 16)  # raises if the suffix is not hex

    def test_the_same_prompt_twice_in_one_session_is_two_tickets(self) -> None:
        """Typing one instruction twice is two pieces of work, not one.

        Without the occurrence index both derive the same id, and the second silently
        adopts the first's transition history, so a ticket could appear already closed
        the moment it was created.
        """
        sha = tickets.text_sha(PROMPT)
        self.assertNotEqual(
            tickets.ticket_id("sess-1", sha, 0),
            tickets.ticket_id("sess-1", sha, 1),
        )

    def test_the_same_prompt_in_two_sessions_is_two_tickets(self) -> None:
        sha = tickets.text_sha(PROMPT)
        self.assertNotEqual(
            tickets.ticket_id("sess-1", sha, 0),
            tickets.ticket_id("sess-2", sha, 0),
        )

    def test_different_prompts_do_not_collide(self) -> None:
        self.assertNotEqual(
            tickets.ticket_id("s", tickets.text_sha(PROMPT), 0),
            tickets.ticket_id("s", tickets.text_sha(OTHER), 0),
        )

    def test_id_carries_no_clock_so_replay_reproduces_it(self) -> None:
        """A derivation that reads the clock cannot be replayed, and the 587 historical
        prompts have no minting event to replay from in the first place."""
        sha = tickets.text_sha(PROMPT)
        payload = json.dumps({"session_id": "sess-1", "text_sha": sha,
                              "occurrence_index": 0}, sort_keys=True,
                             separators=(",", ":"))
        import hashlib
        expected = "PT-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(tickets.ticket_id("sess-1", sha, 0), expected)


class LifecycleTests(unittest.TestCase):
    def test_only_the_genesis_state_is_legal_from_nothing(self) -> None:
        self.assertTrue(tickets.is_allowed(None, tickets.GENESIS))
        for state in tickets.TICKET_STATES - {tickets.GENESIS}:
            self.assertFalse(tickets.is_allowed(None, state), state)

    def test_a_captured_ticket_cannot_jump_straight_to_closed_verified(self) -> None:
        """The exact edge a deny-list permits by omission."""
        self.assertFalse(tickets.is_allowed("CAPTURED", "CLOSED_VERIFIED"))

    def test_terminal_states_have_no_exits(self) -> None:
        self.assertEqual(tickets.TICKET_LIFECYCLE["CLOSED_VERIFIED"], set())
        self.assertEqual(tickets.TICKET_LIFECYCLE["SUPERSEDED"], set())

    def test_a_wrong_close_is_reopenable_and_a_misclassification_correctable(self) -> None:
        """Closing must not be a trapdoor: both were operator judgements that can be wrong."""
        self.assertTrue(tickets.is_allowed("CLOSED_WONTDO", "OPEN"))
        self.assertTrue(tickets.is_allowed("NOT_WORK", "TRIAGED"))

    def test_every_named_target_is_itself_a_declared_state(self) -> None:
        """A typo in the allow-list would otherwise create an unreachable dead end."""
        for src, targets in tickets.TICKET_LIFECYCLE.items():
            for dst in targets:
                self.assertIn(dst, tickets.TICKET_STATES, f"{src} -> {dst}")

    def test_an_unknown_state_permits_nothing(self) -> None:
        self.assertFalse(tickets.is_allowed("NOT_A_STATE", "OPEN"))


class ChainCoverageTests(unittest.TestCase):
    """The defect this module was written to avoid, asserted directly."""

    def _row(self) -> dict:
        return tickets.build_row(
            ticket="PT-abc123abc123", ts="2026-07-29T12:00:00Z", session="sess-1",
            repo="claude-setup", branch="main", prompt_sha=tickets.text_sha(PROMPT),
            state="CAPTURED", prev="",
        )

    def test_editing_state_is_detected(self) -> None:
        row = self._row()
        self.assertFalse(tickets.row_altered(row))
        forged = dict(row, state="CLOSED_VERIFIED")
        self.assertTrue(tickets.row_altered(forged),
                        "state is outside bus CHAIN_FIELDS and must still be covered")

    def test_swapping_which_prompt_the_ticket_refers_to_is_detected(self) -> None:
        row = self._row()
        forged = dict(row, text_sha=tickets.text_sha(OTHER))
        self.assertTrue(tickets.row_altered(forged))

    def test_every_declared_field_is_actually_covered(self) -> None:
        row = self._row()
        for field in tickets.PT_CHAIN_FIELDS:
            if field == "prev":
                continue
            forged = dict(row)
            forged[field] = "tampered-value"
            self.assertTrue(tickets.row_altered(forged),
                            f"{field} is declared covered but editing it is invisible")

    def test_the_declaration_does_not_list_itself(self) -> None:
        """canonical() adds it. A self-listing declaration makes the guarantee
        untestable, which is how the first version of this shipped past a mutation."""
        self.assertNotIn("chain_fields", tickets.PT_CHAIN_FIELDS)

    def test_narrowing_the_declaration_is_detected(self) -> None:
        row = self._row()
        narrowed = dict(row, chain_fields=[f for f in tickets.PT_CHAIN_FIELDS
                                           if f != "state"])
        self.assertTrue(tickets.row_altered(narrowed),
                        "coverage was reduced without moving the hash")


class LedgerTests(unittest.TestCase):
    def test_rows_chain_to_their_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            a = _append(path, ticket="PT-000000000001", prompt_sha=tickets.text_sha(PROMPT))
            b = _append(path, ticket="PT-000000000002", prompt_sha=tickets.text_sha(OTHER))
            self.assertEqual(a["prev"], "")
            self.assertEqual(b["prev"], tickets.row_id(a))
            self.assertEqual(tickets.verify(path), [])

    def test_an_edited_row_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            _append(path, ticket="PT-000000000001", prompt_sha=tickets.text_sha(PROMPT))
            _append(path, ticket="PT-000000000002", prompt_sha=tickets.text_sha(OTHER))
            rows = tickets.read_rows(path)
            rows[0]["state"] = "CLOSED_VERIFIED"
            path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n",
                            encoding="utf-8")
            breaks = tickets.verify(path)
            self.assertTrue(breaks)
            self.assertIn("no longer matches its hash", breaks[0][1])

    def test_a_deleted_row_breaks_the_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            for i in range(3):
                _append(path, ticket=f"PT-00000000000{i}", prompt_sha=tickets.text_sha(str(i)))
            rows = tickets.read_rows(path)
            del rows[1]
            path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n",
                            encoding="utf-8")
            self.assertTrue(tickets.verify(path))

    def test_no_prompt_text_reaches_the_tracked_file(self) -> None:
        """The basis on which this file may live in git."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            secret = "rotate the key sk-do-not-commit-me and email bob@example.com"
            _append(path, ticket="PT-000000000001", prompt_sha=tickets.text_sha(secret))
            body = path.read_text(encoding="utf-8")
            self.assertNotIn("sk-do-not-commit-me", body)
            self.assertNotIn("bob@example.com", body)
            self.assertIn(tickets.text_sha(secret), body)

    def test_a_torn_line_is_skipped_rather_than_raising(self) -> None:
        """This is read by a hook on every prompt; raising would block the session."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            _append(path, ticket="PT-000000000001", prompt_sha=tickets.text_sha(PROMPT))
            with path.open("a", encoding="utf-8") as fh:
                fh.write('{"id": "PT-torn", "ts"')
            self.assertEqual(len(tickets.read_rows(path)), 1)

    def test_concurrent_appends_neither_lose_rows_nor_fork_the_chain(self) -> None:
        """Reading the tip outside the lock is the fork; losing rows is the Windows
        append defect. Both are asserted here because the fix for one is not the
        fix for the other."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt-tickets.jsonl"
            writers = 20

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(
                    lambda i: _append(path, ticket=f"PT-{i:012d}",
                                      prompt_sha=tickets.text_sha(str(i))),
                    range(writers),
                ))

            rows = tickets.read_rows(path)
            self.assertEqual(len(rows), writers, "rows were destroyed by a concurrent append")
            self.assertEqual(len({r["id"] for r in rows}), writers)
            self.assertEqual(tickets.verify(path), [], "the chain forked")


class MintForPromptTests(unittest.TestCase):
    """append_for_prompt derives the id and appends inside ONE lock.

    Splitting those is the bug the function exists to prevent, so the tests are about
    the joint operation rather than about either half.
    """

    def test_the_same_prompt_twice_gets_two_tickets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            sha = tickets.text_sha(PROMPT)
            a = tickets.append_for_prompt(session="s1", repo="r", branch="main",
                                          prompt_sha=sha, ts="2026-07-29T12:00:00Z",
                                          path=path)
            b = tickets.append_for_prompt(session="s1", repo="r", branch="main",
                                          prompt_sha=sha, ts="2026-07-29T12:00:01Z",
                                          path=path)
            self.assertNotEqual(a["id"], b["id"])
            self.assertEqual(b["prev"], tickets.row_id(a))
            self.assertEqual(tickets.verify(path), [])

    def test_the_occurrence_index_is_scoped_to_the_session(self) -> None:
        """A repeat in another session is that session's first, not a global second."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            sha = tickets.text_sha(PROMPT)
            a = tickets.append_for_prompt(session="s1", repo="r", branch="main",
                                          prompt_sha=sha, ts="t", path=path)
            b = tickets.append_for_prompt(session="s2", repo="r", branch="main",
                                          prompt_sha=sha, ts="t", path=path)
            self.assertEqual(a["id"], tickets.ticket_id("s1", sha, 0))
            self.assertEqual(b["id"], tickets.ticket_id("s2", sha, 0))

    def test_the_row_starts_at_the_genesis_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            row = tickets.append_for_prompt(session="s1", repo="r", branch="main",
                                            prompt_sha=tickets.text_sha(PROMPT),
                                            ts="t", path=path)
            self.assertEqual(row["state"], tickets.GENESIS)
            self.assertTrue(tickets.is_allowed(None, row["state"]))

    def test_concurrent_identical_prompts_never_share_a_ticket(self) -> None:
        """The exact race the single lock exists for: same session, same text, at once.

        If the count and the append were separate, every writer would read zero and all
        20 would derive one id, and 19 pieces of work would vanish into the first.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            sha = tickets.text_sha(PROMPT)
            writers = 20

            with ThreadPoolExecutor(max_workers=8) as pool:
                rows = list(pool.map(
                    lambda _: tickets.append_for_prompt(
                        session="s1", repo="r", branch="main", prompt_sha=sha,
                        ts="2026-07-29T12:00:00Z", path=path),
                    range(writers),
                ))

            self.assertEqual(len({r["id"] for r in rows}), writers,
                             "two concurrent prompts were minted the same ticket")
            self.assertEqual(len(tickets.read_rows(path)), writers)
            self.assertEqual(tickets.verify(path), [], "the chain forked")


if __name__ == "__main__":
    unittest.main()
