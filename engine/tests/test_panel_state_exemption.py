"""The self-referential exemption must cover the tools' OWN OUTPUT, not all of state/.

Found 2026-07-31 by a codex review, the first external review this repository ever
completed. `SELF_REFERENTIAL` carried a bare `^state/`, so every tracked source file
under the root `state/` directory was silently skipped while the panel reported a clean
verdict. `git ls-files "state/**/*.py"` returns real Python, so this was not theoretical.

The exemption exists for one reason, stated in panel.py's own comment: a review artifact
quotes source into its `snippet` field, and the next run reads those quotes back as
source, which measurably drove the high count 4 -> 7 across two runs. That justifies
exempting the artifacts the tools WRITE. It never justified exempting content.

These tests pin both halves, because the failure mode of over-correcting is the review
count exploding again on its own output.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine" / "tools" / "review"))
import panel  # noqa: E402

EXEMPT_CASES = [
    ("knowledge/state/reviews/deadbeef.json", "panel.py's own artifact, the original reason"),
    ("knowledge/state/reviews/nested/x.json", "still panel output one level down"),
    ("knowledge/state/gate-runs.jsonl", "the gate's own run ledger"),
    ("knowledge/state/bus.jsonl",
     "a machine-written ledger: a finding names nothing a human can fix"),
    ("knowledge/state/lessons.jsonl", "same"),
    ("knowledge/state/claims.jsonl", "same"),
    ("knowledge/state/compact-log.md", "a generated record, not source"),
    ("engine/tools/review/panel.py", "the reviewer reviewing itself"),
    ("engine/tools/gate/gate.py", "the gate"),
    ("payload/dot-claude/hooks/safety_gate.py", "a hook whose rules are credential patterns"),
]

REVIEWED_CASES = [
    ("knowledge/state/retired-2026-07-25/bin/generate-visual.py",
     "REAL tracked source under state/"),
    ("knowledge/state/retired-2026-07-25/bin/seed-meme-vectordb.py", "its sibling"),
    ("src/state/store.py", "ordinary application code in a very common layout"),
    ("app/state/reducer.ts", "the same, nested"),
    ("engine/tools/map/codemap.py", "a tool the panel does not write"),
]


class TestExemptedPathsStayExempt:
    @pytest.mark.parametrize("path,why", EXEMPT_CASES)
    def test_tool_output_is_not_reviewed(self, path, why):
        assert panel.SELF_REFERENTIAL.search(path), why


class TestContentIsReviewed:
    @pytest.mark.parametrize("path,why", REVIEWED_CASES)
    def test_content_under_state_is_reviewed(self, path, why):
        assert not panel.SELF_REFERENTIAL.search(path), (
            "{} was skipped. That is how tracked source went unreviewed for "
            "an unknown period: {}".format(path, why))


class TestTheRegressionSpecifically:
    def test_the_bare_state_prefix_is_gone(self):
        """The exact defect: `^state/` with nothing after it.

        Written as a source assertion rather than a behaviour one because a future
        edit could reintroduce the bare prefix alongside the narrow one and every
        behaviour test above would still pass while the hole reopened.
        """
        src = (Path(__file__).resolve().parents[2] / "engine" / "tools" / "review" / "panel.py")
        text = src.read_text(encoding="utf-8")
        i = text.find("SELF_REFERENTIAL = re.compile(")
        assert i != -1, "SELF_REFERENTIAL moved; this test needs updating"
        decl = text[i:i + 400]
        assert "SOURCE_EXT" in decl, \
            "the code-versus-ledger split is gone from the declaration"
        assert r"^knowledge/state/(?!" in decl, \
            "the negative lookahead is gone, so knowledge/state/ is unconditional again"
        # A bare `^knowledge/state/` means the prefix followed by anything that is NOT
        # the lookahead that carries the correction. `(?!` is the only acceptable suffix.
        assert not re.search(r"\^knowledge/state/(?!\(\?!)", decl), \
            "a bare ^knowledge/state/ is back, so tracked source under it is unreviewed again"

    def test_a_real_tracked_file_under_state_would_be_seen(self):
        """Guard against the exemption being correct in theory and wrong in fact."""
        assert not panel.SELF_REFERENTIAL.search(
            "state/retired-2026-07-25/bin/generate-visual.py")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
