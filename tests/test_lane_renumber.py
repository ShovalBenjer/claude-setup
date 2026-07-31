"""Guards the 2026-07-30 lane renumber (ADR-0016).

Two things can rot here. The name table is duplicated in tools/bus/bus.py so that
oracle stays importable from any cwd, and a duplicated table drifts. And the letters
collide across the cutover, so a reader that drops the timestamp silently mislabels
every pre-cutover row instead of failing.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader, rel
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lanes = _load("_lanes_under_test", "tools/lib/lanes.py")
bus = _load("_bus_under_test", "tools/bus/bus.py")


class TestSchemeIsSingleSourced(unittest.TestCase):
    def test_bus_name_table_matches_lanes(self):
        """The copy in bus.py must equal the canonical table, key for key."""
        self.assertEqual(
            dict(bus.LANE_NAMES),
            dict(lanes.LANE_NAMES),
            "tools/bus/bus.py::LANE_NAMES drifted from tools/lib/lanes.py::LANE_NAMES; "
            "ADR-0016 permits the duplication only because this test pins it",
        )

    def test_bus_map_only_emits_current_letters(self):
        """No cwd may derive a letter that is not in the current scheme."""
        for prefix, letter in bus.LANE_MAP.items():
            self.assertIn(
                letter,
                lanes.LANE_NAMES,
                "LANE_MAP entry {!r} derives {!r}, which is not a scheme-2 lane"
                .format(prefix, letter),
            )

    def test_retired_letter_e_is_gone_from_derivation(self):
        """E was the content lane pre-renumber and must no longer be derivable."""
        self.assertNotIn("E", set(bus.LANE_MAP.values()))


class TestCutoverCollision(unittest.TestCase):
    def test_same_letter_resolves_differently_across_cutover(self):
        """The whole reason lanes.py exists."""
        before = lanes.resolve("B", "2026-07-29T23:59:59Z")
        after = lanes.resolve("B", "2026-07-30T00:00:01Z")
        self.assertEqual(before[0], "A")
        self.assertEqual(after[0], "B")
        self.assertNotEqual(before, after)

    def test_resolve_requires_a_timestamp(self):
        """A timestamp-free resolve must be a TypeError, not a silent default to now.

        If this ever becomes callable with one argument, every ledger reader that
        forgets the stamp mislabels history and nothing raises.
        """
        with self.assertRaises(TypeError):
            lanes.resolve("B")  # type: ignore[call-arg]

    def test_undated_row_is_treated_as_history(self):
        self.assertEqual(lanes.scheme_for(""), 1)

    def test_retired_concierge_does_not_become_the_harness(self):
        letter, name = lanes.resolve("A", "2026-07-28T00:00:00Z")
        self.assertEqual(letter, "RETIRED")
        self.assertIn("retired", name.lower())

    def test_every_scheme_1_letter_maps_to_a_named_scheme_2_lane(self):
        for old in ("B", "C", "D", "E"):
            new, name = lanes.resolve(old, "2026-07-01T00:00:00Z")
            self.assertIn(new, lanes.LANE_NAMES)
            self.assertEqual(name, lanes.LANE_NAMES[new])

    def test_lanes_selftest_passes(self):
        self.assertEqual(lanes.selftest(), 0)


class TestRealLedgersAreStillReadable(unittest.TestCase):
    def test_pre_cutover_harness_rows_resolve_to_a(self):
        """Spot-check against the real ledger rather than a fixture.

        refutations.jsonl carried ~396 rows stamped lane B before the renumber. Every
        one of them is a harness row and must resolve to A.
        """
        import json

        path = ROOT / "state" / "refutations.jsonl"
        if not path.exists():
            self.skipTest("state/refutations.jsonl absent")
        checked = 0
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            letter = row.get("lane")
            ts = row.get("ts") or row.get("timestamp") or ""
            if letter != "B" or not ts or ts >= lanes.SCHEME_2_CUTOVER:
                continue
            self.assertEqual(lanes.resolve(letter, ts)[0], "A")
            checked += 1
        if checked == 0:
            self.skipTest("no pre-cutover lane-B rows found to check")


if __name__ == "__main__":
    unittest.main()
