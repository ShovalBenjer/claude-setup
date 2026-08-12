"""Mutations for tools/map/codemap.py.

codemap.py owns TWO required gate domains, `codemap` and `prior_art`, and until
2026-07-27 it had no selftest verb at all. Its argument parser accepted only
write / check / prior-art, so tools/audit/mutate.py had nothing to run and every
check in the file was unfalsified. A check that can never fail and a check that
never fires look identical from outside, which is exactly the condition this
whole audit tool exists to detect.

The guarantees re-broken here are the ones a reader of the map depends on:
a pipe inside a purpose must not invent a table column, a rendered row must be
parseable by the checker that reads it back, and a drift report must NAME the
differing rows rather than saying only that something drifted.
"""

TARGET = "tools/map/codemap.py"
ARGV = ["selftest"]

MUTATIONS = [
    # ---- table escaping -------------------------------------------------
    ("a pipe in a purpose is backslash-escaped instead of entity-escaped",
     "the exact defect the comment above cell() warns about: a backslash-escaped "
     "pipe still contains a pipe, so the row gains a column and every later "
     "column shifts",
     'return trimmed.replace("|", "&#124;")',
     'return trimmed.replace("|", "\\\\|")'),

    ("purposes stop being escaped at all",
     "one directory whose README says 'takes a|b' silently corrupts the table",
     'return trimmed.replace("|", "&#124;")',
     'return trimmed'),

    ("an over-long purpose is no longer capped",
     "RENDER_CAP stops applying, so one verbose README makes the map unreadable",
     'trimmed = text if len(text) <= RENDER_CAP else text[:RENDER_CAP - 3].rstrip() + "..."',
     'trimmed = text'),

    ("a truncated purpose stops being marked as truncated",
     "the reader cannot tell a short purpose from a cut-off one, so a sentence "
     "that changes meaning when cut reads as the whole statement",
     'text[:RENDER_CAP - 3].rstrip() + "..."',
     'text[:RENDER_CAP - 3].rstrip()'),

    # ---- render / parse round trip --------------------------------------
    ("the row parser stops matching rendered rows",
     "check() reads the map back with this regex. If it matches nothing, every "
     "comparison is empty-vs-empty and the domain passes on a map that is wrong",
     r'm = re.match(r"\| `([^`]+)` \| (.*) \|$", line)',
     r'm = re.match(r"^NEVER-MATCHES `([^`]+)` \| (.*) \|$", line)'),

    ("the parser keeps the path but drops the rest of the row",
     "a comparison that only ever sees directory names cannot detect a changed "
     "purpose, which is most of what drift actually is",
     'rows[m.group(1)] = m.group(2)',
     'rows[m.group(1)] = ""'),

    ("the header stops counting undocumented directories",
     "that count is the single number the map exists to report",
     '"{} directories, {} tracked files, {} without a stated purpose.".format(\n'
     '            len(dirs), sum(d.files for d in dirs), len(undoc)),',
     '"{} directories, {} tracked files.".format(\n'
     '            len(dirs), sum(d.files for d in dirs)),'),

    # ---- problem reporting ----------------------------------------------
    ("undocumented directories stop being reported",
     "the check goes quiet on the one condition it was written for",
     'if state["undocumented"]:',
     'if False:'),

    ("registry rows naming a missing directory stop being reported",
     "a row that outlives its directory keeps asserting a purpose nobody can open",
     'if state["stale_rows"]:',
     'if False:'),

    ("shadow rows stop being reported",
     "a registry row beside a self-documenting directory is a copy that drifts, "
     "whether or not it agrees today",
     'if state["shadow_rows"]:',
     'if False:'),

    ("a drifted map stops naming which rows differ",
     "the comment on this branch says a check that reports a mismatch without "
     "saying which one sends the reader to regenerate and diff by hand, and a "
     "reader who does that twice stops reading the check",
     'detail += "\\n  {}: {}".format(label, ", ".join(rows[:12]))',
     'detail += ""'),

    ("a missing map is reported as merely drifted",
     "'not what the repository implies' sends the reader looking for a difference "
     "in a file that does not exist",
     '"missing" if not state["map_present"] else',
     '"not missing" if not state["map_present"] else'),

    ("a clean state starts reporting a problem",
     "a check that fires on a clean tree is noise, and noise is how a gate stops "
     "being read at all",
     '    out = []\n    if state["undocumented"]:',
     '    out = ["always a problem"]\n    if state["undocumented"]:'),

    # ---- absorption schema, ABSORB-01 and ABSORB-09 ----------------------
    # These four break the checks added when the prior-art schema gained the
    # ability to say what an evaluation took from its alternatives. The row that
    # asked for them named the root cause exactly: absorption was
    # unrepresentable, therefore unchecked, therefore it never happened. A
    # schema field with no oracle would leave it exactly there.
    ("a record with no verdict_class stops being faulted",
     "the enumerated field goes back to optional, so 'how many components did we "
     "decide to replace' costs 41 file reads again and the answer decays from "
     "the next record onward",
     '    klass = rec.get("verdict_class")\n    if not klass:',
     '    klass = rec.get("verdict_class")\n    if False:'),

    ("a record with no absorption_status stops being faulted",
     "this is the whole of ABSORB-01. With the check gone the field is advisory, "
     "and an advisory field on a schema nobody re-reads is the condition that "
     "produced 0 of 41 in the first place",
     '    status = rec.get("absorption_status")\n    if not status:',
     '    status = rec.get("absorption_status")\n    if False:'),

    ("the status vocabulary stops being closed",
     "any string becomes a legal status, so the enum degrades into the free text "
     "it was added to replace and groups nothing",
     'elif status not in ABSORPTION_STATUSES:',
     'elif False:'),

    ("a status may claim a decision without naming it",
     "absorption_status 'absorbed' with an empty `absorbed` field is the free-text "
     "defect wearing an enum: it groups perfectly and carries no information about "
     "what was actually taken or where it landed",
     'elif status in ABSORPTION_NEEDS_DETAIL and not str(rec.get("absorbed", "")).strip():',
     'elif False:'),
]
