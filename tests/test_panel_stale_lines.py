"""A finding must cite a line the tree actually contains.

Written 2026-07-30, closing the review domain's third waiver rather than renewing it.

`added_lines` unions three diffs (branch-base...HEAD, working tree vs HEAD, and the
index) and dedupes by (path, lineno). A line added early on a branch and deleted later
on the same branch is still present in the first diff, so it survives into the review,
and its recorded line number now points at whatever text occupies that position today.

Measured on the 2026-07-30 tree, both remaining HIGH findings were this:

    tools/map/codemap.py:66   snippet: p = subprocess.run("git " + args, ... shell=True,
    tools/map/codemap.py:157  snippet: p = subprocess.run("git ls-files -z", ... shell=True,

Line 66 of that file is a comment recording that the helper was DELETED on 2026-07-27,
and line 157 sits inside a docstring. The vulnerable code is not in the tree; an AST walk
for a shell=True keyword returns []. So the reviewer was reporting a vulnerability that
the change under review removes.

This is the same principle panel.py already enforces in the other direction. Its mutation
spec carries "findings citing a line the change did not add are kept" as a regression it
must catch, because an invented file:line is unactionable. A line the change added and
then removed is unactionable for the same reason and was not being filtered.

The filter is fail-open on purpose: if the file cannot be read, the line is kept. A
reviewer that goes quiet when it cannot check something is worse than one that over-reports.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "review"))
import panel  # noqa: E402


def test_line_matching_the_file_is_kept(tmp_path):
    src = tmp_path / "keep.py"
    src.write_text("import os\nsubprocess.run(cmd, shell=True)\n", encoding="utf-8")
    rows = [{"file": "keep.py", "line": 2, "text": "subprocess.run(cmd, shell=True)"}]
    assert panel.drop_stale_lines(str(tmp_path), rows) == rows


def test_line_the_tree_no_longer_contains_is_dropped(tmp_path):
    """The codemap.py:66 case, reduced."""
    src = tmp_path / "gone.py"
    src.write_text("import os\n# the shell=True helper was deleted on 2026-07-27\n",
                   encoding="utf-8")
    rows = [{"file": "gone.py", "line": 2,
             "text": 'p = subprocess.run("git " + args, shell=True)'}]
    assert panel.drop_stale_lines(str(tmp_path), rows) == []


def test_line_past_the_end_of_the_file_is_dropped(tmp_path):
    src = tmp_path / "short.py"
    src.write_text("one\n", encoding="utf-8")
    rows = [{"file": "short.py", "line": 40, "text": "subprocess.run(x, shell=True)"}]
    assert panel.drop_stale_lines(str(tmp_path), rows) == []


def test_deleted_file_drops_its_lines(tmp_path):
    rows = [{"file": "removed.py", "line": 1, "text": "subprocess.run(x, shell=True)"}]
    assert panel.drop_stale_lines(str(tmp_path), rows) == []


def test_whitespace_and_line_ending_differences_do_not_drop_a_real_line(tmp_path):
    src = tmp_path / "ws.py"
    src.write_text("    subprocess.run(cmd, shell=True)   \r\n", encoding="utf-8")
    rows = [{"file": "ws.py", "line": 1, "text": "  subprocess.run(cmd, shell=True)"}]
    assert len(panel.drop_stale_lines(str(tmp_path), rows)) == 1


def test_unreadable_file_fails_open(tmp_path, monkeypatch):
    """A reviewer that goes quiet when it cannot check is worse than one that shouts."""
    rows = [{"file": "x.py", "line": 1, "text": "subprocess.run(x, shell=True)"}]

    (tmp_path / "x.py").write_text("subprocess.run(x, shell=True)\n", encoding="utf-8")

    def boom(*a, **k):
        raise OSError("nope")

    # Patch the NAME in panel's module namespace, not builtins. A global
    # builtins.open that raises also breaks pytest's assertion rewriting, capture and
    # traceback machinery, which made this test order-dependent: it failed once in a
    # full-suite run and passed alone (L-2026-07-30-c). A module-scoped shadow reaches
    # panel.drop_stale_lines and nothing else.
    monkeypatch.setattr(panel, "open", boom, raising=False)
    assert panel.drop_stale_lines(str(tmp_path), rows) == rows


def test_a_file_is_read_once_for_many_lines(tmp_path, monkeypatch):
    """Ten thousand findings in one file must not be ten thousand reads."""
    src = tmp_path / "big.py"
    src.write_text("\n".join("line %d" % i for i in range(1, 501)), encoding="utf-8")
    rows = [{"file": "big.py", "line": i, "text": "line %d" % i} for i in range(1, 501)]
    reads = {"n": 0}
    real = open

    def counting(path, *a, **k):
        if str(path).endswith("big.py"):
            reads["n"] += 1
        return real(path, *a, **k)

    # Module-scoped for the same reason, and so a failing assertion below cannot
    # leave a swapped global open behind for whatever test runs next.
    monkeypatch.setattr(panel, "open", counting, raising=False)
    kept = panel.drop_stale_lines(str(tmp_path), rows)
    assert len(kept) == 500
    assert reads["n"] == 1, "read the file %d times" % reads["n"]
