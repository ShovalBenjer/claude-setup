"""E-row enforcement tests: anatomy/e-rows/ for claude-setup.

Each E-row's hook is proven against a real git diff, the way the panel
itself sees it. Conventions follow the other test_panel_* files:
tools/review on sys.path, `panel.added_lines` over a temp repo.

E-0001  undeclared tradeoff fails the panel            (issue #374)
E-0002  high-risk prompt/schema/evidence edits need a
        declared regression scope                     (issue #373)
E-0003  memoized review decisions, fingerprint-guarded
        keys, anti-stale expiry                       (issue #372)
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "review"))
import panel  # noqa: E402
import e_rows  # noqa: E402


def _sh(cmd, cwd):
    import subprocess
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 0, p.stderr


def _diff(files: dict[str, str]):
    """Build a temp git repo whose HEAD diff adds `files`; return added lines."""
    td = tempfile.mkdtemp()
    _sh("git init -q .", td)
    _sh("git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base", td)
    for name, body in files.items():
        full = os.path.join(td, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(body if body.endswith("\n") else body + "\n")
    return panel.added_lines(td, "HEAD")


def _checks(lines):
    return {(f["persona"], f["check"]) for f in panel.run_local(lines)}


# ------------------------------------------------------------------ E-0001

TRADEOFF_WEAKEN = "    requests.get(url, verify=False)\n"
TRADEOFF_TUNE = "from functools import lru_cache\n\n@lru_cache(maxsize=512)\ndef render(template_id):\n    ...\n"


def test_e0001_fires_on_guard_weakening_plus_perf_tuning():
    lines = _diff({"svc/handler.py": TRADEOFF_WEAKEN + TRADEOFF_TUNE})
    found = [f for f in panel.run_local(lines)
             if f["check"] == "undeclared-tradeoff"]
    assert len(found) == 1
    assert found[0]["severity"] == e_rows.HIGH
    assert found[0]["persona"] == "ops_release"


def test_e0001_suppressed_by_tradeoff_record():
    lines = _diff({"svc/handler.py": TRADEOFF_WEAKEN + TRADEOFF_TUNE,
                   "TRADEOFFS.md": ("tradeoff: accepts +80ms p95 for a "
                                    "stricter identity check\n")})
    assert ("ops_release", "undeclared-tradeoff") not in _checks(lines)


def test_e0001_guard_weakening_alone_is_not_a_tradeoff():
    lines = _diff({"svc/handler.py": TRADEOFF_WEAKEN})
    assert ("ops_release", "undeclared-tradeoff") not in _checks(lines)


def test_e0001_perf_tuning_alone_is_not_a_tradeoff():
    lines = _diff({"svc/handler.py": TRADEOFF_TUNE})
    assert ("ops_release", "undeclared-tradeoff") not in _checks(lines)


def test_e0001_prose_about_weakening_does_not_fire():
    lines = _diff({"docs/notes.md": (
        "We disabled verification to improve latency.\n"
        "The lru_cache now memoizes renders.\n")})
    assert ("ops_release", "undeclared-tradeoff") not in _checks(lines)


# ------------------------------------------------------------------ E-0002

SCHEMA_EDIT = '{\n  "properties": {\n    "verdict": {"type": "string"}\n  },\n  "required": ["verdict"]\n}\n'
ATTENTION_EDIT = "focus on the bounding box region of the input image\n"


def test_e0002_schema_structure_edit_needs_regression_scope():
    lines = _diff({"contracts/output.schema.json": SCHEMA_EDIT})
    found = [f for f in panel.run_local(lines)
             if f["check"] == "high-risk-edit-no-regression-scope"]
    assert len(found) == 1
    assert found[0]["severity"] == e_rows.MED
    assert found[0]["persona"] == "correctness"


def test_e0002_attention_directive_edit_needs_regression_scope():
    lines = _diff({"prompts/vision.prompt.md": ATTENTION_EDIT})
    found = [f for f in panel.run_local(lines)
             if f["check"] == "high-risk-edit-no-regression-scope"]
    assert len(found) == 1


def test_e0002_regression_scope_record_satisfies():
    lines = _diff({"contracts/output.schema.json": SCHEMA_EDIT,
                   "contracts/CHANGELOG.md": (
                       "regression-scope: contracts/*, prompts/*, "
                       "evidence fixtures\n")})
    assert ("correctness", "high-risk-edit-no-regression-scope") \
        not in _checks(lines)


def test_e0002_test_in_diff_satisfies():
    lines = _diff({"contracts/output.schema.json": SCHEMA_EDIT,
                   "tests/test_output_schema.py": "def test_required():\n    assert True\n"})
    assert ("correctness", "high-risk-edit-no-regression-scope") \
        not in _checks(lines)


def test_e0002_ordinary_code_edit_is_out_of_scope():
    lines = _diff({"svc/handler.py": "def render(t):\n    return t.strip()\n"})
    assert ("correctness", "high-risk-edit-no-regression-scope") \
        not in _checks(lines)


# ------------------------------------------------------------------ E-0003

def _cache(tmp_path):
    return e_rows.ReviewDecisionCache(str(tmp_path / "decision-cache.json"))


def _fp():
    return e_rows.registry_fingerprint(panel.PERSONAS)


def test_e0003_same_diff_hits(tmp_path):
    lines = [{"file": "a.py", "line": 1, "text": "x = 1"}]
    c = _cache(tmp_path)
    assert c.lookup(lines, _fp()) is None
    c.store(lines, _fp(), "pass", [{"check": "x"}])
    hit = c.lookup(lines, _fp())
    assert hit is not None
    assert hit["verdict"] == "pass"
    assert hit["findings"] == [{"check": "x"}]


def test_e0003_registry_change_expires_entries(tmp_path):
    lines = [{"file": "a.py", "line": 1, "text": "x = 1"}]
    c = _cache(tmp_path)
    c.store(lines, _fp(), "pass", [])
    personas2 = dict(panel.PERSONAS)
    personas2["zzz_new"] = {"checks": [("zzz-check", "high", [], r"zzz", "why")]}
    assert c.lookup(lines, e_rows.registry_fingerprint(personas2)) is None


def test_e0003_different_diff_misses(tmp_path):
    c = _cache(tmp_path)
    c.store([{"file": "a.py", "line": 1, "text": "x = 1"}], _fp(), "pass", [])
    assert c.lookup([{"file": "a.py", "line": 1, "text": "x = 2"}],
                    _fp()) is None


def test_e0003_corrupt_cache_is_a_miss_not_a_crash(tmp_path):
    p = tmp_path / "decision-cache.json"
    p.write_text("not json{", encoding="utf-8")
    c = e_rows.ReviewDecisionCache(str(p))
    assert c.lookup([{"file": "a.py", "line": 1, "text": "x = 1"}],
                    _fp()) is None


def test_e0003_oldest_entry_evicted_at_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(e_rows, "CACHE_MAX_ENTRIES", 2)
    c = _cache(tmp_path)
    first = [{"file": "a.py", "line": 1, "text": "x = 1"}]
    c.store(first, _fp(), "pass", [])
    c.store([{"file": "b.py", "line": 1, "text": "y = 1"}], _fp(), "pass", [])
    c.store([{"file": "c.py", "line": 1, "text": "z = 1"}], _fp(), "pass", [])
    assert c.lookup(first, _fp()) is None


def test_e0003_key_ignores_diff_order_and_line_numbers():
    a = [{"file": "b.py", "line": 9, "text": "y = 1"},
         {"file": "a.py", "line": 3, "text": "x = 1"}]
    b = [{"file": "a.py", "line": 1, "text": "x = 1"},
         {"file": "b.py", "line": 2, "text": "y = 1"}]
    assert e_rows.canonical_key(a) == e_rows.canonical_key(b)
