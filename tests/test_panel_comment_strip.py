"""Regression: a quotation of a dangerous call is not a dangerous call.

WHY THIS FILE EXISTS. The review domain has been waived four times. Across those
renewals one HIGH never moved: py-shell-true firing on `tools/map/codemap.py:66`,
whose matched line is a comment quoting

    subprocess.run("git " + args, shell=True)

inside an explanation of why that form is deliberately not used. The rule is right
about the characters and wrong about the world. That is L-2026-07-31-b, the gate
checking the ruled form instead of the property, and it is the third instance: the
first was sql-concat on this same file, the second was hooks_exist gating a hook
target on its file extension on 2026-08-03.

The cases below are chosen so this file can go red in BOTH directions. Stripping
comments is a change that makes a noisy checker quiet, which is exactly how a real
finding gets suppressed, so half of these exist to prove nothing real went silent.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PANEL = Path(__file__).resolve().parents[1] / "tools" / "review" / "panel.py"


def load_panel():
    spec = importlib.util.spec_from_file_location("panel_under_test", PANEL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ the fix

def test_quoted_call_inside_a_comment_is_not_code():
    """THE REGRESSION. The exact shape of codemap.py:66."""
    p = load_panel()
    line = '# never do: subprocess.run("git " + args, shell=True)'
    assert p.code_only(line, "py") == ""


def test_slash_comment_in_js_is_stripped():
    p = load_panel()
    assert p.code_only('// execSync(`rm ${x}`)', "js") == ""


# -------------------------------------------------- nothing real went silent

def test_a_real_call_with_a_trailing_comment_still_fires():
    """The code precedes the comment, so the code survives the strip."""
    p = load_panel()
    line = 'subprocess.run(cmd, shell=True)  # noqa: S602'
    assert "shell=True" in p.code_only(line, "py")


def test_a_hash_inside_a_string_is_not_a_comment():
    """`f"echo #{x}"` must not truncate the line and lose the real call."""
    p = load_panel()
    line = 'subprocess.run(f"echo #{x}", shell=True)'
    assert p.code_only(line, "py") == line


def test_an_escaped_quote_does_not_end_the_string():
    p = load_panel()
    line = "subprocess.run('it\\'s # fine', shell=True)"
    assert "shell=True" in p.code_only(line, "py")


def test_plain_code_is_returned_unchanged():
    p = load_panel()
    line = "    subprocess.run(cmd, shell=True)"
    assert p.code_only(line, "py") == line


def test_unknown_language_is_left_alone():
    """No opener registered means no strip, rather than a guessed one."""
    p = load_panel()
    line = "# this is not a comment in some language we do not model"
    assert p.code_only(line, "bin") == line


# ------------------------------------------------- the two comment readers

def test_the_comment_reading_checks_are_exempt():
    """todo-added and commented-code exist to read comments and must keep them.

    Guards the obvious over-reach: applying the strip everywhere would blind the
    two checks whose whole subject is the comment.
    """
    p = load_panel()
    # Membership is pinned exactly, not with `in`, because the failure mode that
    # actually happened was an INCOMPLETE set: the first draft had two entries and
    # the panel selftest reported MISS py-type-ignore. An exact assertion fails when
    # a new comment-reading check is registered without being listed.
    assert p.COMMENT_AWARE == {
        "todo-added", "commented-code", "py-type-ignore", "ts-escape",
    }


def test_every_comment_reading_check_is_actually_listed():
    """Derives the set instead of trusting it, which is how the missing two were found.

    Probes every registered check, in every language it declares, against strings
    that are entirely a comment. Any check that matches the raw string but not the
    stripped one depends on comment text and must be exempt.
    """
    import re
    p = load_panel()
    bodies = ["type: ignore", "TODO: x", "FIXME", "noqa", "nosec", "@ts-ignore",
              "eslint-disable-next-line", "def f():", "if x:", "const a = 1"]
    needed = set()
    for spec_ in p.PERSONAS.values():
        for cid, _sev, langs, pat, _why in spec_["checks"]:
            rx = re.compile(pat)
            for lang in (langs or list(p._LINE_COMMENT)):
                for op in p._LINE_COMMENT.get(lang, ()):
                    for b in bodies:
                        s = f"{op} {b}"
                        if rx.search(s) and not rx.search(p.code_only(s, lang)):
                            needed.add(cid)
    assert needed == p.COMMENT_AWARE, (
        f"comment-dependent but not exempt: {sorted(needed - p.COMMENT_AWARE)}; "
        f"exempt without needing it: {sorted(p.COMMENT_AWARE - needed)}"
    )


# ------------------------------------------------------- the stated residual

@pytest.mark.xfail(
    reason="KNOWN AND DOCUMENTED: the panel scans added diff lines, never whole "
           "files, so it cannot know it is inside a triple-quoted docstring. "
           "Pinned as xfail so the residual stays visible instead of reading as "
           "solved. Closing it needs file-level parsing, a different change.",
    strict=True,
)
def test_docstring_quotation_is_still_a_false_positive():
    p = load_panel()
    line = '    subprocess.run("git", shell=True)   <- inside a docstring'
    assert p.code_only(line, "py") == ""
