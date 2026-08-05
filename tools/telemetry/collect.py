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



def first_of(r: dict, *keys: str, default: str = "") -> str:
    """First non-empty value among `keys`, so one extractor reads both ledger generations.

    Measured 2026-08-05: 52 of 516 notable events reached the feed with an EMPTY subject
    payload and no timestamp, and every one of them came from `lessons` or `claims`. The
    cause is not a bug in the extractor's logic, it is that each extractor named ONE
    spelling of a field the ledger writes under two:

        lessons.jsonl  43 rows: id 43, status 43, lesson 33, ts 25, lane 25, class 20,
                                date 18, incident 18
        claims.jsonl   22 rows: lane 22, note 16, proposal_id 15, ts 15,
                                id 7, claimed_at 7, scope 7

    So `r.get("class")` finds nothing on 23 of 43 lesson rows and `r.get("scope")` finds
    nothing on 15 of 22 claim rows. The rows were carried, published, and said nothing.

    An empty string is treated as absent, not as a value. A ledger that writes `"ts": ""`
    is saying it does not know, and preferring it over a populated `date` would be reading
    the placeholder as data.
    """
    for k in keys:
        v = r.get(k)
        if v not in (None, ""):
            s = str(v).strip()
            if s:
                return s
    return default


def is_worktree(child: Path) -> bool:
    """True when `child/.git` is a FILE rather than a directory.

    Measured 2026-08-05: `.wt-rules-sync` contributed 212 of 516 notable events, byte
    identical to claude-setup's own rows. It is a git WORKTREE of claude-setup, created
    by this session to work around a concurrent writer in the main tree. A worktree's
    `.git` is a pointer file (`gitdir: .../worktrees/<name>`) rather than a directory, and
    its `state/*.jsonl` are tracked, so they are checked out a second time and read as if
    they belonged to a second repository.

    Nothing downstream can undo that. `fingerprint()` includes `repo`, deliberately,
    because the same lesson in two repos is two facts. So a duplicated repo name produces
    duplicated feed items that no dedupe is allowed to collapse.

    Keyed on the `.git` TYPE rather than on a dot prefix or a name pattern, because a
    worktree may be named anything and a real repository may be hidden. A submodule also
    writes a pointer file and is skipped for the same reason: its ledgers, if any, belong
    to the superproject's sweep of it, not to this one.
    """
    dotgit = child / ".git"
    return dotgit.is_file()


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
    # `class` on 20 of 43 rows, `lesson` on 33, `incident` on 18; `ts` on 25, `date` on 18.
    # Naming one spelling each is what published 22 lessons that said only "L006:".
    return event(ts=_iso(first_of(r, "ts", "date")), lane=r.get("lane", ""), source="lessons",
                 kind="lesson", severity=ALERT,
                 subject="{}: {}".format(first_of(r, "id", default="?"),
                                         first_of(r, "class", "lesson", "incident")[:160]),
                 ref=first_of(r, "id"))


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
    # `scope` on 7 of 22 rows, `note` on 16; `claimed_at` on 7, `ts` on 15; `id` on 7,
    # `proposal_id` on 15. Three fields, three spellings each, and the older generation
    # uses the second of every pair, which is why 30 claim rows published as
    # "lane B claimed:" with nothing after the colon.
    return event(ts=_iso(first_of(r, "claimed_at", "ts")), lane=r.get("lane", ""), source="claims",
                 kind="claim", severity=NOTE,
                 subject="lane {} claimed: {}".format(first_of(r, "lane", default="?"),
                                                      first_of(r, "scope", "note")[:140]),
                 ref=first_of(r, "id", "proposal_id"))


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


