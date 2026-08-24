"""build_body is the whole projection: what it emits is what a reader sees on GitHub.

Written 2026-07-31, when the backlog gained priority and ingestion fields and the
publisher gained --update. Three things are worth pinning:

  1. DONE rendering. A task marked DONE in the JSON must arrive checked, because the
     entire point of --update is that finished work shows as finished on the board.
  2. The source attribution. The footer used to name
     state/github-backlog-2026-07-30.json unconditionally, so publishing any later
     backlog instructed every reader to edit a file it did not come from. That is the
     drift class the footer sentence itself warns about, committed by the warning.
  3. Header fields are optional. The 2026-07-30 backlog has no priority, session or
     estimate key on any epic, and re-publishing it must not crash or invent one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine" / "tools" / "ghpub"))
import publish_backlog as pb  # noqa: E402


BARE = {
    "title": "EPIC: something",
    "body_intro": "why this exists",
    "labels": ["epic"],
    "tasks": ["do the thing", "DONE 2026-07-31: did the other thing"],
}


def test_done_task_renders_checked_and_open_task_does_not():
    body = pb.build_body(BARE)
    assert "- [ ] do the thing" in body
    assert "- [x] DONE 2026-07-31: did the other thing" in body


def test_footer_names_the_source_actually_published():
    body = pb.build_body(BARE, "state/github-backlog-2026-07-31.json")
    assert "`state/github-backlog-2026-07-31.json`" in body
    assert "2026-07-30" not in body


def test_epic_without_optional_fields_still_renders():
    """Every epic in the 2026-07-30 backlog looks like this."""
    body = pb.build_body(BARE)
    assert body.startswith("why this exists")
    assert "Ingestion" not in body
    assert "Priority" not in body


def test_priority_and_ingestion_appear_before_the_intro():
    epic = dict(BARE, priority="P0", session="S1", estimate="20 min")
    body = pb.build_body(epic)
    head = body.splitlines()[0]
    assert "**P0**" in head
    assert "**Ingestion S1**" in head
    assert "~20 min" in head
    assert body.splitlines()[2] == "why this exists"


def test_partial_header_does_not_leave_a_dangling_separator():
    body = pb.build_body(dict(BARE, priority="P1"))
    assert body.splitlines()[0] == "**P1**"


def test_task_order_is_preserved():
    epic = dict(BARE, tasks=["first", "second", "third"])
    lines = [l for l in pb.build_body(epic).splitlines() if l.startswith("- [")]
    assert lines == ["- [ ] first", "- [ ] second", "- [ ] third"]


def test_the_live_backlog_files_render_without_error():
    """Guards the real sources, not a fixture: a bad key ships to GitHub."""
    root = Path(__file__).resolve().parents[2]
    sources = sorted((root / "knowledge" / "state").glob("github-backlog-*.json"))
    assert sources, "no backlog source found"
    import json
    for src in sources:
        data = json.loads(src.read_text(encoding="utf-8"))
        for epic in data["epics"]:
            body = pb.build_body(epic, str(src.name))
            assert epic["body_intro"] in body
            assert body.count("## Tasks") == 1
            for t in epic["tasks"]:
                assert t in body


# --------------------------------------------------------------- field sync
#
# Added 2026-07-31 with the field-sync path. The two live defects on Zion (a Lane
# option set retired by ADR-0016, and an Evidence field holding one identical
# string on 23 of 26 items) both existed because nothing wrote these fields, so
# nothing could regenerate them. These tests pin the resolver and the planner: the
# gh calls are a thin shell over `plan_field_writes`, so the plan is the oracle.

LANE = {
    "id": "F_lane", "name": "Lane", "type": "ProjectV2SingleSelectField",
    "options": [{"id": "o_a", "name": "A harness"}, {"id": "o_b", "name": "B resume"},
                {"id": "o_c", "name": "C learning"}, {"id": "o_d", "name": "D content"}],
}
INGEST = {
    "id": "F_ing", "name": "Ingestion", "type": "ProjectV2SingleSelectField",
    "options": [{"id": "s1", "name": "S1 25min"}, {"id": "s2", "name": "S2 45min"},
                {"id": "s3", "name": "S3 60min"}],
}
EVID = {
    "id": "F_ev", "name": "Evidence state", "type": "ProjectV2SingleSelectField",
    "options": [{"id": "e_u", "name": "unmeasured"}, {"id": "e_a", "name": "asserted"},
                {"id": "e_m", "name": "measured"}, {"id": "e_v", "name": "verified"},
                {"id": "e_r", "name": "refuted"}],
}
FIELDS = [LANE, INGEST, EVID]
EPIC = dict(BARE, lane="A harness", session="S2", evidence_state="measured")
ITEM = {"id": "I1", "title": BARE["title"]}


_UNSET = object()


def _plan(epics=_UNSET, fields=_UNSET, items=_UNSET):
    """Sentinel defaults, not `or`: an empty item list is a meaningful input here
    (it is the 'epic is not on the board' case) and `or` would swallow it."""
    return pb.plan_field_writes(
        [EPIC] if epics is _UNSET else epics,
        FIELDS if fields is _UNSET else fields,
        [ITEM] if items is _UNSET else items)


def _row(plan, field):
    return next(r for r in plan if r["field"] == field)


def test_exact_option_name_resolves():
    assert pb.resolve_option(LANE, "A harness")["id"] == "o_a"


def test_leading_token_resolves_the_backlog_shorthand():
    """The JSON says S2, the board says 'S2 45min'. Same fact, written twice."""
    assert pb.resolve_option(INGEST, "S2")["id"] == "s2"
    assert pb.resolve_option(LANE, "A")["id"] == "o_a"


def test_a_retired_lane_letter_does_not_resolve():
    """The exact defect: 'B harness' was the old label for what is now 'A harness'.
    It must fail loudly rather than land on 'B resume', which is a different lane."""
    assert pb.resolve_option(LANE, "B harness") is None
    assert _row(_plan([dict(EPIC, lane="B harness")]), "Lane")["action"] == "unresolved"


def test_ambiguous_prefix_returns_none_rather_than_guessing():
    amb = {"id": "F", "name": "X", "type": "ProjectV2SingleSelectField",
           "options": [{"id": "1", "name": "ship it"}, {"id": "2", "name": "ship later"}]}
    assert pb.resolve_option(amb, "ship") is None


def test_plan_sets_every_owned_field_for_a_fresh_item():
    plan = _plan()
    assert {r["field"] for r in plan} == {"Lane", "Ingestion", "Evidence state"}
    assert all(r["action"] == "set" for r in plan)
    assert _row(plan, "Lane")["option_id"] == "o_a"
    assert _row(plan, "Ingestion")["option_id"] == "s2"
    assert all(r["item_id"] == "I1" for r in plan)


def test_plan_is_idempotent_against_the_boards_current_values():
    """A second run must write nothing. See test_item_key_* for how gh keys these."""
    current = {"id": "I1", "title": BARE["title"], "lane": "A harness",
               "ingestion": "S2 45min", "evidence state": "measured"}
    assert all(r["action"] == "skip" for r in _plan(items=[current]))


def test_one_stale_value_is_the_only_write():
    current = {"id": "I1", "title": BARE["title"], "lane": "B resume",
               "ingestion": "S2 45min", "evidence state": "measured"}
    plan = _plan(items=[current])
    assert [r["field"] for r in plan if r["action"] == "set"] == ["Lane"]


def test_absent_keys_produce_no_rows_at_all():
    """An epic with none of the owned keys must not be written with defaults."""
    assert _plan([BARE]) == []


def test_a_field_missing_from_the_board_is_reported_not_dropped():
    plan = _plan(fields=[LANE, INGEST])
    assert _row(plan, "Evidence state")["action"] == "no-field"


def test_an_epic_not_on_the_board_is_reported_not_dropped():
    plan = _plan(items=[])
    assert {r["action"] for r in plan} == {"no-item"}
    assert all(r["item_id"] is None for r in plan)


def test_status_is_not_an_owned_field():
    """Status is a reaction to work happening and is hand-set on GitHub. One writer
    per field is the property that makes drift detectable."""
    assert "Status" not in dict(pb.FIELD_MAP).values()


def test_the_live_backlog_carries_the_keys_the_board_needs():
    root = Path(__file__).resolve().parents[2]
    import json
    data = json.loads((root / "knowledge" / "state" / "github-backlog-2026-07-31.json")
                      .read_text(encoding="utf-8"))
    for epic in data["epics"]:
        assert epic["lane"] == "A harness", epic["title"]
        assert epic["evidence_state"] in {"unmeasured", "asserted", "measured",
                                          "verified", "refuted"}
        assert pb.resolve_option(LANE, epic["lane"]) is not None
        assert pb.resolve_option(EVID, epic["evidence_state"]) is not None


def test_item_key_lowercases_only_the_first_character():
    """Measured against gh on 2026-07-31: a field named `ZZ probe` came back under
    the key `zZ probe`, not `zz probe`. A `.lower()` here reads None forever, which
    makes every run look like a needed write."""
    assert pb.item_key("ZZ probe") == "zZ probe"
    assert pb.item_key("Evidence state") == "evidence state"
    assert pb.item_key("Lane") == "lane"


def test_idempotence_uses_the_gh_key_not_the_lowercased_name():
    odd = {"id": "F", "name": "ZZ probe", "type": "ProjectV2SingleSelectField",
           "options": [{"id": "1", "name": "A harness"}]}
    epic = dict(BARE, lane="A harness")
    items = [{"id": "I1", "title": BARE["title"], "zZ probe": "A harness"}]
    monkey = tuple(("lane", "ZZ probe") if k == "lane" else (k, v)
                   for k, v in pb.FIELD_MAP)
    original, pb.FIELD_MAP = pb.FIELD_MAP, monkey
    try:
        assert pb.plan_field_writes([epic], [odd], items)[0]["action"] == "skip"
    finally:
        pb.FIELD_MAP = original


def test_exit_code_fails_on_unrepresentable_values_not_on_missing_items():
    assert pb.exit_code_for({"skip": 130}) == 0
    assert pb.exit_code_for({"set": 26, "skip": 104}) == 0
    assert pb.exit_code_for({"no-item": 26}) == 0, "first run of a new backlog"
    assert pb.exit_code_for({"unresolved": 1}) == 1, "the retired-Lane-letter case"
    assert pb.exit_code_for({"no-field": 1}) == 1
    assert pb.exit_code_for({"failed": 1}) == 1
