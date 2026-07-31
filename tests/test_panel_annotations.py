"""GitHub workflow-command emission from panel.py findings.

Written 2026-07-30 in place of adopting reviewdog. The adopt case was that we needed a
binary to get findings onto a pull request; reviewdog's own `github-annotations` reporter
emits the same string this function prints, so the payload never needed a translator.

What these tests protect, in order of what would actually break in CI:
  1. silence outside Actions, so local runs and the gate selftest are unaffected
  2. the exact command shape GitHub parses
  3. escaping, because an unescaped newline ends the command and an unescaped comma
     inside a property splits it, and both fail SILENTLY on GitHub's side
  4. the cap, and that exceeding it is announced rather than dropped quietly
"""
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "review"))
import panel  # noqa: E402


def emit(findings, monkeypatch, actions="true"):
    if actions is None:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    else:
        monkeypatch.setenv("GITHUB_ACTIONS", actions)
    buf = io.StringIO()
    n = panel.emit_github_annotations(findings, stream=buf)
    return n, buf.getvalue()


def f(sev="high", file="tools/x.py", line=7, why="boom", check="model-review"):
    return {"severity": sev, "file": file, "line": line, "why": why, "check": check}


class TestSilentOutsideActions:
    def test_no_output_when_env_absent(self, monkeypatch):
        n, out = emit([f()], monkeypatch, actions=None)
        assert (n, out) == (0, "")

    def test_no_output_when_env_is_not_true(self, monkeypatch):
        n, out = emit([f()], monkeypatch, actions="false")
        assert (n, out) == (0, "")


class TestCommandShape:
    def test_high_becomes_error_and_medium_becomes_warning(self, monkeypatch):
        n, out = emit([f(sev="high"), f(sev="medium", why="meh")], monkeypatch)
        assert n == 2
        assert "::error file=tools/x.py,line=7,title=panel/model-review::boom" in out
        assert "::warning file=tools/x.py,line=7,title=panel/model-review::meh" in out

    def test_low_severity_is_not_annotated(self, monkeypatch):
        n, out = emit([f(sev="low")], monkeypatch)
        assert (n, out) == (0, "")

    def test_severity_match_is_case_insensitive(self, monkeypatch):
        n, _ = emit([f(sev="HIGH")], monkeypatch)
        assert n == 1


class TestEscaping:
    """Each of these fails silently on GitHub if wrong, which is why they are here."""

    def test_newline_in_message_does_not_end_the_command(self, monkeypatch):
        _, out = emit([f(why="line one\nline two")], monkeypatch)
        assert "%0Aline two" in out
        assert out.count("\n") == 1  # exactly one real newline: the trailing one

    def test_carriage_return_is_escaped(self, monkeypatch):
        _, out = emit([f(why="a\r\nb")], monkeypatch)
        assert "%0D%0A" in out

    def test_percent_is_escaped_first_and_not_double_escaped(self, monkeypatch):
        _, out = emit([f(why="100% sure")], monkeypatch)
        assert "100%25 sure" in out
        assert "%2525" not in out

    def test_comma_and_colon_escaped_in_properties_only(self, monkeypatch):
        _, out = emit([f(file="a,b:c.py", why="plain, text: here")], monkeypatch)
        assert "file=a%2Cb%3Ac.py" in out          # property: escaped
        assert "::plain, text: here" in out        # message: left alone


class TestCapIsAnnouncedNotSilent:
    def test_cap_limits_annotations(self, monkeypatch):
        n, _ = emit([f(line=i) for i in range(25)], monkeypatch)
        assert n == panel.ANNOTATION_CAP

    def test_overflow_emits_a_notice_naming_the_count(self, monkeypatch):
        _, out = emit([f(line=i) for i in range(25)], monkeypatch)
        assert "::notice::" in out
        assert "15 high finding(s) not annotated" in out

    def test_no_notice_when_under_the_cap(self, monkeypatch):
        _, out = emit([f(line=i) for i in range(3)], monkeypatch)
        assert "::notice::" not in out


class TestMalformedInput:
    def test_missing_fields_do_not_raise(self, monkeypatch):
        n, out = emit([{"severity": "high"}], monkeypatch)
        assert n == 1
        assert "::error file=,line=0,title=panel/review::" in out

    def test_empty_findings(self, monkeypatch):
        assert emit([], monkeypatch) == (0, "")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