def discover_repos(skipped: list[str] | None = None) -> list[Path]:
    """Every git repo with a state/ directory, under the configured roots.

    Worktrees are excluded and RECORDED. A skip that leaves no trace is the failure this
    file's own docstring is about: a repo that silently stops being swept looks exactly
    like a repo that went quiet. `--audit` prints what was skipped and why.
    """
    out = []
    for root in REPO_ROOTS:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not ((child / ".git").exists() and (child / "state").is_dir()):
                continue
            if is_worktree(child):
                if skipped is not None:
                    skipped.append(child.name)
                continue
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
    """Return (events, per-source audit).

    UNDATED ROWS AND A WINDOW. Until 2026-08-05 the filter read `if since and ev["ts"]`,
    so a row with no derivable timestamp skipped the comparison and passed EVERY window
    forever. That is why the same blank claims rows appeared in all 12 published posts:
    they were not recent, they were permanent residents. A windowed query now excludes an
    undated row and counts it, because "I do not know when this happened" cannot answer
    "what happened in the last 24 hours". Unwindowed queries still carry them.
    """
    events: list[dict] = []
    audit: dict[str, dict] = {}
    skipped_worktrees: list[str] = []
    undated_dropped = 0
    for repo in discover_repos(skipped_worktrees):
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
                if since:
                    if not ev["ts"]:
                        undated_dropped += 1
                        continue
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
    audit["__meta__"] = {"rows": 0, "events": 0, "skipped": 0, "present": False,
                         "skipped_worktrees": sorted(skipped_worktrees),
                         "undated_dropped": undated_dropped}
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

    # Both ledger generations, from real rows. The OLD spelling is the one that was
    # dropped, so it is the one asserted; testing only the new spelling would pass
    # against the very code that shipped 52 empty rows.
    old_lesson = _from_lessons({"status": "open", "id": "L006", "date": "2026-07-27",
                                "incident": "a gate PASS was claimed from a stale ledger"})
    if not old_lesson["ts"]:
        failures.append("a lessons row that dates itself with `date` yields no timestamp, "
                        "so it passes every --since window forever")
    if old_lesson["subject"].rstrip().endswith(":"):
        failures.append("a lessons row that describes itself with `incident` publishes as "
                        "an id and an empty colon, which is what 22 of them did")
    old_claim = _from_claims({"lane": "B", "ts": "2026-07-31T14:05:00",
                              "proposal_id": "session-x", "note": "cross-lane, approved"})
    if not old_claim["ts"] or not old_claim["ref"]:
        failures.append("a claims row using `ts`/`proposal_id` yields no timestamp or no ref")
    if old_claim["subject"].rstrip().endswith(":"):
        failures.append("a claims row that describes itself with `note` publishes as "
                        "'lane B claimed:' and nothing else, which is what 30 of them did")
    if first_of({"a": "", "b": "   ", "c": "x"}, "a", "b", "c") != "x":
        failures.append("first_of read an empty or whitespace field as a value, so a "
                        "placeholder wins over a populated fallback")

    # The worktree rule, proved on a synthetic tree rather than on the live one, because
    # the live answer changes the moment somebody removes the worktree.
    import tempfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as td:
        wt, real = Path(td) / "wt", Path(td) / "real"
        (wt / "state").mkdir(parents=True)
        (wt / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n", encoding="utf-8")
        (real / "state").mkdir(parents=True)
        (real / ".git").mkdir()
        if not is_worktree(wt):
            failures.append("a .git POINTER FILE was read as a real repository, so a "
                            "worktree's checked-out ledgers are collected a second time")
        if is_worktree(real):
            failures.append("a real clone was skipped as a worktree, so a whole repo "
                            "goes silent with nothing reporting it")

        # The skip must be RECORDED. Proved against discover_repos itself, on a synthetic
        # root, because a skip that leaves no trace is indistinguishable from a tree that
        # went quiet and that ambiguity is what this file exists to remove.
        global REPO_ROOTS  # noqa: PLW0603
        saved_roots = REPO_ROOTS
        try:
            REPO_ROOTS = [Path(td)]
            noted: list[str] = []
            found = discover_repos(noted)
        finally:
            REPO_ROOTS = saved_roots
        if [p.name for p in found] != ["real"]:
            failures.append("discover_repos returned {} where it should have returned "
                            "only the real clone".format([p.name for p in found]))
        if noted != ["wt"]:
            failures.append("a skipped worktree was not recorded, so --audit cannot "
                            "report it and the omission reads as coverage")

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

    # EMPTINESS, per source. The assertion above counts events and passed while 52 of
    # them carried nothing a reader could act on. A row that is carried and says nothing
    # is worse than a row that is dropped, because it consumes a feed slot and looks like
    # coverage.
    def _blank_sources(evs: list[dict]) -> dict:
        out: dict[str, int] = {}
        for e in evs:
            if e["severity"] not in (ALERT, NOTE):
                continue
            body = e["subject"]
            for sep in (": ", " -> ", "] "):
                if sep in body:
                    body = body.split(sep, 1)[1]
                    break
            if not body.strip():
                out[e["source"]] = out.get(e["source"], 0) + 1
        return out

    # POSITIVE CONTROL, and it is the load-bearing half. The live corpus now has zero
    # blank rows, so an assertion that only reads the corpus passes whether the detector
    # works or has been deleted. Feed it a known-blank event first: a checker that cannot
    # be seen finding anything is a checker nobody can trust to find nothing.
    planted = [event(source="planted", severity=ALERT, subject="L006: ")]
    if _blank_sources(planted) != {"planted": 1}:
        failures.append("the empty-subject detector did not flag a planted blank row, so "
                        "its clean verdict on the real corpus proves nothing")

    blank = _blank_sources(events)
    if blank:
        failures.append("source(s) emitted an alert or note with an empty subject: "
                        + ", ".join("{}={}".format(k, v) for k, v in sorted(blank.items())))

    # The window, exercised against a PLANTED undated row rather than against the live
    # corpus. Asserting the corpus still contains undated rows would make this oracle
    # depend on the ledgers staying broken: the extractor fix above removed all 52 of
    # them, so a corpus-based assertion would have to be deleted the moment it started
    # being true. Plant one instead, so the rule is proved on input it must handle.
    with tempfile.TemporaryDirectory() as td2:
        planted_repo = Path(td2) / "planted"
        (planted_repo / "state").mkdir(parents=True)
        (planted_repo / ".git").mkdir()
        (planted_repo / "state" / "lessons.jsonl").write_text(
            json.dumps({"id": "L-UNDATED", "status": "open",
                        "lesson": "no timestamp anywhere on this row"}) + "\n",
            encoding="utf-8")
        saved_roots2 = REPO_ROOTS
        try:
            REPO_ROOTS = [Path(td2)]
            unwindowed, _ = collect()
            _, windowed_audit = collect(dt.datetime.now() - dt.timedelta(days=3650))
        finally:
            REPO_ROOTS = saved_roots2
        meta = windowed_audit.get("__meta__", {})
        if len(unwindowed) != 1:
            failures.append("an undated row is dropped even without a window, so the "
                            "rule is not a window rule at all")
        if meta.get("undated_dropped") != 1:
            failures.append("a windowed collect did not exclude a planted undated row "
                            "(reported {}), so such a row passes every window forever "
                            "and becomes a permanent feed resident".format(
                                meta.get("undated_dropped")))

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
    print("  ok    both ledger generations are read: date/incident and ts/proposal_id/note")
    print("  ok    an empty or whitespace field never wins over a populated fallback")
    print("  ok    a .git pointer file is a worktree and a .git directory is a repo")
    print("  ok    every ledger that has rows yields events ({} sources, {} events)".format(
        len(present), len(events)))
    print("  ok    no alert or note carries an empty subject, and a planted blank IS flagged")
    print("  ok    a skipped worktree is recorded, not dropped silently")
    print("  ok    a planted undated row survives an unwindowed query and is excluded from a windowed one")
    print("VERDICT: the collector reads every live ledger, no source is silently empty, "
          "and nothing is published that says nothing")
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
        meta = audit.get("__meta__", {})
        print("{:<44} {:>7} {:>8} {:>8}".format("source", "rows", "events", "skipped"))
        for k in sorted(audit):
            if k == "__meta__":
                continue
            v = audit[k]
            flag = "" if not v["present"] else ("   <- SILENT" if v["rows"] and not v["events"] else "")
            print("{:<44} {:>7} {:>8} {:>8}{}".format(
                k, v["rows"], v["events"], v["skipped"], flag))
        # Named, not silent. A worktree checks out the same tracked ledgers a second
        # time, so sweeping it double-counts every row under a repo name that no
        # fingerprint may merge.
        for name in meta.get("skipped_worktrees", []):
            print("skipped worktree: {} (its .git is a pointer file; its ledgers belong "
                  "to the repo it points at)".format(name))
        if meta.get("undated_dropped"):
            print("undated rows excluded by --since: {} (a row with no timestamp cannot "
                  "answer a question about a time window)".format(meta["undated_dropped"]))
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
