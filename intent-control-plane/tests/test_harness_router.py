"""Golden tests for the prompt router decision + render logic.

Pure (no corpus I/O): they freeze the behavior verified byte-for-byte against the
old embedded-python hook on 2026-07-09 (low-confidence injection, skill/persona
routing, the trivial-prompt silence, en/he uncertainty).
"""
from __future__ import annotations

import sqlite3

from intent_control_plane.harness.router import (
    build_context,
    corpus_snippets,
    rank_by_usage,
    render_context,
    route,
    routed_skill_names,
    skill_usage_counts,
)


def _make_sessions_db(db_path, invocations) -> None:
    """Build a real sessions.db session_events table (matches the live schema)."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "create table session_events ("
        " id integer primary key autoincrement, session_id text not null,"
        " fired_at text not null, event_type text not null, detail text)"
    )
    for skill in invocations:
        conn.execute(
            "insert into session_events(session_id, fired_at, event_type, detail)"
            " values ('s', '2026-07-10T00:00:00Z', 'skill_invoke', ?)",
            (skill,),
        )
    conn.commit()
    conn.close()


def _make_corpus(db_path) -> None:
    """Build a minimal real FTS5 corpus matching the live schema (no mocks)."""
    conn = sqlite3.connect(db_path)
    conn.execute("create table chunks (id integer primary key, source_id text, locator text, text text)")
    conn.execute("create virtual table corpus_fts using fts5(chunk_id unindexed, title, locator, text)")
    rows = [
        (1, "local-shoval-docs", "/home/shovalbe/docs/Harness-Engineering.md",
         "Harness engineering wraps the agent with sensors and guides for reliability."),
        (2, "local-shoval-docs", "/home/shovalbe/docs/Context-Rot.md",
         "Context rot degrades performance past 100k tokens so use just in time loading."),
        (3, "other-source", "/x/Other.md",
         "harness content from an unrelated source that the source_id filter must exclude."),
        (4, "local-shoval-docs", "/home/shovalbe/docs/Dash-Test.md",
         "reliability first — then speed, an en dash – too."),  # noqa: RUF001 - test fixture on purpose
    ]
    for rid, src, loc, txt in rows:
        conn.execute("insert into chunks(id, source_id, locator, text) values (?,?,?,?)", (rid, src, loc, txt))
        conn.execute(
            "insert into corpus_fts(chunk_id, title, locator, text) values (?,?,?,?)",
            (rid, loc.split("/")[-1], loc, txt),
        )
    conn.commit()
    conn.close()


def test_corpus_snippets_returns_name_and_content(tmp_path):
    db = tmp_path / "corpus.sqlite3"
    _make_corpus(db)
    hits = corpus_snippets("harness reliability", db)
    assert hits, "expected at least one hit"
    assert hits[0]["name"] == "Harness-Engineering.md"
    assert "harness" in hits[0]["snippet"].lower()  # content, not just a filename
    assert all(set(h) == {"name", "path", "snippet"} for h in hits)


def test_corpus_snippets_excludes_other_sources_and_caps_three(tmp_path):
    db = tmp_path / "corpus.sqlite3"
    _make_corpus(db)
    hits = corpus_snippets("harness reliability context loading speed", db)
    names = [h["name"] for h in hits]
    assert "Other.md" not in names  # source_id filter
    assert len(hits) <= 3
    assert len(names) == len(set(names))  # deduped


def test_corpus_snippets_normalizes_dashes(tmp_path):
    db = tmp_path / "corpus.sqlite3"
    _make_corpus(db)
    hits = corpus_snippets("reliability speed", db)
    for h in hits:
        assert "—" not in h["snippet"]  # no em-dash in emitted context
        assert "–" not in h["snippet"]  # noqa: RUF001 - asserting the en-dash is absent


def test_corpus_snippets_fails_closed_on_missing_db(tmp_path):
    assert corpus_snippets("anything", tmp_path / "nope.sqlite3") == []


def test_render_includes_doc_previews_when_snippets_present():
    ctx = render_context(
        {"hits": [], "personas": ["Mayor Opus"], "low_conf": False},
        ["a.md"],
        [{"name": "a.md", "snippet": "the preview text"}],
    )
    assert "- doc previews" in ctx
    assert "a.md: the preview text" in ctx


def test_render_no_previews_when_snippets_empty():
    ctx = render_context({"hits": [], "personas": ["Mayor Opus"], "low_conf": False}, ["a.md"], [])
    assert "doc previews" not in ctx


def test_build_context_surfaces_snippet_content(tmp_path):
    db = tmp_path / "corpus.sqlite3"
    _make_corpus(db)
    ctx = build_context("how does harness engineering improve reliability of the agent", db)
    assert ctx is not None
    assert "- relevant docs (corpus, ~/docs): Harness-Engineering.md" in ctx
    assert "- doc previews" in ctx
    assert "Harness engineering" in ctx  # actual content reached the model, not just a name


def test_rank_by_usage_orders_by_count():
    assert rank_by_usage(["a", "b", "c"], {"c": 5, "a": 2}) == ["c", "a", "b"]


def test_rank_by_usage_empty_counts_is_identity():
    assert rank_by_usage(["a", "b", "c"], {}) == ["a", "b", "c"]


def test_rank_by_usage_ties_preserve_router_order():
    # a and b tie on count 1, c unseen (0), so router order holds among ties
    assert rank_by_usage(["a", "b", "c"], {"a": 1, "b": 1}) == ["a", "b", "c"]


def test_skill_usage_counts_reads_skill_invoke_rows(tmp_path):
    db = tmp_path / "sessions.db"
    _make_sessions_db(db, ["reground", "reground", "tdd"])
    counts = skill_usage_counts(db)
    assert counts == {"reground": 2, "tdd": 1}


def test_skill_usage_counts_fails_closed_on_missing_db(tmp_path):
    assert skill_usage_counts(tmp_path / "nope.db") == {}


def test_build_context_reorders_candidate_skills_by_measured_usage(tmp_path):
    corpus = tmp_path / "corpus.sqlite3"
    _make_corpus(corpus)
    usage = tmp_path / "sessions.db"
    _make_sessions_db(usage, ["tdd"] * 9)  # tdd is heavily used
    ctx = build_context("review the tests before merge please now team", corpus, usage)
    assert ctx is not None
    # tdd was a lower-priority router hit but floats to the front by measured usage
    skills_line = next(line for line in ctx.splitlines() if line.startswith("- candidate skills:"))
    assert skills_line.startswith("- candidate skills: tdd")


def test_routed_skill_names_includes_the_wired_skills():
    # Guards the 2026-07-09 wiring: these were the router-unreachable skills, plus advisor.
    names = routed_skill_names()
    for skill in ["LTMD", "persona", "meme-control", "ponytail-review", "ponytail-help", "red-team", "advisor"]:
        assert skill in names, skill


def test_route_trivial_is_silent():
    assert route("ok thanks") is None
    assert route("") is None


def test_route_low_confidence_flags():
    decision = route("idk, im lost here, is this right?")
    assert decision is not None
    assert decision["low_conf"] is True


def test_route_hebrew_uncertainty_flags():
    decision = route("אני לא בטוח מה לעשות עם זה")
    assert decision is not None
    assert decision["low_conf"] is True


def test_route_normal_substantive_has_hits_and_no_lowconf():
    decision = route("deploy the widgora dashboard to production and run the pipeline for me now")
    assert decision is not None
    assert decision["low_conf"] is False
    assert "prod-deploy-rules" in decision["hits"]


def test_route_short_prompt_with_a_hit_still_fires():
    # under 12 words, but a route matches, so it is not silent
    decision = route("review this PR before merge")
    assert decision is not None
    assert "review" in decision["hits"]


def test_render_confidence_block_only_when_low_conf():
    low = render_context({"hits": [], "personas": ["Mayor Opus"], "low_conf": True}, [])
    assert "CONFIDENCE CHECK" in low
    assert "/advisor" in low
    normal = render_context({"hits": ["review"], "personas": ["Review Board"], "low_conf": False}, [])
    assert "CONFIDENCE CHECK" not in normal
    assert "- candidate skills: review" in normal


def test_render_docs_line_only_when_docs_present():
    with_docs = render_context({"hits": [], "personas": ["Mayor Opus"], "low_conf": False}, ["a.md", "b.md"])
    assert "- relevant docs (corpus, ~/docs): a.md, b.md" in with_docs
    without = render_context({"hits": [], "personas": ["Mayor Opus"], "low_conf": False}, [])
    assert "relevant docs" not in without


def test_build_context_survives_missing_corpus(tmp_path):
    # corpus_docs must fail closed (no docs line) when the DB is unreachable.
    ctx = build_context(
        "deploy to production and run the pipeline now for the widget dashboard please",
        tmp_path / "does-not-exist.sqlite3",
    )
    assert ctx is not None
    assert ctx.startswith("TASK ROUTER (deterministic nudge")
    assert "relevant docs" not in ctx
