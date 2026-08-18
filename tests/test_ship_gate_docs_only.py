"""The ship-gate downgrades a docs-only delta since the last PASS, blocks code.

Regression guard for the 2026-08-12/13 fixes. v1 classified only the WORKING diff,
which left two holes, both hit in practice on 2026-08-13: a clean tree whose only
delta since the gate was a committed docs regen still hard-blocked, and a dirty
docs-only tree sitting on committed-but-ungated code would have downgraded (a
bypass). v2 unions working changes with commits since the last full run's commit,
and requires that run to be a PASS. These tests pin the classifier, the baseline
rule, and both holes.
"""
from __future__ import annotations

import importlib.util
import json
import os

HOOK = os.path.join(os.path.dirname(__file__), "..", "dot-claude", "hooks", "ship_gate_stop.py")


def _load():
    spec = importlib.util.spec_from_file_location("_ship_gate", os.path.abspath(HOOK))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeGate:
    """Just enough gate surface for is_docs_only: setup_root, LEDGER, git()."""

    LEDGER = "gate-runs.jsonl"

    def __init__(self, root, status_lines, diff_since_baseline):
        self._root = root
        self._status = status_lines          # `git status --porcelain -z` records
        self._diff = diff_since_baseline     # paths for `diff --name-only <sha>..HEAD`

    def setup_root(self):
        return self._root

    def git(self, cmd, project):
        if cmd.startswith("status --porcelain -z"):
            return "\0".join(self._status)
        if cmd.startswith("diff --name-only HEAD"):
            return ""  # working tracked diff folded into status records for these tests
        if "..HEAD" in cmd:
            return "\n".join(self._diff)
        return ""


def _write_ledger(tmp_path, rows):
    p = tmp_path / "gate-runs.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return str(tmp_path)


def test_classifier_prose_and_code_paths():
    h = _load()
    assert h.classify_paths(["docs/x.md", "dot-claude/skills/a/SKILL.md", "README.md",
                             "state/gate-runs.jsonl"]) == []
    assert h.classify_paths(["dot-claude/hooks/ship_gate_stop.py"]) == \
        ["dot-claude/hooks/ship_gate_stop.py"]
    assert h.classify_paths(["docs/x.md", "tools/gate/gate.py"]) == ["tools/gate/gate.py"]


def test_suffix_list_stays_tight():
    h = _load()
    forbidden = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".go", ".rs"}
    assert not (set(h._DOC_ONLY_SUFFIXES) & forbidden)


def test_committed_docs_since_pass_downgrades(tmp_path):
    """Hole 1: clean tree, docs-only commits since a PASS -> docs_only True."""
    h = _load()
    root = _write_ledger(tmp_path, [
        {"project_path": "/p", "commit": "abc123", "verdict": "PASS"}])
    g = FakeGate(root, status_lines=[], diff_since_baseline=["docs/CODEBASE-MAP.md", "docs/DOCMAP.md"])
    docs_only, code = h.is_docs_only(g, "/p")
    assert docs_only is True and code == []


def test_dirty_docs_over_ungated_code_blocks(tmp_path):
    """Hole 2 (the bypass): dirty doc on top of committed code -> blocks."""
    h = _load()
    root = _write_ledger(tmp_path, [
        {"project_path": "/p", "commit": "abc123", "verdict": "PASS"}])
    g = FakeGate(root, status_lines=[" M docs/notes.md"],
                 diff_since_baseline=["tools/gate/gate.py"])
    docs_only, code = h.is_docs_only(g, "/p")
    assert docs_only is False and code == ["tools/gate/gate.py"]


def test_no_baseline_or_fail_baseline_blocks(tmp_path):
    """No run ever, or a FAIL baseline: never downgrade."""
    h = _load()
    # no ledger at all
    g = FakeGate(str(tmp_path), status_lines=[" M docs/x.md"], diff_since_baseline=[])
    assert h.is_docs_only(g, "/p") == (False, [])
    # FAIL baseline
    root = _write_ledger(tmp_path, [
        {"project_path": "/p", "commit": "abc123", "verdict": "FAIL"}])
    g2 = FakeGate(root, status_lines=[" M docs/x.md"], diff_since_baseline=["docs/x.md"])
    assert h.is_docs_only(g2, "/p") == (False, [])


def test_empty_delta_since_pass_blocks(tmp_path):
    """Identical tree to the PASS run: nothing changed, downgrade not needed and
    not granted (the green fingerprint path handles this case upstream)."""
    h = _load()
    root = _write_ledger(tmp_path, [
        {"project_path": "/p", "commit": "abc123", "verdict": "PASS"}])
    g = FakeGate(root, status_lines=[], diff_since_baseline=[])
    assert h.is_docs_only(g, "/p") == (False, [])
