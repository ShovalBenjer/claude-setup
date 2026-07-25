"""Mutations for tools/bus/bus.py.

Two of these SURVIVED the first run of this harness on 2026-07-25, and both were
real defects in bus.py's tests rather than in the harness:

  - "prev is no longer written" survived because the deletion-detection case
    planted its fixture with the test's OWN writer, which computed prev itself, so
    the test passed with cmd_send's prev removed entirely. A test that plants its
    fixture with its own writer has stopped testing the product.
  - "canonical stops omitting absent keys" survived because every case within one
    run writes and reads with the same canonical(), so a change to its SHAPE stays
    self-consistent while silently invalidating every row already on disk. A wire
    format needs a fixed external oracle, which is now a pinned golden vector.

Each entry is a plausible regression, not a syntax error: the shape of the edit
someone would actually make while refactoring.
"""

TARGET = "tools/bus/bus.py"
ARGV = ["selftest"]

MUTATIONS = [
    ("row_altered always says clean",
     "the read path stops marking tampered rows",
     'return "hash" in rec and row_hash(rec) != rec["hash"]',
     'return False'),

    ("row_altered fires on every row",
     "the mark appears on clean rows, so it carries no information",
     'return "hash" in rec and row_hash(rec) != rec["hash"]',
     'return True'),

    ("inbox drops the ALTERED banner",
     "verify still detects the edit but the reader is never told",
     'if row_altered(r):\n            print("  !! ALTERED',
     'if False:\n            print("  !! ALTERED'),

    ("log drops the ALTERED mark",
     "one of the two read surfaces silently loses the mark",
     'mark = " !! ALTERED" if row_altered(r) else ""',
     'mark = ""'),

    ("cursor goes back to a positional offset",
     "the defect that lost an unread message after a merge dropped a line",
     'cursor_path(lane).write_text(row_id(rows[-1]) if rows else "", encoding="utf-8")',
     'cursor_path(lane).write_text(str(len(rows)), encoding="utf-8")'),

    ("unread skips instead of replaying on a miss",
     "a cursor naming a vanished row silently loses everything after it",
     '        if row_id(rows[i]) == cur:\n            return rows[i + 1:]\n    return list(rows)',
     '        if row_id(rows[i]) == cur:\n            return rows[i + 1:]\n    return []'),

    ("legacy positional cursor no longer honoured",
     "a lane mid-flight replays its entire history on upgrade",
     '    if cur.isdigit():                       # legacy positional cursor, honoured once\n        return rows[int(cur):]',
     '    if False:\n        return rows[int(cur):]'),

    ("cmd_send stops recording origin_lane",
     "--from-lane can declare any sender with nothing recording the truth",
     '"origin_lane": lane_for(os.getcwd()),',
     ''),

    ("inbox hides the declared/derived mismatch",
     "the field is recorded and nobody ever sees it",
     'claim = f" [declared; sender cwd was lane {origin}]"',
     'claim = ""'),

    ("prev is no longer written",
     "rows commit to themselves but not to each other, so deletion is invisible",
     '"prev": row_id(rows[-1]) if rows else "",\n    }\n    rec["hash"] = row_hash(rec)',
     '"prev": "",\n    }\n    rec["hash"] = row_hash(rec)'),

    ("verify exits 0 on a break",
     "a check that finds defects and exits 0 reports rather than enforces",
     '        print("      " + why)\n    return 1',
     '        print("      " + why)\n    return 0'),

    ("--strict stops failing unchained rows",
     "the opt-in strict mode is a no-op",
     '        if unchained and a.strict:',
     '        if unchained and False:'),

    ("canonical stops omitting absent keys",
     "adding a CHAIN_FIELD silently rehashes every older row",
     'payload = {k: rec[k] for k in CHAIN_FIELDS if k in rec}',
     'payload = {k: rec.get(k, "") for k in CHAIN_FIELDS}'),

    ("canonical stops sorting keys",
     "a row hashes differently depending on how it was serialized",
     'return json.dumps(payload, sort_keys=True, separators=(",", ":"),',
     'return json.dumps(payload, sort_keys=False, separators=(",", ":"),'),

    ("canonical includes the hash field",
     "a value committing to itself, so no row can ever verify",
     'CHAIN_FIELDS = ("id", "ts", "from_lane", "origin_lane", "from_session", "to",\n                "kind", "subject", "body", "refs", "prev")',
     'CHAIN_FIELDS = ("id", "ts", "from_lane", "origin_lane", "from_session", "to",\n                "kind", "subject", "body", "refs", "prev", "hash")'),

    ("row_id recomputes instead of returning the stored hash",
     "a tampered row loses its address, so every lane replays consumed traffic",
     'return rec.get("hash") or row_hash(rec)',
     'return row_hash(rec)'),

    ("row_hash truncates to 8 hex instead of 16",
     "the digest width changes, so every row already on disk stops verifying",
     'return hashlib.sha256(canonical(rec)).hexdigest()[:16]',
     'return hashlib.sha256(canonical(rec)).hexdigest()[:8]'),

    ("verify stops checking prev at all",
     "content is checked but deletion and reordering become invisible",
     'elif prev_id is not None and r.get("prev", "") != prev_id:',
     'elif False:'),
]
