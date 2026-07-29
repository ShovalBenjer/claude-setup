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

    def test_an_edit_to_other_state_files_still_moves_it(self, repo):
        """Only the gate's OWN outputs are exempt. state/lessons.jsonl and the
        rest are ordinary content and a change to them is a change."""
        before = fp(repo)
        (repo / "state" / "lessons.jsonl").write_text('{"id": "L1"}\n',
                                                      encoding="utf-8")
        assert fp(repo) != before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
