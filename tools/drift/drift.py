#!/usr/bin/env python
"""Session drift sentinel: measure lane drift from the transcript, notify only.

Purpose. A session claims a lane (charter) and then edits files. When the edits
land outside the lane's owned tree, the session is drifting, and the operator
finds out only after the work is misfiled. This measures that signal per session
and keeps a strike ledger so an escalation policy (notify first, close second)
can be armed later ON DATA rather than on hope: the follow-through hook cost a
measured 66 operator turns before its threshold was softened, so v1 records and
notifies but never blocks.

Contracts. Strikes live in state/drift/<session_id>.json, one file per session,
rewritten whole (small, single writer: the Stop hook of that session). The lane
map is parsed from docs/charters.md `Owns:` lines; a lane whose owned paths
cannot be parsed yields NO drift verdicts, loudly, because a guard that cannot
run must announce it (ship_gate_stop.py's rule). Edit/Write paths are read from
the session transcript JSONL, the same source ship_gate_stop.py reads.

Prior art, in-repo: ship_gate_stop.py (blocking stop hook), completion_gate.py
(nudge), watchdog skill. This adds only the lane-vs-paths measurement.

Typical usage:
  python tools/drift/drift.py check --transcript T.jsonl --lane A --session s1
  python tools/drift/drift.py status
  python tools/drift/drift.py selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STRIKE_DIR = REPO / "state" / "drift"
CHARTERS = REPO / "docs" / "charters.md"

LANE_HEAD = re.compile(r"^#+\s*Lane\s+([A-Z])\b", re.I)
OWNS = re.compile(r"^-\s*Owns:\s*(.+)$")
# Only ~-anchored or absolute paths: bare prose like "writing/case-study" in a
# charter sentence must not resolve against whatever cwd the hook runs from.
PATHISH = re.compile(r"(?<![\w.-])[`]?((?:~|/)[\w./-]+)[`]?")


def lane_roots(charters_text: str) -> dict[str, list[Path]]:
    """Map lane letter to the owned root paths named on its Owns: line."""
    lanes: dict[str, list[Path]] = {}
    current = None
    for line in charters_text.splitlines():
        head = LANE_HEAD.match(line.strip())
        if head:
            current = head.group(1).upper()
            continue
        owns = OWNS.match(line.strip())
        if owns and current:
            roots = []
            for tok in owns.group(1).split("."):
                for m in PATHISH.finditer(tok):
                    p = m.group(1).strip("`")
                    if "/" in p:
                        roots.append(Path(p.replace("~", str(Path.home()))).resolve())
                break  # paths live in the first sentence; the rest is prose
            lanes[current] = roots
    return lanes


def edited_paths(transcript: Path, tail: int = 2000) -> list[Path]:
    """Edit/Write/NotebookEdit file_path targets from the transcript tail."""
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-tail:]:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if (isinstance(block, dict) and block.get("type") == "tool_use"
                    and block.get("name") in ("Edit", "Write", "NotebookEdit")):
                fp = (block.get("input") or {}).get("file_path")
                if fp:
                    out.append(Path(fp))
    return out


def offending(paths: list[Path], roots: list[Path]) -> list[Path]:
    """Edited paths that sit under no owned root."""
    bad = []
    for p in paths:
        rp = p.resolve()
        if not any(rp.is_relative_to(r) for r in roots):
            bad.append(p)
    return bad


def strike(session: str, evidence: list[str], strike_dir: Path) -> int:
    """Record one strike for this session and return the new count."""
    strike_dir.mkdir(parents=True, exist_ok=True)
    f = strike_dir / (session + ".json")
    rec = {"session": session, "strikes": []}
    if f.exists():
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            pass  # a torn write loses old strikes, never the ability to record
    rec["strikes"].append({"evidence": evidence})
    f.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return len(rec["strikes"])


def check(transcript: Path, lane: str, session: str,
          charters: Path = CHARTERS, strike_dir: Path = STRIKE_DIR) -> dict:
    """Measure drift; on drift, record a strike. Returns the verdict dict."""
    try:
        lanes = lane_roots(charters.read_text(encoding="utf-8"))
    except OSError:
        return {"verdict": "OFF", "why": "charters unreadable at {}".format(charters)}
    roots = lanes.get(lane.upper())
    if not roots:
        return {"verdict": "OFF",
                "why": "no owned paths parsed for lane {}".format(lane)}
    if not transcript.is_file():
        return {"verdict": "OFF",
                "why": "no transcript at {}".format(transcript)}
    bad = offending(edited_paths(transcript), roots)
    if not bad:
        return {"verdict": "CLEAN", "lane": lane, "roots": [str(r) for r in roots]}
    count = strike(session, [str(p) for p in bad], strike_dir)
    return {"verdict": "DRIFT", "lane": lane, "strike": count,
            "offending": sorted({str(p) for p in bad}),
            "action": "notify+reground" if count < 2 else
                      "close (NOT ARMED: v1 is notify-only until a week of "
                      "ledger shows the false-positive rate)"}


def cmd_check(args) -> int:
    verdict = check(Path(args.transcript), args.lane, args.session)
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["verdict"] in ("CLEAN", "OFF") else 1


def cmd_status(_args) -> int:
    files = sorted(STRIKE_DIR.glob("*.json")) if STRIKE_DIR.is_dir() else []
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            print("{:2d} strike(s)  {}".format(len(rec.get("strikes", [])),
                                               rec.get("session", f.stem)))
        except ValueError:
            print(" ?  unreadable  {}".format(f.name))
    if not files:
        print("no strikes recorded")
    return 0


def selftest_checks(tmp: Path) -> list[tuple[str, bool]]:
    charters = ("## Lane A: harness\n- Owns: {0}/repo-a. Rules and hooks.\n"
                "## Lane B: resume\n- Owns: `{0}/repo-b`. Hiring machine.\n"
                "## Lane C: learning\n- Owns: the study loops, no path here.\n"
                ).format(tmp)
    cf = tmp / "charters.md"
    cf.write_text(charters, encoding="utf-8")
    lanes = lane_roots(charters)

    def tool_use(path):
        return {"message": {"content": [{"type": "tool_use", "name": "Edit",
                                         "input": {"file_path": path}}]}}
    t = tmp / "t.jsonl"
    t.write_text("\n".join([
        json.dumps(tool_use(str(tmp / "repo-a" / "x.py"))),
        json.dumps(tool_use(str(tmp / "repo-b" / "y.py"))),
        json.dumps({"message": {"content": "prose only"}}),
        "{ torn",
    ]) + "\n", encoding="utf-8")
    sd = tmp / "strikes"
    clean = check(t, "B", "s-clean", charters=cf, strike_dir=sd)  # b owns repo-b
    first = check(t, "A", "s1", charters=cf, strike_dir=sd)
    second = check(t, "A", "s1", charters=cf, strike_dir=sd)
    off = check(t, "C", "s2", charters=cf, strike_dir=sd)
    missing = check(tmp / "absent.jsonl", "A", "s3", charters=cf, strike_dir=sd)
    return [
        ("both pathed lanes parsed", set(lanes) >= {"A", "B"}),
        ("backtick path parsed", lanes["B"] == [ (tmp / "repo-b").resolve() ]),
        ("only the cross-lane path offends for lane B",
         clean["verdict"] == "DRIFT" and clean["offending"] == [str(tmp / "repo-a" / "x.py")]),
        ("cross-lane edit flagged with the offending path",
         first["verdict"] == "DRIFT" and str(tmp / "repo-b" / "y.py") in first["offending"]),
        ("first strike says notify", first["action"].startswith("notify")),
        ("second strike escalates but names itself unarmed",
         second["strike"] == 2 and "NOT ARMED" in second["action"]),
        ("pathless lane reports OFF, not clean", off["verdict"] == "OFF"),
        ("missing transcript reports OFF, not clean", missing["verdict"] == "OFF"),
        ("torn line and prose turns ignored", True),
        ("mid-word slash prose parses no path",
         lane_roots("## Lane D: x\n- Owns: the writing/case-study artifacts.\n")["D"] == []),
    ]


def cmd_selftest(_args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        checks = selftest_checks(Path(tmp))
    failed = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print("{:8s} {}".format("ok" if ok else "FAIL", n))
    print("selftest: {} checks, {} failed".format(len(checks), len(failed)))
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--transcript", required=True)
    c.add_argument("--lane", required=True)
    c.add_argument("--session", required=True)
    c.set_defaults(fn=cmd_check)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
