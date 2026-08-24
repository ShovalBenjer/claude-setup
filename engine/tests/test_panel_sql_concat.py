"""The sql-concat check must fire on assembled SQL and not on English prose.

Written 2026-07-30 after the review domain took its third waiver for the same class.
The waiver text on the first two blamed comments and docstrings. That reason was
wrong, and this file exists so the real one is executable rather than argued.

Measured on the 2026-07-30 tree, sql-concat produced three HIGH findings and none of
them contained SQL:

    docs/prior-art/dot-claude-skills-explain-simply.json:40
        "Delete ~380 lines (passive/jargon/acronym/length checks + their selftest)"
    docs/prior-art/dot-claude-skills-prove-implementation-scripts.json:75
        "Delete loop_audit.py heuristic (~180 lines), add ~50-line radon/scalene wrapper"
    tools/workspace/clean_oren_roast.py:93
        print("  delete .env: " + ("done" if rc == 0 else "FAILED " + out[:160]))

All three are a SQL verb used as an English verb, followed later on the line by a plus
sign and a word. The pattern asked for a verb and a concatenation and never asked for
SQL, so any sentence that deletes something and adds something else matched.

The fix requires a SQL clause keyword between the verb and the concatenation. What that
must NOT do is let a real injection through, so the first two tests here are the ones
that matter: they are the shapes the check exists to catch, and they are also what
panel.py's own cmd_selftest plants.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "review"))
import panel  # noqa: E402


def _sql_concat_pattern() -> str:
    for persona, spec in panel.PERSONAS.items():
        for cid, sev, langs, pat, why in spec["checks"]:
            if cid == "sql-concat":
                return pat
    raise AssertionError("sql-concat check is gone from PERSONAS")


def fires(line: str) -> bool:
    return bool(re.search(_sql_concat_pattern(), line))


# --------------------------------------------------------------- must still fire

def test_planted_selftest_defect_still_fires():
    """The exact line cmd_selftest plants. If this goes green the oracle is dead."""
    assert fires("  return db.query('SELECT * FROM users WHERE id = ' + id);")


def test_python_fstring_query_fires():
    assert fires('cur.execute(f"SELECT * FROM users WHERE name = {name}")')


def test_percent_format_query_fires():
    assert fires('cur.execute("SELECT id FROM t WHERE a = %s" % (val,))')


def test_update_with_concatenation_fires():
    assert fires('db.exec("UPDATE accounts SET balance = " + amount + " WHERE id = 1")')


def test_insert_with_interpolation_fires():
    assert fires('conn.query(`INSERT INTO logs (msg) VALUES (${payload})`)')


def test_delete_with_where_and_concat_fires():
    assert fires('db.run("DELETE FROM sessions WHERE token = " + token)')


# ------------------------------------------------------------ must not fire now

def test_english_delete_then_add_does_not_fire():
    """docs/prior-art/dot-claude-skills-explain-simply.json:40, verbatim."""
    assert not fires(
        '"migration_loc": "Delete ~380 lines (passive/jargon/acronym/length checks '
        '+ their selftest); add ~150-200 lines vendored Vale YAML"')


def test_english_delete_then_add_second_record_does_not_fire():
    """docs/prior-art/dot-claude-skills-prove-implementation-scripts.json:75, verbatim."""
    assert not fires(
        '"migration_loc": "Delete loop_audit.py heuristic (~180 lines), add ~50-line '
        'radon/scalene wrapper; add ~40 lines ingesting pytest-"')


def test_print_of_a_delete_result_does_not_fire():
    """tools/workspace/clean_oren_roast.py:93, verbatim."""
    assert not fires(
        'print("  delete .env: " + ("done" if rc == 0 else "FAILED " + out[:160]))')


def test_prose_about_selecting_does_not_fire():
    assert not fires("We select the best layer + the best k, then report both.")


def test_http_delete_verb_does_not_fire():
    """clean_oren_roast.py:85. A REST verb in an argv list is not a query."""
    assert not fires('"api", "-X", "DELETE", f"repos/{REPO}/contents/.env",')


def test_update_the_docs_does_not_fire():
    assert not fires("# update the map + the purpose row before committing")


# ------------------------------------------------------------------- end to end

def test_run_local_reports_the_planted_defect_and_not_the_prose():
    lines = [
        {"file": "src/db/api.ts", "line": 12,
         "text": "  return db.query('SELECT * FROM users WHERE id = ' + id);"},
        {"file": "src/notes.ts", "line": 3,
         "text": '  log("Delete 380 lines of checks + their selftest");'},
    ]
    hits = [f for f in panel.run_local(lines) if f["check"] == "sql-concat"]
    assert [h["line"] for h in hits] == [12], hits
