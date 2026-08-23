"""The gate's fingerprint must cover the change being gated, not the gate's own output.

Measured 2026-07-27 on this repository. `state/gate-runs.jsonl` is tracked, and
`tree_fingerprint` hashes `git diff HEAD`, so every gate run appended its own
result row to a file inside its own fingerprint. The run recorded fingerprint A,
the append turned the tree into B, and the Stop hook then looked for a green run
matching B and could never find one. Appending a single ledger row moved the live
fingerprint from 5dad68ca to 62951e50.

The consequence was not that some domain was red. It was that a fully green run
could not have satisfied the Stop boundary either, because the act of recording
the pass destroyed the fingerprint the pass was recorded against. That is a check
that cannot pass, which carries exactly as much information as one that cannot
fail.

These tests run against a throwaway git repository so they never touch the real
tree, and the last one exists to stop the fix from over-correcting into a
fingerprint that ignores real edits.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "gate"))
import gate  # noqa: E402


def _run(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path):
    """A minimal repo shaped like this one: tracked source, tracked run ledger."""
    _run(["git", "init", "-q"], tmp_path)
    _run(["git", "config", "user.email", "t@example.invalid"], tmp_path)
    _run(["git", "config", "user.name", "test"], tmp_path)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "thing.py").write_text("x = 1\n", encoding="utf-8")
    state = tmp_path / "state"
    state.mkdir()
    (state / "gate-runs.jsonl").write_text('{"verdict": "PASS"}\n', encoding="utf-8")
    (state / "prompt-tickets.jsonl").write_text('{"ticket": "t0"}\n', encoding="utf-8")
    (state / "skill-use.jsonl").write_text('{"skill": "s0"}\n', encoding="utf-8")
    (state / "routing.jsonl").write_text('{"route": "r0"}\n', encoding="utf-8")
    (state / "agent-spawns.jsonl").write_text('{"spawn": "a0"}\n', encoding="utf-8")
    (state / "prose-scores.jsonl").write_text('{"score": 0}\n', encoding="utf-8")
    (state / "telemetry-published.txt").write_text("abc\n", encoding="utf-8")
    _run(["git", "add", "-A"], tmp_path)
    _run(["git", "commit", "-qm", "initial"], tmp_path)
    return tmp_path


def fp(repo):
    return gate.tree_fingerprint(str(repo))[2]


class TestGateOutputIsNotHashed:
    def test_appending_a_run_row_does_not_move_the_fingerprint(self, repo):
        """The defect, stated directly: recording a result must not invalidate it."""
        before = fp(repo)
        led = repo / "state" / "gate-runs.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + '{"verdict": "PASS"}\n',
                       encoding="utf-8")
        assert fp(repo) == before

    def test_many_appends_still_do_not_move_it(self, repo):
        before = fp(repo)
        led = repo / "state" / "gate-runs.jsonl"
        for i in range(5):
            led.write_text(led.read_text(encoding="utf-8") + '{"n": %d}\n' % i,
                           encoding="utf-8")
        assert fp(repo) == before

    def test_a_new_review_artifact_does_not_move_the_fingerprint(self, repo):
        """panel.py writes state/reviews/<sha>.json as the review domain's own
        output. It arrives untracked, which lands it in `git status --porcelain`
        and moved the fingerprint the same way the ledger did."""
        before = fp(repo)
        reviews = repo / "state" / "reviews"
        reviews.mkdir()
        (reviews / "deadbeef.json").write_text('{"verdict": "approve"}\n',
                                               encoding="utf-8")
        assert fp(repo) == before


class TestHarnessPerTurnOutputIsNotHashed:
    """The same defect by a second route, measured 2026-07-30.

    state/prompt-tickets.jsonl is tracked on purpose and the UserPromptSubmit hook
    appends to it once per operator turn. Four consecutive turns of one session
    produced four fingerprints (76378e5f, 05fdfc73, b10cfce6, 9f0ccd38) with a green
    run recorded against each and the Stop boundary rejecting all four, while
    nothing in the repository changed between the second and third. Continuing a
    conversation is not a change to the tree being gated.
    """

    def test_appending_a_prompt_ticket_does_not_move_the_fingerprint(self, repo):
        before = fp(repo)
        led = repo / "state" / "prompt-tickets.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + '{"ticket": "t1"}\n',
                       encoding="utf-8")
        assert fp(repo) == before

    def test_a_turn_of_conversation_alone_leaves_the_verdict_valid(self, repo):
        """The end-to-end shape of the bug: gate, then one more turn, then check."""
        recorded = fp(repo)
        led = repo / "state" / "prompt-tickets.jsonl"
        for i in range(3):
            led.write_text(led.read_text(encoding="utf-8") + '{"t": %d}\n' % i,
                           encoding="utf-8")
        assert fp(repo) == recorded, "a passing run must survive the next prompt"

    def test_the_skill_use_ledger_is_exempt_too(self, repo):
        """Second instance of the same defect, found 2026-07-30 an hour after the first.

        state/skill-use.jsonl is tracked and the live PostToolUse hook
        skill-usage-log.sh appends to it once per TOOL CALL, so it moves the
        fingerprint faster than the per-turn ticket ledger does. One exempt path was a
        fix for one file; two make it a class, and the class is 'a tracked ledger the
        harness writes on its own schedule'.
        """
        before = fp(repo)
        led = repo / "state" / "skill-use.jsonl"
        for i in range(4):
            led.write_text(led.read_text(encoding="utf-8") + '{"n": %d}\n' % i,
                           encoding="utf-8")
        assert fp(repo) == before

    def test_both_harness_ledgers_moving_together_still_leaves_it_stable(self, repo):
        before = fp(repo)
        for name, key in (("prompt-tickets.jsonl", "t"), ("skill-use.jsonl", "s")):
            led = repo / "state" / name
            led.write_text(led.read_text(encoding="utf-8") + '{"%s": 1}\n' % key,
                           encoding="utf-8")
        assert fp(repo) == before

    def test_the_exemption_is_the_exact_path_and_not_its_neighbours(self, repo):
        """Guard against the exemption widening into all of state/ by accident."""
        before = fp(repo)
        (repo / "state" / "prompt-tickets-archive.jsonl").write_text(
            '{"ticket": "old"}\n', encoding="utf-8")
        assert fp(repo) != before

    def test_the_other_per_turn_ledgers_are_exempt(self, repo):
        """Third finding of the same class, measured 2026-08-12 after the operator
        named the cost ('the hook... really slows me down'): one estate-audit
        session was forced through three full gate runs in 18 hours because
        routing.jsonl (route.py, once per prompt), agent-spawns.jsonl
        (spawn_log.py, once per Agent call) and prose-scores.jsonl moved the
        fingerprint between done-claims while no gated content changed."""
        before = fp(repo)
        for name, row in (("routing.jsonl", '{"route": "r1"}'),
                          ("agent-spawns.jsonl", '{"spawn": "a1"}'),
                          ("prose-scores.jsonl", '{"score": 1}')):
            led = repo / "state" / name
            led.write_text(led.read_text(encoding="utf-8") + row + "\n",
                           encoding="utf-8")
        assert fp(repo) == before

    def test_the_feed_cursor_is_exempt(self, repo):
        """state/telemetry-published.txt is appended by the agent-feed systemd
        timer every 30 minutes on a real post: a schedule the gated change does
        not control, which is this exemption class's own definition."""
        before = fp(repo)
        cur = repo / "state" / "telemetry-published.txt"
        cur.write_text(cur.read_text(encoding="utf-8") + "def\n", encoding="utf-8")
        assert fp(repo) == before


