# -*- coding: utf-8 -*-
"""Plan-divergence ledger: what a plan promised vs what execution did.

Stdlib only. Append-only JSONL at state/plan_divergence.jsonl.

Design note on the one thing this file refuses to do: it never decides the
category. Whether a failure was a code bug or an unfeasible plan is a judgement,
and a script that guessed it would launder a guess into a record. It measures the
part that IS measurable (which files the work touched against which files it
promised to touch) and makes the human state the rest, with evidence, or refuses
to close the row.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STATE = os.path.join(REPO, "state")
LOG = os.path.join(STATE, "plan_divergence.jsonl")

CATEGORIES = ("codebug", "plan-unfeasible", "contract-violation")
OUTCOMES = ("held", "diverged")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _read():
    if not os.path.exists(LOG):
        return []
    rows = []
    with open(LOG, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _append(row):
    os.makedirs(STATE, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _open_contract(rows, cid):
    """Latest lock for cid with no later close. None if absent or already closed."""
    state = None
    for r in rows:
        if r.get("id") != cid:
            continue
        if r.get("event") == "lock":
            state = r
        elif r.get("event") == "close":
            state = None
    return state


def _changed_files():
    """Files changed in the working tree. Empty list if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return None
        return sorted(f for f in out.stdout.splitlines() if f.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def _drift(promised, touched):
    """Files touched that no promise covers. Prefix match, so a promised
    directory covers its contents."""
    if touched is None:
        return None
    out = []
    for f in touched:
        if not any(f == p or f.startswith(p.rstrip("/") + "/") for p in promised):
            out.append(f)
    return out


def cmd_lock(a):
    rows = _read()
    if _open_contract(rows, a.id):
        print(f"refused: contract '{a.id}' is already open. close it first.", file=sys.stderr)
        return 2
    _append({
        "event": "lock", "id": a.id, "at": _now(), "goal": a.goal,
        "promises": sorted(set(a.promises)), "falsifier": a.falsifier,
    })
    print(f"locked {a.id}: {len(set(a.promises))} promised path(s)")
    return 0


def cmd_status(a):
    rows = _read()
    c = _open_contract(rows, a.id)
    if not c:
        print(f"no open contract for '{a.id}'")
        return 1
    touched = _changed_files()
    drift = _drift(c["promises"], touched)
    print(f"id        {c['id']}\nlocked    {c['at']}\ngoal      {c['goal']}")
    print(f"promises  {', '.join(c['promises'])}")
    print(f"falsifier {c['falsifier']}")
    if touched is None:
        print("touched   UNKNOWN (git unavailable)")
    else:
        print(f"touched   {len(touched)} file(s)")
        print(f"drift     {len(drift)} outside promises" + (": " + ", ".join(drift[:8]) if drift else ""))
    return 0


def cmd_close(a):
    rows = _read()
    c = _open_contract(rows, a.id)
    if not c:
        print(f"refused: no open contract for '{a.id}'.", file=sys.stderr)
        return 2
    if a.outcome == "diverged" and not a.category:
        print("refused: --outcome diverged requires --category.", file=sys.stderr)
        return 2
    if not a.evidence:
        print("refused: --evidence is required. An outcome without evidence is a diary entry.",
              file=sys.stderr)
        return 2
    touched = _changed_files()
    drift = _drift(c["promises"], touched)
    _append({
        "event": "close", "id": a.id, "at": _now(), "outcome": a.outcome,
        "category": a.category, "evidence": a.evidence, "note": a.note or "",
        "promises": c["promises"], "falsifier": c["falsifier"],
        "touched_count": None if touched is None else len(touched),
        "drift_files": drift, "opened_at": c["at"],
    })
    d = "unknown" if drift is None else str(len(drift))
    print(f"closed {a.id}: {a.outcome}" + (f" / {a.category}" if a.category else "") + f", drift={d}")
    return 0


def build_report():
    rows = _read()
    closed = [r for r in rows if r.get("event") == "close"]
    open_ids = sorted({r["id"] for r in rows if r.get("event") == "lock"}
                      - {r["id"] for r in rows if r.get("event") == "close"})
    by_cat = {}
    for r in closed:
        key = r.get("category") or ("held" if r.get("outcome") == "held" else "uncategorised")
        by_cat[key] = by_cat.get(key, 0) + 1
    return {
        "generated_at": _now(),
        "locked_total": sum(1 for r in rows if r.get("event") == "lock"),
        "closed_total": len(closed),
        "open_ids": open_ids,
        "by_category": by_cat,
        "closed": closed,
    }


def cmd_report(a):
    rep = build_report()
    if a.json:
        print(json.dumps(rep, indent=1, ensure_ascii=False))
        return 0
    print(f"locked {rep['locked_total']}  closed {rep['closed_total']}  open {len(rep['open_ids'])}")
    for k, v in sorted(rep["by_category"].items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k}")
    if rep["open_ids"]:
        print("open: " + ", ".join(rep["open_ids"]))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="divergence")
    sub = p.add_subparsers(dest="cmd", required=True)

    lk = sub.add_parser("lock")
    lk.add_argument("--id", required=True)
    lk.add_argument("--goal", required=True)
    lk.add_argument("--promises", action="append", required=True)
    lk.add_argument("--falsifier", required=True)
    lk.set_defaults(fn=cmd_lock)

    st = sub.add_parser("status")
    st.add_argument("--id", required=True)
    st.set_defaults(fn=cmd_status)

    cl = sub.add_parser("close")
    cl.add_argument("--id", required=True)
    cl.add_argument("--outcome", required=True, choices=OUTCOMES)
    cl.add_argument("--category", choices=CATEGORIES)
    cl.add_argument("--evidence")
    cl.add_argument("--note")
    cl.set_defaults(fn=cmd_close)

    rp = sub.add_parser("report")
    rp.add_argument("--json", action="store_true")
    rp.set_defaults(fn=cmd_report)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
