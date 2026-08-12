#!/usr/bin/env python3
"""One event stream out of every agent ledger, across every repo.

THE PROBLEM THIS ADDRESSES, measured 2026-08-04 rather than assumed.

Telemetry already exists and is already automatic. Ten append-only ledgers under
`state/` are written by hooks and oracles with no operator step: gate-runs 7029
rows, handback-log 597, prompt-tickets 334, skill-use 52, claims 19, lessons 42,
plus refutations, plan-deviations, prose-scores and the bus. **None of it leaves
the machine and none of it is joined across repos.** Three repos are in play
(claude-setup, new-recruit, daily-deep-learning) and each keeps its own state/
directory that no other repo can see.

The messaging half is the mirror image and it is more interesting. `tools/bus/bus.py`
is a real hash-chained A2A bus, and it IS wired: `bus.py inbox` runs from BOTH
SessionStart and UserPromptSubmit in the live `~/.claude/settings.json`. So reading
is automatic and always has been. It still holds 25 messages, the last written
2026-07-30. **Reading was never the problem. Sending is voluntary, and this
repository's own lesson ledger says every voluntary step eventually stops
happening** (23 hook entries unwired, dispatch never run, the external review
backend never once requested across 11 review artifacts).

So this file does not add an eleventh ledger and does not ask an agent to report
anything. It DERIVES the report from what the agent already wrote. A gate FAIL, a
refuted claim, a lesson, a plan deviation, a handback: those rows exist because a
hook wrote them, they are exactly what another lane needs to know, and nobody has
to remember to send them.

PRIOR ART, named rather than skipped. This is not a new idea in either half.
Agent-observability products (Langfuse, LangSmith, W&B Weave) and the OpenTelemetry
GenAI semantic conventions all normalise heterogeneous agent events into one
stream; using GitHub Issues as a message bus between automated actors is an
established pattern with many implementations. What is specific here is the
constraint set, not the concept: stdlib only, no daemon, no service to keep
running, offline-first, append-only ledgers that already exist, and a hash-chained
source of truth that must not be rewritten.

SCHEMAS ARE READ, NOT GUESSED. Every extractor below was written against a real
last-row sample from the live file. The ledgers disagree about nearly everything:
`bus.jsonl` timestamps as `ts` and identifies as `from_lane`, `claims.jsonl` uses
`claimed_at` and `lane`, `handback-log.jsonl` has only action/reason/session/ts and
no lane at all. An extractor that assumed one shape would silently emit zero rows
for the others, and zero rows from a collector looks exactly like a quiet period.
That is why `--audit` exists and why the selftest asserts a nonzero yield per
source rather than a nonzero total.

    python tools/telemetry/collect.py --since 24h
    python tools/telemetry/collect.py --audit          # per-source yield, find the silent ones
    python tools/telemetry/collect.py --notable        # only what another agent needs
    python tools/telemetry/collect.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1

# Repos to sweep. Discovered rather than hardcoded where possible, because a repo
# added next month should appear without editing this file.
REPO_ROOTS = [Path.home() / "work/repos"]

# Severity is the collector's own judgement and is deliberately coarse. Three
# levels, because a scale nobody can apply consistently is a scale that gets
# ignored: `alert` means another agent should act, `note` means it should know,
# `trace` means it is volume.
ALERT, NOTE, TRACE = "alert", "note", "trace"


def _iso(value) -> str:
    """Best-effort ISO timestamp. Returns '' rather than raising or inventing one."""
    if not value:
        return ""
    s = str(value)
    # Ledgers carry both offset-aware ("+03:00") and naive stamps. Neither is
    # normalised to UTC here: rewriting a recorded timestamp to a different zone
    # makes a row disagree with the file it came from, and the file is the truth.
    return s if re.match(r"^\d{4}-\d{2}-\d{2}", s) else ""



def row_repo(r: dict, fallback: str) -> str:
    """The repo a row is ABOUT, which is usually not the repo the file sits in.

    Corrected 2026-08-04 by the --audit output. Every hook writes to a fixed path:
    `session-recall.sh` and `capture_turn.py` both resolve
    `CLAUDE_OS_DIR` with a default of `~/claude-setup`. So a session working in
    new-recruit still lands its telemetry in claude-setup's ledgers, and attributing
    a row to the directory holding the file labels every one of them "claude-setup".
    That is not aggregation, it is a collapse, and the cross-repo view it produces
    would be uniformly wrong while looking complete.

    Several ledgers do carry the real origin (`repo`, `project`, `project_path`,
    `cwd`); those are preferred. Rows that carry none keep the fallback, and the
    difference is visible because `origin` records which of the two was used.
    """
    for field in ("repo", "project", "project_path", "cwd"):
        val = r.get(field)
        if val:
            name = str(val).rstrip("/").split("/")[-1].split("\\")[-1]
            if name and name not in {".", ""}:
                return name
    return fallback


def event(**kw) -> dict:
    base = {"schema": SCHEMA_VERSION, "ts": "", "repo": "", "lane": "", "source": "",
            "kind": "", "severity": TRACE, "subject": "", "ref": "", "origin": "row"}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# One extractor per ledger. Each takes a parsed row and returns an event or None.
# Returning None is a real answer: not every row is worth carrying.
# ---------------------------------------------------------------------------


# Temp roots on both hosts this repo runs on. `gate.py selftest` builds throwaway
# projects with tempfile and gates them on purpose, several of which MUST report
# FAIL for the oracle to be proving anything.
_TEMP_MARKERS = ("/tmp/", "\\temp\\", "\\appdata\\local", "/var/folders/")


def is_fixture(r: dict) -> bool:
    """True for a gate row produced by the gate's own selftest.

    Found by running publish.py --dry-run for the first time: the feed came back
    almost entirely `gate FAIL on tmpd1fy6797`, and the one row that mattered, a
    real FAIL in new-recruit, was buried among them. 6613 of 7029 gate rows are
    fixtures. Publishing them would have made the surface useless on day one,
    which is the exact death the volume cap was supposed to prevent.

    Keyed on project_path rather than on a `tmp` name prefix, because a real
    project may legitimately be named with that prefix and a path into a temp root
    cannot be a tracked repository. Fixtures are DOWNGRADED to trace, never
    dropped: the count stays visible in --audit, so the ratio of fixture to real
    remains measurable rather than being quietly erased.
    """
    path = str(r.get("project_path", "")).lower().replace("\\", "\\")
    return any(m in path for m in _TEMP_MARKERS) or path.startswith("/tmp")


def _from_gate_runs(r: dict) -> dict | None:
    verdict = r.get("verdict", "")
    # PASS rows are 7000 of the 7029 and carry no information for another agent.
    # They are still emitted at TRACE so a rate can be computed; --notable drops them.
    sev = ALERT if (verdict == "FAIL" and not is_fixture(r)) else TRACE
    blocking = r.get("blocking") or []
    subject = "gate {} on {}".format(verdict or "?", r.get("project", "?"))
    if blocking:
        subject += ": " + ", ".join(str(b) for b in blocking)[:120]
    return event(ts=_iso(r.get("ts")), source="gate-runs", kind="gate", severity=sev,
                 subject=subject, ref=str(r.get("commit", ""))[:12])


def _from_lessons(r: dict) -> dict | None:
    if str(r.get("status", "")).lower() in {"closed", "resolved"}:
        return None
    return event(ts=_iso(r.get("ts")), lane=r.get("lane", ""), source="lessons",
                 kind="lesson", severity=ALERT,
                 subject="{}: {}".format(r.get("id", "?"), str(r.get("class", ""))[:160]),
                 ref=str(r.get("id", "")))


def _from_refutations(r: dict) -> dict | None:
    # A refuted claim is the single highest-value cross-agent signal in this repo:
    # it means something another session believed is now known false.
    refuted = str(r.get("verdict", "")).lower() in {"refuted", "fail", "false"}
    return event(ts=_iso(r.get("ts")), lane=r.get("lane", ""), source="refutations",
                 kind="refutation", severity=ALERT if refuted else NOTE,
                 subject="{} -> {}".format(str(r.get("claim", ""))[:120], r.get("verdict", "?")),
                 ref=str(r.get("id", "")))


def _from_plan_deviations(r: dict) -> dict | None:
    return event(ts=_iso(r.get("ts")), lane=r.get("lane", ""), source="plan-deviations",
                 kind="deviation", severity=ALERT,
                 subject="plan refuted by {}: {}".format(
                     str(r.get("refuted_by", "?"))[:60], str(r.get("plan", ""))[:100]),
                 ref=str(r.get("session", ""))[:12])


def _from_claims(r: dict) -> dict | None:
    return event(ts=_iso(r.get("claimed_at")), lane=r.get("lane", ""), source="claims",
                 kind="claim", severity=NOTE,
                 subject="lane {} claimed: {}".format(r.get("lane", "?"), str(r.get("scope", ""))[:140]),
                 ref=str(r.get("id", "")))


def _from_handback(r: dict) -> dict | None:
    # 597 rows and no lane field at all. Emitting lane="" is correct and honest;
    # inventing one from cwd would be a guess dressed as data.
    action = str(r.get("action", ""))
    sev = ALERT if action in {"blocked", "stuck", "handback"} else TRACE
    return event(ts=_iso(r.get("ts")), source="handback-log", kind="handback", severity=sev,
                 subject="{}: {}".format(action or "?", str(r.get("reason", ""))[:140]),
                 ref=str(r.get("session", ""))[:12])


def _from_bus(r: dict) -> dict | None:
    return event(ts=_iso(r.get("ts")), lane=r.get("from_lane", ""), source="bus",
                 kind="message", severity=ALERT if r.get("kind") in {"ask", "warn"} else NOTE,
                 subject="to {} [{}] {}".format(r.get("to", "?"), r.get("kind", "?"),
                                               str(r.get("subject", ""))[:120]),
                 ref=str(r.get("id", "")))


def _from_skill_use(r: dict) -> dict | None:
    return event(ts=_iso(r.get("ts")), source="skill-use", kind="skill", severity=TRACE,
                 subject="{} -> {}".format(r.get("skill", "?"), r.get("outcome", "?")),
                 ref=str(r.get("project", ""))[:40])


def _from_prompt_tickets(r: dict) -> dict | None:
    return event(ts=_iso(r.get("ts")), source="prompt-tickets", kind="turn", severity=TRACE,
                 subject="state {} on {}".format(r.get("state", "?"), r.get("branch", "?")),
                 ref=str(r.get("id", ""))[:12])


EXTRACTORS = {
    "gate-runs.jsonl": _from_gate_runs,
    "lessons.jsonl": _from_lessons,
    "refutations.jsonl": _from_refutations,
    "plan-deviations.jsonl": _from_plan_deviations,
    "claims.jsonl": _from_claims,
    "handback-log.jsonl": _from_handback,
    "bus.jsonl": _from_bus,
    "skill-use.jsonl": _from_skill_use,
    "prompt-tickets.jsonl": _from_prompt_tickets,
}


def discover_repos() -> list[Path]:
    """Every git repo with a state/ directory, under the configured roots."""
    out = []
    for root in REPO_ROOTS:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if (child / ".git").exists() and (child / "state").is_dir():
                out.append(child)
    return out


def read_ledger(path: Path) -> list[dict]:
    """Parse a JSONL ledger, skipping unparseable lines rather than aborting.

    Torn lines are a documented reality on these files (bus.py's own docstring
    records six rows destroyed by concurrent appends on Windows), so a collector
    that raises on the first bad line would report nothing at all for a ledger
    that is 99% readable. The count of skipped lines is surfaced by --audit so the
    tolerance never becomes silent.
    """
    rows, bad = [], 0
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:  # noqa: BLE001
                    bad += 1
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        return []
    if bad:
        rows.append({"__collector_skipped__": bad})
    return rows


def collect(since: dt.datetime | None = None) -> tuple[list[dict], dict]:
    """Return (events, per-source audit)."""
    events: list[dict] = []
    audit: dict[str, dict] = {}
    for repo in discover_repos():
        for name, extract in EXTRACTORS.items():
            path = repo / "state" / name
            key = "{}/{}".format(repo.name, name)
            if not path.exists():
                audit[key] = {"rows": 0, "events": 0, "skipped": 0, "present": False}
                continue
            rows = read_ledger(path)
            skipped = sum(r.get("__collector_skipped__", 0) for r in rows)
            rows = [r for r in rows if "__collector_skipped__" not in r]
            got = 0
            for r in rows:
                try:
                    ev = extract(r)
                except Exception:  # noqa: BLE001
                    continue
                if not ev:
                    continue
                attributed = row_repo(r, repo.name)
                ev["repo"] = attributed
                ev["origin"] = "row" if attributed != repo.name else "file-location"
                if since and ev["ts"]:
                    try:
                        stamp = dt.datetime.fromisoformat(ev["ts"])
                        if stamp.tzinfo:
                            stamp = stamp.replace(tzinfo=None)
                        if stamp < since:
                            continue
                    except ValueError:
                        pass
                events.append(ev)
                got += 1
            audit[key] = {"rows": len(rows), "events": got, "skipped": skipped, "present": True}
    events.sort(key=lambda e: (e["ts"] or "", e["source"]))
    return events, audit


def parse_since(spec: str | None) -> dt.datetime | None:
    if not spec:
        return None
    m = re.fullmatch(r"(\d+)([hdw])", spec.strip().lower())
    if not m:
        raise SystemExit("--since takes forms like 24h, 7d, 2w")
    n, unit = int(m.group(1)), m.group(2)
    delta = {"h": dt.timedelta(hours=n), "d": dt.timedelta(days=n), "w": dt.timedelta(weeks=n)}[unit]
    return dt.datetime.now() - delta


def selftest() -> int:
    failures = []

    ev = _from_gate_runs({"ts": "2026-08-04T18:37:00", "verdict": "FAIL",
                          "project": "claude-setup", "blocking": ["unit"], "commit": "abc123def456"})
    if ev["severity"] != ALERT:
        failures.append("a gate FAIL is not an alert")
    if "unit" not in ev["subject"]:
        failures.append("a gate FAIL drops the blocking domain from its subject")
    if _from_gate_runs({"ts": "x", "verdict": "PASS"})["severity"] != TRACE:
        failures.append("a gate PASS is not trace-level, so alerts will be drowned")
    fixture = {"ts": "x", "verdict": "FAIL", "project": "tmpabc",
               "project_path": "C:\\Users\\shova\\AppData\\Local\\tmpabc"}
    if _from_gate_runs(fixture)["severity"] == ALERT:
        failures.append("a selftest fixture FAIL alerts, which floods the feed")
    real = {"ts": "x", "verdict": "FAIL", "project": "new-recruit",
            "project_path": "/home/shov/work/repos/new-recruit"}
    if _from_gate_runs(real)["severity"] != ALERT:
        failures.append("a real repo FAIL was downgraded along with the fixtures")

    if _from_lessons({"status": "closed", "id": "L-1"}) is not None:
        failures.append("a closed lesson is still emitted")
    if _from_lessons({"status": "open", "id": "L-2", "class": "x"}) is None:
        failures.append("an open lesson is dropped")

    # Every extractor must survive a row it has never seen. A collector that
    # raises on one malformed ledger stops carrying the other nine.
    for name, fn in EXTRACTORS.items():
        try:
            fn({})
        except Exception as exc:  # noqa: BLE001
            failures.append("{} raised on an empty row: {}".format(name, type(exc).__name__))

    if row_repo({"project": "/home/shov/work/repos/new-recruit"}, "claude-setup") != "new-recruit":
        failures.append("row_repo ignored the row's own project path")
    if row_repo({}, "claude-setup") != "claude-setup":
        failures.append("row_repo did not fall back to the file location")
    if row_repo({"repo": ""}, "claude-setup") != "claude-setup":
        failures.append("row_repo took an empty field as an attribution")

    if _iso(None) or _iso("not-a-date"):
        failures.append("_iso invented a timestamp for a row that had none")
    if _iso("2026-08-04T12:00:00+03:00") != "2026-08-04T12:00:00+03:00":
        failures.append("_iso rewrote an offset-aware stamp")

    # The load-bearing check: yield is asserted PER SOURCE, not in total. A total
    # stays healthy while one ledger silently contributes nothing, which is the
    # exact failure this file's docstring is about.
    events, audit = collect()
    present = {k: v for k, v in audit.items() if v["present"] and v["rows"] > 0}
    silent = [k for k, v in present.items() if v["events"] == 0]
    if not present:
        failures.append("no ledger was found at all, so this proves nothing")
    if silent:
        failures.append("ledger(s) with rows produced zero events: " + ", ".join(sorted(silent)))
    if events and not any(e["severity"] == ALERT for e in events):
        failures.append("not one alert across the whole corpus, which is implausible")

    for line in failures:
        print("  FAIL  " + line)
    if failures:
        print("VERDICT: {} check(s) failed".format(len(failures)))
        return 1
    print("  ok    a gate FAIL alerts and names its blocking domain")
    print("  ok    a gate PASS stays at trace so it cannot drown the alerts")
    print("  ok    a selftest fixture FAIL is trace, a real repo FAIL is still an alert")
    print("  ok    a closed lesson is dropped, an open one is carried")
    print("  ok    every extractor survives a row shaped like nothing")
    print("  ok    a row is attributed to the repo it is about, not the file it sits in")
    print("  ok    no timestamp is invented and none is rewritten")
    print("  ok    every ledger that has rows yields events ({} sources, {} events)".format(
        len(present), len(events)))
    print("VERDICT: the collector reads every live ledger and no source is silently empty")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="collect.py", description=__doc__.splitlines()[0])
    ap.add_argument("--since", help="24h, 7d, 2w")
    ap.add_argument("--notable", action="store_true", help="alerts and notes only, drop trace")
    ap.add_argument("--audit", action="store_true", help="per-source yield instead of events")
    ap.add_argument("--json", action="store_true", help="JSONL out")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    events, audit = collect(parse_since(args.since))

    if args.audit:
        print("{:<44} {:>7} {:>8} {:>8}".format("source", "rows", "events", "skipped"))
        for k in sorted(audit):
            v = audit[k]
            flag = "" if not v["present"] else ("   <- SILENT" if v["rows"] and not v["events"] else "")
            print("{:<44} {:>7} {:>8} {:>8}{}".format(
                k, v["rows"], v["events"], v["skipped"], flag))
        return 0

    if args.notable:
        events = [e for e in events if e["severity"] in (ALERT, NOTE)]

    if args.json:
        for e in events:
            print(json.dumps(e, ensure_ascii=False))
        return 0

    for e in events:
        print("{:<26} {:<7} {:<16} {:<6} {:<16} {}".format(
            e["ts"][:26] or "-", e["severity"], e["repo"][:16], e["lane"] or "-",
            e["source"][:16], e["subject"][:96]))
    print("\n{} event(s) from {} source(s)".format(len(events), sum(1 for v in audit.values() if v["events"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