class TestRealChangesStillMoveTheFingerprint:
    """The fix must not buy satisfiability by going blind."""

    def test_editing_tracked_source_moves_it(self, repo):
        before = fp(repo)
        (repo / "tools" / "thing.py").write_text("x = 2\n", encoding="utf-8")
        assert fp(repo) != before

    def test_a_new_untracked_source_file_moves_it(self, repo):
        before = fp(repo)
        (repo / "tools" / "new.py").write_text("y = 1\n", encoding="utf-8")
        assert fp(repo) != before

    def test_a_new_commit_moves_it(self, repo):
        before = fp(repo)
        (repo / "tools" / "thing.py").write_text("x = 3\n", encoding="utf-8")
        _run(["git", "add", "-A"], repo)
        _run(["git", "commit", "-qm", "second"], repo)
        assert fp(repo) != before

    def test_a_commit_of_only_excluded_ledgers_does_not_move_it(self, repo):
        """Fifth finding of the class, 2026-08-23, by a third route: COMMITTING.

        The exclusions only filtered the dirty diff; the fingerprint also hashed the
        raw HEAD sha, so `git commit` of nothing but gate-runs.jsonl and hook rows
        minted a new fingerprint and invalidated the very run being recorded. One
        session was made to run the full gate three times in a day with no gated
        content changing, each time because it had committed the previous verdict.
        """
        before = fp(repo)
        led = repo / "state" / "gate-runs.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + '{"verdict": "PASS"}\n',
                       encoding="utf-8")
        tick = repo / "state" / "prompt-tickets.jsonl"
        tick.write_text(tick.read_text(encoding="utf-8") + '{"ticket": "t9"}\n',
                        encoding="utf-8")
        _run(["git", "add", "-A"], repo)
        _run(["git", "commit", "-qm", "chore(state): ledger rows only"], repo)
        assert fp(repo) == before

    def test_a_commit_mixing_ledgers_and_content_still_moves_it(self, repo):
        before = fp(repo)
        led = repo / "state" / "gate-runs.jsonl"
        led.write_text(led.read_text(encoding="utf-8") + '{"verdict": "PASS"}\n',
                       encoding="utf-8")
        (repo / "tools" / "thing.py").write_text("x = 9\n", encoding="utf-8")
        _run(["git", "add", "-A"], repo)
        _run(["git", "commit", "-qm", "mixed"], repo)
        assert fp(repo) != before

    def test_an_edit_to_other_state_files_still_moves_it(self, repo):
        """Only the gate's OWN outputs are exempt. state/lessons.jsonl and the
        rest are ordinary content and a change to them is a change."""
        before = fp(repo)
        (repo / "state" / "lessons.jsonl").write_text('{"id": "L1"}\n',
                                                      encoding="utf-8")
        assert fp(repo) != before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
