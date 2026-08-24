"""The three boundary-contract bans must fire on the real form and stay quiet otherwise.

`dot-claude/rules/boundary-contracts.md` was cut from 5557 bytes to 488 by a sync on
2026-08-04 and restored the same day. The restored rule names three language-level
bans by example, and until 2026-08-05 none of `panel.py`'s checks matched any of
them: the rule was readable again and nothing could fail because of it.

These cases pin the two properties a regex ban needs. Firing on the real form is the
easy half and `panel.py selftest` already covers it. The half that decides whether a
check survives contact is the negative set, because a checker that also fires on
`a, b := json.Marshal(...)` gets waived within a week and this repository has three
recorded instances of exactly that.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("panel", REPO / "engine/tools/review/panel.py")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)

CHECKS = {c[0]: c for c in panel.PERSONAS["boundary"]["checks"]}


def _fires(check_id: str, line: str) -> bool:
    return re.search(CHECKS[check_id][3], line) is not None


def test_the_boundary_persona_exists_and_covers_the_named_bans():
    # The registry aspect `boundary` had no local rule set at all; four external
    # actors declared may_enact for it and nothing here could plan against them.
    assert "boundary" in panel.PERSONAS
    assert set(CHECKS) == {"go-discarded-marshal", "go-discarded-read",
                           "ts-unchecked-json-parse"}


def test_go_discarded_marshal_fires_on_the_form_the_rule_names():
    # Verbatim from boundary-contracts.md's own incident section.
    assert _fires("go-discarded-marshal", "\tpayload, _ := json.Marshal(req)")
    assert _fires("go-discarded-marshal", "data, _ = yaml.Unmarshal(b)")


def test_go_discarded_marshal_is_quiet_on_handled_errors():
    # Both values bound: the error is handled on the next line and this is correct code.
    assert not _fires("go-discarded-marshal", "\tpayload, err := json.Marshal(req)")
    # A blank in the FIRST slot discards the value, not the error, which is a
    # different (and legal) thing.
    assert not _fires("go-discarded-marshal", "\t_, err := json.Marshal(req)")
    # Prose about the ban must not trip the ban. This is the failure class the repo
    # logs as L-2026-07-31-b and it has already cost three review waivers.
    assert not _fires("go-discarded-marshal", "we never write x = json.Marshal(y) here")


def test_go_discarded_read_fires_and_stays_scoped():
    assert _fires("go-discarded-read", "\tout, _ := io.ReadAll(resp.Body)")
    assert _fires("go-discarded-read", "b, _ := ioutil.ReadFile(path)")
    assert not _fires("go-discarded-read", "\tout, err := io.ReadAll(resp.Body)")
    assert not _fires("go-discarded-read", "\t_, err := io.ReadAll(resp.Body)")


def test_json_parse_fires_on_a_bare_call():
    assert _fires("ts-unchecked-json-parse", "  const cfg = JSON.parse(raw);")


def test_json_parse_does_not_fire_on_a_member_call_of_another_object():
    # `myCodec.JSON.parse(x)` is somebody else's API, not the global.
    assert not _fires("ts-unchecked-json-parse", "  const v = codec.JSON.parse(raw);")


def test_json_parse_severity_is_medium_and_says_why():
    # Deliberately MEDIUM, not HIGH. The panel reads added diff lines and never holds
    # a whole file, so a `try {` two lines above is invisible to it. Claiming HIGH
    # would be asserting a fact the instrument cannot observe, and the message has to
    # tell the reader which check is theirs to do.
    _, sev, _, _, msg = CHECKS["ts-unchecked-json-parse"]
    assert sev == panel.MED
    assert "cannot see" in msg


def test_every_boundary_check_cites_the_rule_it_enforces():
    # A finding that does not name its rule is an opinion. All three point back at
    # boundary-contracts.md so a reader can go argue with the rule instead of the regex.
    for cid, spec_ in CHECKS.items():
        assert "boundary-contracts.md" in spec_[4], cid
