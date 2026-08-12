"""The coffee-break v2 tools keep their CLI contract: selftests green, rejects exit 1."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*argv):
    return subprocess.run([sys.executable, *argv], cwd=ROOT,
                          capture_output=True, text=True)


def test_futures_selftest_green():
    r = run("tools/coffee/futures.py", "selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 checks failed" in r.stdout


def test_smoking_selftest_green():
    r = run("tools/coffee/smoking.py", "selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 checks failed" in r.stdout


def test_futures_full_cycle_via_cli(tmp_path):
    ledger = str(tmp_path / "futures.jsonl")
    r = run("tools/coffee/futures.py", "--ledger", ledger, "post",
            "--session", "qa-lab", "--claim", "PR 62 round 2 passes clean",
            "--falsifier", "pr:62", "--settle-by", "2026-08-14")
    assert r.returncode == 0, r.stderr
    pid = r.stdout.strip()
    assert run("tools/coffee/futures.py", "--ledger", ledger, "bet", "--id", pid,
               "--session", "review-board", "--side", "against",
               "--stake", "20").returncode == 0
    assert run("tools/coffee/futures.py", "--ledger", ledger, "settle", "--id", pid,
               "--outcome", "true", "--evidence", "merged").returncode == 0
    board = run("tools/coffee/futures.py", "--ledger", ledger, "board")
    assert board.returncode == 0
    assert "80  review-board" in board.stdout  # lost the against-bet


def test_smoking_gripe_mine_cycle(tmp_path):
    coffee = str(tmp_path / "coffee.jsonl")
    assert run("tools/coffee/smoking.py", "--coffee", coffee, "gripe",
               "--session", "eng-firm", "--text", "docmap stale again",
               "--about", "docmap.py").returncode == 0
    mined = run("tools/coffee/smoking.py", "--coffee", coffee, "mine")
    assert mined.returncode == 0
    assert "[bar-talk] eng-firm: docmap stale again" in mined.stdout
    again = run("tools/coffee/smoking.py", "--coffee", coffee, "mine")
    assert "nothing to mine" in again.stdout
