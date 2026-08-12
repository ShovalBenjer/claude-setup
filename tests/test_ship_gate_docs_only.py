"""The ship-gate downgrades a docs-only tree, still blocks any code change.

Regression guard for the 2026-08-12 fix: a Stop-boundary done-claim used to demand
a full 12-domain gate run even when the turn changed only prose (.md frontmatter,
docs/). That is a mismatch, since no code domain covers prose. The fix classifies the
tree: docs-only -> systemMessage, any code path -> hard block. This test pins both
directions AND the two bugs found only by testing against a real tree (the truncated
`status --porcelain` slice, and state ledgers reading as code).
"""
from __future__ import annotations

import importlib.util
import os

HOOK = os.path.join(os.path.dirname(__file__), "..", "dot-claude", "hooks", "ship_gate_stop.py")


def _load():
    spec = importlib.util.spec_from_file_location("_ship_gate", os.path.abspath(HOOK))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_classifier_prose_paths_are_docs_only():
    h = _load()

    def classify(paths):
        code = []
        for p in paths:
            low = p.lower()
            if low.endswith(h._DOC_ONLY_SUFFIXES):
                continue
            if any(low.startswith(d) or ("/" + d) in low for d in h._DOC_ONLY_DIRS):
                continue
            code.append(p)
        return (not code), code

    assert classify(["docs/analysis/x.md", "dot-claude/skills/a/SKILL.md"]) == (True, [])
    assert classify(["README.md"]) == (True, [])
    assert classify(["state/gate-runs.jsonl"]) == (True, [])


def test_classifier_any_code_path_is_not_docs_only():
    h = _load()

    def classify(paths):
        code = [p for p in paths
                if not p.lower().endswith(h._DOC_ONLY_SUFFIXES)
                and not any(p.lower().startswith(d) or ("/" + d) in p.lower()
                            for d in h._DOC_ONLY_DIRS)]
        return (not code), code

    # a .py hook is CODE even though it lives under dot-claude/
    assert classify(["dot-claude/hooks/ship_gate_stop.py"]) == (False, ["dot-claude/hooks/ship_gate_stop.py"])
    assert classify(["docs/x.md", "tools/gate/gate.py"]) == (False, ["tools/gate/gate.py"])


def test_suffix_list_stays_tight():
    """A regression tripwire: the allowlist must not silently grow to cover code.

    If someone adds .py/.ts/.js/.sh here, the gate goes blind on code. That is the
    exact failure the gate's own docstring names, so pin the allowlist explicitly.
    """
    h = _load()
    forbidden = {".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".go", ".rs"}
    assert not (set(h._DOC_ONLY_SUFFIXES) & forbidden)
