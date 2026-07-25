#!/usr/bin/env python3
"""The hiring ledger holds real rows, and the funnel has actually moved.

Replaces an inline PowerShell one-liner whose SQL used chr() (SQLite has char(),
not chr()), so the check crashed and the claim came back REFUTED when the ledger
was in fact fine. A verifier bug and a real defect look identical from the
outside, which is why verifiers live in files with tests-of-their-own rather than
in quoted strings inside a JSONL field.

"Tables exist" is too weak a bar: an empty schema passes it. This asserts rows in
the tables that represent the funnel actually moving, and prints the numbers so a
human reads the funnel instead of a boolean.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

DB = (Path(os.path.expanduser("~")) / "Downloads" / "new-recruit"
      / "hiring_engine" / "ledger.sqlite")

# table -> minimum rows for the claim "the funnel is real and has moved"
REQUIRED = {"jobs": 1, "applications": 1, "outcomes": 1, "runs": 1}


def main() -> int:
    if not DB.exists():
        print(f"ledger.sqlite missing at {DB}")
        return 1

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    have = {r[0] for r in con.execute(
        "select name from sqlite_master where type='table'")}

    missing = [t for t in REQUIRED if t not in have]
    if missing:
        print(f"ledger is missing funnel tables: {missing} (has {sorted(have)})")
        return 1

    counts = {}
    for t in sorted(have):
        counts[t] = con.execute(f'select count(*) from "{t}"').fetchone()[0]

    print("ledger row counts: " + ", ".join(f"{t}={n}" for t, n in counts.items()))

    empty = [t for t, n in REQUIRED.items() if counts[t] < n]
    if empty:
        print(f"funnel tables present but empty: {empty} "
              f"(schema without rows is not a funnel)")
        return 1

    # The headline numbers, so the check reports the funnel rather than a boolean.
    try:
        by_status = con.execute(
            "select status, count(*) from applications group by status "
            "order by count(*) desc").fetchall()
        print("applications by status: "
              + ", ".join(f"{s or 'null'}={n}" for s, n in by_status))
    except sqlite3.OperationalError:
        pass  # schema drift on the status column is not what this claim asserts

    return 0


if __name__ == "__main__":
    sys.exit(main())
