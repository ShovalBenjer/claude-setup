"""Oracle for tools/slop_lint.py, including the item-2 check() adapter
(docs/taste.md, 2026-08-24, "global rule-enforcement oracle" migration).

No test file existed for this checker before this commit; it was only ever
exercised indirectly through the gate's docs domain running the CLI against
real files, with no pinned expectations of its own. Writing this alongside
the check() migration closes that gap rather than leaving it, and pins the
one real finding the migration surfaced: `\\bdelve\\b` (word-boundary regex)
does not match "delves" or any other inflected form, a pre-existing gap in
scan()'s BANNED_PHRASES that check() correctly reproduces rather than fixes,
since fixing it silently inside a migration commit would hide a scope
decision (fix the regex vs keep behavior identical) that belongs to its own
commit, not this one.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "lib"))
import slop_lint  # noqa: E402


class ScanBaseline(unittest.TestCase):
    """scan()'s existing behavior, pinned so check() can be shown to wrap it
    exactly rather than reimplementing and silently diverging."""

    def test_banned_phrase_exact_form_matches(self):
        hits = slop_lint.scan("this will delve into the topic")
        kinds = [h[0] for h in hits]
        self.assertIn("phrase", kinds)

    def test_banned_phrase_inflected_form_does_not_match(self):
        # The known gap: \bdelve\b requires the exact word, "delves" has a
        # trailing character after the word-boundary match point.
        hits = slop_lint.scan("this delves into the topic")
        kinds = [h[0] for h in hits]
        self.assertNotIn("phrase", kinds)

    def test_spaced_em_dash_flagged(self):
        hits = slop_lint.scan("a claim — with a dash")
        self.assertTrue(any(h[0] == "em/en-dash" for h in hits))

    def test_hyphen_in_compound_not_flagged(self):
        hits = slop_lint.scan("a well-known compound-word case")
        self.assertFalse(any(h[0] == "em/en-dash" for h in hits))

    def test_clean_text_produces_no_hits(self):
        self.assertEqual(slop_lint.scan("a plain, ordinary sentence with no issues"), [])

    def test_line_numbers_are_1_indexed_and_correct(self):
        hits = slop_lint.scan("line one\nline two has a delve\nline three")
        phrase_hits = [h for h in hits if h[0] == "phrase"]
        self.assertEqual(phrase_hits[0][2], 2)


class CheckAdapter(unittest.TestCase):
    """check(diff_or_text) -> list[Finding], the item-2 shared-signature entry
    point. Must agree with scan() exactly: same hits, same lines, nothing
    added or dropped in translation to Finding."""

    def test_check_returns_finding_list(self):
        results = slop_lint.check("a claim — with a dash")
        self.assertEqual(len(results), 1)
        f = results[0]
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.line, 1)
        self.assertEqual(f.source, "local")

    def test_check_agrees_with_scan_on_hit_count(self):
        text = "delve into it — twice — and you're absolutely right"
        self.assertEqual(len(slop_lint.check(text)), len(slop_lint.scan(text)))

    def test_check_clean_text_returns_empty_list(self):
        self.assertEqual(slop_lint.check("a plain, ordinary sentence"), [])

    def test_check_carries_optional_file_locator(self):
        results = slop_lint.check("a claim — with a dash", file="docs/example.md")
        self.assertEqual(results[0].file, "docs/example.md")

    def test_check_default_file_is_empty_string_not_placeholder(self):
        results = slop_lint.check("a claim — with a dash")
        self.assertEqual(results[0].file, "")

    def test_check_checker_name_is_namespaced_by_kind(self):
        results = slop_lint.check("a claim — with a dash")
        self.assertTrue(results[0].checker.startswith("slop_lint."))


if __name__ == "__main__":
    unittest.main()
