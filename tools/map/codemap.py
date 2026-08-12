#!/usr/bin/env python3
"""Generated directory map, plus the standing prior-art audit.

Two instructions became one tool because both are the same failure: a fact
written into a document once and then trusted forever.

MAP. 351 tracked directories, 19 READMEs. A hand-written map of that is stale
before it is committed, so the map is generated from the repository and the
generated text is compared against the copy on disk. A purpose comes from the
directory's own SKILL.md, README.md, AGENTS.md or CLAUDE.md; only a directory
with none of those gets a row in docs/dir-purpose.txt. A row for a directory
that already self-documents is rejected, because a second copy of a purpose
string is the copy that goes stale. Directory line counts are deliberately not
in the map: a stamped LOC number would turn every one-line edit into a
documentation failure, while a file count changes only when the structure does.

PRIOR ART. "constantly audit yourself if there is a better lib" cannot be a
report. It is a per-component record with a review date, an expiry, and named
alternatives, and it expires the way a gate waiver expires. The set of
components that owe a record is derived from line count, not from a list, so
code cannot be born exempt.

  python tools/map/codemap.py write        regenerate docs/CODEBASE-MAP.md
  python tools/map/codemap.py check        fail on undocumented, stale, drifted
  python tools/map/codemap.py prior-art    fail on missing or expired records
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import re
import subprocess
import sys

UNDOCUMENTED = "UNDOCUMENTED"
MAP_PATH = "docs/CODEBASE-MAP.md"
REGISTRY_PATH = "docs/dir-purpose.txt"
PRIOR_ART_DIR = "docs/prior-art"
SCOPE_PATH = "docs/prior-art/out-of-scope.txt"
SELF_DOC = ("SKILL.md", "README.md", "AGENTS.md", "CLAUDE.md")
PRIOR_ART_LOC = 300
# `evidence` is required because a build-vs-buy verdict reached by recalling what
# a library does is a different claim from one reached by reading its docs or
# running it, and the record has to say which it was.
PRIOR_ART_FIELDS = ("component", "reviewed", "recheck_after", "verdict", "why",
                    "alternatives", "evidence", "recheck")

# ABSORB-09. `verdict` is free text and stays free text, because the sentences
# are better than any enum would be: one of them reads "keep-provisionally, and
# it is the weakest of the three records written today", which no vocabulary
# expresses. What the sentence cannot do is answer "how many components did we
# decide to replace" without 41 file reads, so the enumerated field sits BESIDE
# the sentence rather than instead of it.
VERDICT_CLASSES = ("absorb", "adopt", "build", "delete-ours", "keep-ours",
                   "split", "wrap")

# ABSORB-01. The schema could not express absorption at all: 41 records shared
# 14 fields and not one of them named what was taken from the alternative. So
# absorption was unrepresentable, therefore unchecked, therefore never happened.
# `unreviewed` is a real value rather than a hole, and it is bounded by the
# record's own `recheck_after`: a record cannot expire while still claiming
# nobody has looked.
ABSORPTION_STATUSES = ("absorbed", "adopted", "used-as-is", "rejected-with-reason",
                       "unreviewed")
ABSORPTION_NEEDS_DETAIL = ("absorbed", "adopted", "used-as-is", "rejected-with-reason")
BACKFILL_CMD = "python tools/audit/absorption_backfill.py apply"
RENDER_CAP = 180

# The map is a tracked file in docs/. Counting it would make generation clean
# before its own commit and drifted after it, permanently.
GENERATED = (MAP_PATH,)


@dataclasses.dataclass
class Dir:
    path: str
    files: int
    purpose: str
    source: str


# A `git(args: str, cwd: str)` helper used to live here. It ran
# `subprocess.run("git " + args, shell=True)`, which is command injection the
# moment any caller passes a string it did not write itself. It had ZERO callers
# anywhere in the repository, so on 2026-07-27 it was deleted rather than
# hardened: dead code carrying a security finding is a liability that only ever
# grows a caller later. tracked_files() below makes the one git call this module
# actually needs, with a literal argv and no shell.


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def from_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    block = text[3:end] if end > 0 else text
    m = re.search(r"^description:[ \t]*(.*)$", block, re.M)
    if not m:
        return ""
    head = m.group(1).strip()
    if head not in (">", ">-", ">+", "|", "|-", "|+", ""):
        return one_line(head)
    folded: list[str] = []
    for line in block[m.end():].splitlines():
        if not line.strip():
            if folded:
                break
            continue
        if not line.startswith((" ", "\t")):
            break
        folded.append(line.strip())
    return one_line(" ".join(folded))


def first_prose(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", "<!--", ">", "-", "*", "|", "```", "=", "!")):
            continue
        return one_line(s)
    return ""


def read_registry(project: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in read(os.path.join(project, REGISTRY_PATH)).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        key, _, val = line.partition("|")
        key, val = key.strip().rstrip("/"), val.strip()
        if key and val:
            rows[key] = val
    return rows


def resolve(project: str, path: str, registry: dict[str, str]) -> tuple[str, str]:
    for name in SELF_DOC:
        full = os.path.join(project, path, name)
        if not os.path.exists(full):
            continue
        text = read(full)
        got = from_frontmatter(text) if name == "SKILL.md" else ""
        got = got or first_prose(text)
        if got:
            return got, name
    if path in registry:
        return one_line(registry[path]), "registry"
    return UNDOCUMENTED, "none"


def tracked(project: str) -> list[str]:
    """Every tracked path, read as bytes and decoded here.

    `git ls-files` C-quotes any path with a byte outside ASCII: a Hebrew folder
    arrives as "\\327\\236..." wrapped in literal quotes. Splitting that on
    newlines yields a directory whose name starts with a quote character, which
    matches no registry row and can never be documented, so the check demands a
    row for a path that does not exist. Five of this repository's 194
    undocumented directories were that bug rather than real gaps.

    -z turns the quoting off at the source and separates records with NUL, so
    there is nothing to unescape and a path containing a newline cannot split a
    record either.
    """
    # Literal argv, no shell. The argument list is fixed and contains nothing
    # caller-supplied, so a shell buys nothing here and only widens the surface.
    p = subprocess.run(["git", "ls-files", "-z"], cwd=project, shell=False,
                       capture_output=True, timeout=120)
    if p.returncode != 0:
        return []
    out = p.stdout.decode("utf-8", "replace")
    return [x for x in out.split("\0") if x and x not in GENERATED]


def inventory(project: str) -> list[Dir]:
    registry = read_registry(project)
    direct: dict[str, int] = {}
    seen: set[str] = set()
    for rel in tracked(project):
        parts = rel.split("/")
        if len(parts) == 1:
            continue
        direct["/".join(parts[:-1])] = direct.get("/".join(parts[:-1]), 0) + 1
        for i in range(1, len(parts)):
            seen.add("/".join(parts[:i]))
    out = []
    for path in sorted(seen):
        purpose, source = resolve(project, path, registry)
        out.append(Dir(path, direct.get(path, 0), purpose, source))
    return out


# ------------------------------------------------------------------ render

def cell(text: str) -> str:
    # &#124; not \| : a backslash-escaped pipe still contains a pipe character,
    # so a purpose string carrying one would silently add a column.
    trimmed = text if len(text) <= RENDER_CAP else text[:RENDER_CAP - 3].rstrip() + "..."
    return trimmed.replace("|", "&#124;")


def render(dirs: list[Dir]) -> str:
    undoc = [d for d in dirs if d.source == "none"]
    lines = [
        "# Codebase map",
        "",
        "Generated by `python tools/map/codemap.py write`. Do not edit: `check` compares",
        "this file against the repository and a hand edit reads as drift. To change a",
        "purpose, edit the directory's own SKILL.md or README.md, or its row in",
        "`docs/dir-purpose.txt` when it has neither.",
        "",
        "No timestamp and no commit sha here on purpose: either would make the map drift",
        "on every commit and train a reader to ignore the check. Line counts are out for",
        "the same reason, one level down.",
        "",
        "{} directories, {} tracked files, {} without a stated purpose.".format(
            len(dirs), sum(d.files for d in dirs), len(undoc)),
        "",
    ]
    areas: dict[str, list[Dir]] = {}
    for d in dirs:
        areas.setdefault(d.path.split("/")[0], []).append(d)
    for area in sorted(areas):
        lines += ["## {}".format(area), "",
                  "| dir | files | purpose | from |",
                  "| --- | ----: | ------- | ---- |"]
        for d in areas[area]:
            lines.append("| `{}` | {} | {} | {} |".format(
                d.path, d.files, cell(d.purpose), d.source))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------ checks

def map_rows(text: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        m = re.match(r"\| `([^`]+)` \| (.*) \|$", line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def evaluate(project: str) -> dict:
    registry = read_registry(project)
    dirs = inventory(project)
    known = {d.path for d in dirs}
    wanted = render(dirs)
    on_disk = read(os.path.join(project, MAP_PATH))
    want_rows, have_rows = map_rows(wanted), map_rows(on_disk)
    return {
        "dirs": len(dirs),
        "missing_rows": sorted(set(want_rows) - set(have_rows)),
        "extra_rows": sorted(set(have_rows) - set(want_rows)),
        "changed_rows": sorted(p for p in set(want_rows) & set(have_rows)
                               if want_rows[p] != have_rows[p]),
        "undocumented": sorted(d.path for d in dirs if d.source == "none"),
        "stale_rows": sorted(p for p in registry if p not in known),
        "shadow_rows": sorted(d.path for d in dirs
                              if d.path in registry and d.source != "registry"),
        "drifted": wanted != on_disk,
        "map_present": bool(on_disk),
        "rendered": wanted,
    }


def problems(state: dict) -> list[str]:
    out = []
    if state["undocumented"]:
        out.append("{} directory(ies) with no purpose. Add a README.md, or a row in {}:\n  {}".format(
            len(state["undocumented"]), REGISTRY_PATH, "\n  ".join(state["undocumented"])))
    if state["stale_rows"]:
        out.append("{} registry row(s) naming a directory that is not in the repository. "
                   "A row that outlives its directory keeps asserting a purpose nobody can "
                   "open:\n  {}".format(len(state["stale_rows"]), "\n  ".join(state["stale_rows"])))
    if state["shadow_rows"]:
        out.append("{} registry row(s) for a directory that already documents itself. The "
                   "directory's own file is the source of truth; a row beside it is a copy "
                   "that drifts, whether it agrees today or not. Delete the row:\n  {}".format(
                       len(state["shadow_rows"]), "\n  ".join(state["shadow_rows"])))
    if state["drifted"]:
        # Naming the differing rows, not just "drifted": a check that reports a
        # mismatch without saying which one sends the reader to regenerate and
        # diff by hand, and a reader who does that twice stops reading the check.
        detail = ""
        for label, rows in (("only in the repository", state["missing_rows"]),
                            ("only in the map", state["extra_rows"]),
                            ("different", state["changed_rows"])):
            if rows:
                detail += "\n  {}: {}".format(label, ", ".join(rows[:12]))
        out.append("{} is {}. Run `python tools/map/codemap.py write`.{}".format(
            MAP_PATH, "missing" if not state["map_present"] else
            "not what the repository implies", detail))
    return out


def py_loc(project: str) -> dict[str, int]:
    loc: dict[str, int] = {}
    for rel in tracked(project):
        if not rel.endswith(".py") or "/" not in rel:
            continue
        d = rel.rsplit("/", 1)[0]
        loc[d] = loc.get(d, 0) + len(read(os.path.join(project, rel)).splitlines())
    return loc


def read_records(project: str) -> tuple[dict[str, dict], list[str]]:
    found: dict[str, dict] = {}
    broken: list[str] = []
    base = os.path.join(project, PRIOR_ART_DIR)
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if not name.endswith(".json"):
            continue
        rel = "{}/{}".format(PRIOR_ART_DIR, name)
        try:
            rec = json.loads(read(os.path.join(base, name)))
        except ValueError as exc:
            broken.append("{}: not valid JSON ({})".format(rel, exc))
            continue
        missing = [f for f in PRIOR_ART_FIELDS if not rec.get(f)]
        if missing:
            broken.append("{}: missing or empty {}".format(rel, ", ".join(missing)))
            continue
        found[str(rec["component"]).strip().rstrip("/")] = rec
    return found, broken


def absorption_problems(component: str, rec: dict) -> list[str]:
    """Fault the two fields ABSORB-01 and ABSORB-09 added, on one record.

    Pure by construction so the selftest can plant every defect without writing
    a file. Kept separate from audit_prior_art for the same reason: a check
    reachable only through a directory walk is a check the mutation runner has
    to build a repository to break.
    """
    out = []
    klass = rec.get("verdict_class")
    if not klass:
        out.append("{}: no verdict_class beside its free-text verdict. The sentence "
                   "stays; add the enumerated field. Run: {}".format(component, BACKFILL_CMD))
    elif klass not in VERDICT_CLASSES:
        out.append("{}: verdict_class {!r} is not one of {}".format(
            component, klass, ", ".join(VERDICT_CLASSES)))

    status = rec.get("absorption_status")
    if not status:
        out.append("{}: no absorption_status, so what this evaluation took from its "
                   "alternatives is unrepresentable and therefore unchecked. Run: "
                   "{}".format(component, BACKFILL_CMD))
    elif status not in ABSORPTION_STATUSES:
        out.append("{}: absorption_status {!r} is not one of {}".format(
            component, status, ", ".join(ABSORPTION_STATUSES)))
    elif status in ABSORPTION_NEEDS_DETAIL and not str(rec.get("absorbed", "")).strip():
        # A status with nothing named beside it is the free-text problem wearing
        # an enum: it groups cleanly and says nothing. "absorbed" has to name
        # what was taken and the file it landed in, and the rejecting statuses
        # have to name the reason, or the field is decoration.
        out.append("{}: absorption_status is {!r} and `absorbed` is empty. Name what "
                   "was taken and the file it landed in, or the reason it was "
                   "not.".format(component, status))
    return out


def read_scope(project: str) -> list[tuple[str, str]]:
    rows = []
    for line in read(os.path.join(project, SCOPE_PATH)).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        prefix, _, reason = line.partition("|")
        if prefix.strip() and reason.strip():
            rows.append((prefix.strip().rstrip("/"), reason.strip()))
    return rows


def audit_prior_art(project: str, today: datetime.date) -> tuple[list[str], dict]:
    loc = py_loc(project)
    scope = read_scope(project)
    over = sorted(d for d, n in loc.items() if n >= PRIOR_ART_LOC)
    excluded = {}
    owing = []
    for d in over:
        hit = next((r for p, r in scope if d == p or d.startswith(p + "/")), None)
        if hit:
            excluded[d] = hit
        else:
            owing.append(d)
    records, out = read_records(project)
    dirs = {d.path for d in inventory(project)}
    for component in owing:
        rec = records.get(component)
        if rec is None:
            out.append("{} is {} lines of Python with no prior-art record. Write "
                       "{}/<name>.json naming what else could do this job.".format(
                           component, loc[component], PRIOR_ART_DIR))
            continue
        try:
            until = datetime.date.fromisoformat(str(rec["recheck_after"]))
        except ValueError:
            out.append("{}: recheck_after is not an ISO date".format(component))
            continue
        if until < today:
            owed = (" This record also still reports absorption_status unreviewed, so "
                    "the recheck decides that too."
                    if rec.get("absorption_status") == "unreviewed" else "")
            out.append("{}: prior-art record expired {}. Re-run its recheck: {}{}".format(
                component, until.isoformat(), rec.get("recheck"), owed))
    # Over every record, not only the ones a line count currently obliges. A
    # component can drop under 300 lines and keep its record, and the absorption
    # question does not stop mattering when it does.
    for component in sorted(records):
        out.extend(absorption_problems(component, records[component]))
        if component not in dirs:
            out.append("{}: prior-art record for a directory that is not in the "
                       "repository".format(component))
    unreviewed = sorted(c for c, r in records.items()
                        if r.get("absorption_status") == "unreviewed")
    return out, {"owing": owing, "recorded": sorted(records), "loc": loc,
                 "excluded": excluded, "unreviewed_absorption": unreviewed}


# ------------------------------------------------------------------ cli

def cmd_write(args) -> int:
    state = evaluate(args.project)
    dest = os.path.join(args.project, MAP_PATH)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(state["rendered"])
    print("wrote {} ({} dirs, {} undocumented)".format(
        MAP_PATH, state["dirs"], len(state["undocumented"])))
    return 0


def cmd_check(args) -> int:
    state = evaluate(args.project)
    found = problems(state)
    if args.json:
        print(json.dumps({k: v for k, v in state.items() if k != "rendered"} |
                         {"problems": found}, indent=2))
        return 1 if found else 0
    if not found:
        print("map clean: {} dirs, all with a stated purpose, {} matches the repository".format(
            state["dirs"], MAP_PATH))
        return 0
    for p in found:
        print("FAIL " + p)
    return 1


def cmd_prior_art(args) -> int:
    found, detail = audit_prior_art(args.project, datetime.date.today())
    if args.json:
        print(json.dumps({"problems": found, **detail}, indent=2))
        return 1 if found else 0
    # Printed on the pass path too. An exclusion nobody sees is a silent
    # suppression, and the point of the file is that dropping a component from
    # the audit costs a visible line with a reason attached.
    for path, reason in sorted(detail["excluded"].items()):
        print("out of scope {} ({} lines): {}".format(path, detail["loc"][path], reason))
    if not found:
        # The unreviewed count is printed on the PASS path on purpose. It is the
        # measured absorption rate across every external evaluation this repo has
        # made, and a number that only appears when something is broken is a
        # number nobody watches.
        n = len(detail["unreviewed_absorption"])
        print("prior art current: {} component(s) over {} lines, all with an unexpired "
              "record. {} of {} record(s) still report absorption_status unreviewed; "
              "each is decided no later than its own recheck_after.".format(
                  len(detail["owing"]), PRIOR_ART_LOC, n, len(detail["recorded"])))
        return 0
    for p in found:
        print("FAIL " + p)
    return 1


def cmd_selftest(args) -> int:
    """Plant one defect per guarantee this module makes, and prove each is caught.

    Added 2026-07-27. Until then codemap.py owned two required gate domains
    (`codemap` and `prior_art`) with no selftest verb at all, which meant
    tools/audit/mutate.py had nothing to run against it and its checks were
    unfalsified: a check that can never fail and a check that never fires are
    indistinguishable from outside.

    Every assertion below is over a pure function. Nothing here touches git, the
    filesystem or the network, so this verb is safe to run anywhere.
    """
    rc = 0

    def ok(cond: bool, what: str, detail: str = "") -> None:
        nonlocal rc
        print(("[ok]   " if cond else "[FAIL] ") + what
              + (f"  <- {detail}" if not cond and detail else ""))
        if not cond:
            rc = 1

    # cell(): a purpose string containing a pipe must not gain a column. The
    # comment at its definition is explicit that backslash-escaping is wrong
    # because the pipe character survives it.
    piped = cell("takes a|b and returns c")
    ok("|" not in piped and "&#124;" in piped,
       "a pipe in a purpose is entity-escaped, not backslash-escaped", repr(piped))
    long = cell("x" * (RENDER_CAP + 50))
    ok(len(long) <= RENDER_CAP and long.endswith("..."),
       "an over-long purpose is capped and marked elided", str(len(long)))

    # render()/map_rows() round trip: the map is parsed back by check(), so a
    # rendering the parser cannot read makes every comparison silently empty.
    d = Dir(path="tools/map", files=3, purpose="draws the map", source="README.md")
    text = render([d])
    rows = map_rows(text)
    ok("tools/map" in rows, "a rendered row is parseable by the checker", str(list(rows)[:3]))
    ok(rows.get("tools/map", "").startswith("3 |"),
       "the parsed row carries the file count", rows.get("tools/map", ""))

    piped_dir = Dir(path="a/b", files=1, purpose="reads a|b", source="README.md")
    ok("a/b" in map_rows(render([piped_dir])),
       "a row whose purpose contains a pipe still parses as ONE row")

    # render() must state the undocumented count, because that number is the
    # entire point of the map.
    undoc = Dir(path="x/y", files=2, purpose=UNDOCUMENTED, source="none")
    ok("1 without a stated purpose" in render([undoc]),
       "the header counts directories with no stated purpose")

    # problems(): each state key must produce a message. A state that reports a
    # fault silently is the failure mode the gate exists to prevent.
    base = {"undocumented": [], "stale_rows": [], "shadow_rows": [], "drifted": False,
            "map_present": True, "missing_rows": [], "extra_rows": [], "changed_rows": []}
    ok(problems(dict(base)) == [], "a clean state reports no problems")

    for key, label in (("undocumented", "undocumented directories"),
                       ("stale_rows", "registry rows naming a missing directory"),
                       ("shadow_rows", "registry rows shadowing a self-documenting dir")):
        st = dict(base)
        st[key] = ["a/b"]
        ok(len(problems(st)) == 1, "{} are reported".format(label))

    st = dict(base)
    st.update(drifted=True, changed_rows=["docs/analysis"])
    msgs = problems(st)
    ok(len(msgs) == 1 and "docs/analysis" in msgs[0],
       "a drifted map NAMES the differing row, not just 'drifted'",
       msgs[0][:80] if msgs else "no message")

    st = dict(base)
    st.update(drifted=True, map_present=False)
    absent = problems(st)
    # Substring matching on "missing" is not enough: a mutation that renders
    # "not missing" satisfies it. Mutation testing found exactly that hole in the
    # first version of this assertion, so the check is on the whole phrase and on
    # the absence of the drift wording it must NOT use.
    ok(any("is missing." in m for m in absent)
       and not any("not what the repository implies" in m for m in absent),
       "a map that does not exist says 'is missing', not the drift wording",
       absent[0][:90] if absent else "no message")

    # absorption_problems(): ABSORB-01 and ABSORB-09. The schema could not say
    # what an evaluation took from its alternatives, so absorption was
    # unrepresentable and therefore never measured. These pin that the two new
    # fields are required, that both vocabularies are closed, and that a status
    # claiming a decision must name it.
    whole = {"verdict_class": "keep-ours", "absorption_status": "unreviewed"}
    ok(absorption_problems("c", whole) == [],
       "a record carrying both fields with nothing claimed is clean")
    # Assert the MESSAGE, not the count. A count-only assertion cannot tell the
    # missing-field branch from the invalid-value branch one line below it: with
    # the missing-field check disabled, a None value falls through to the
    # vocabulary check and still produces exactly one message. Mutation testing
    # found precisely that, and both of these passed for the wrong reason until
    # they named the wording each branch owns.
    no_class = absorption_problems("c", {"absorption_status": "unreviewed"})
    ok(len(no_class) == 1 and "no verdict_class" in no_class[0],
       "a record with no verdict_class is faulted AS MISSING, not as invalid",
       no_class[0][:90] if no_class else "no message")
    no_status = absorption_problems("c", {"verdict_class": "keep-ours"})
    ok(len(no_status) == 1 and "no absorption_status" in no_status[0],
       "a record with no absorption_status is faulted AS MISSING, not as invalid",
       no_status[0][:90] if no_status else "no message")
    ok(len(absorption_problems("c", dict(whole, verdict_class="probably"))) == 1,
       "verdict_class is a CLOSED vocabulary, not any string")
    ok(len(absorption_problems("c", dict(whole, absorption_status="probably"))) == 1,
       "absorption_status is a CLOSED vocabulary, not any string")
    claimed = absorption_problems("c", dict(whole, absorption_status="absorbed"))
    ok(len(claimed) == 1 and "absorbed` is empty" in claimed[0],
       "a status claiming a decision must NAME what was taken",
       claimed[0][:90] if claimed else "no message")
    ok(absorption_problems(
        "c", dict(whole, absorption_status="absorbed", absorbed="the elision rule")) == [],
       "the same status with the detail named is clean")
    # The failure message has to carry the fix. A record fails here at the
    # moment somebody adds a component, which is the moment they have the least
    # context about a schema field that did not exist last week.
    named = absorption_problems("c", {})
    ok(all(BACKFILL_CMD in m for m in named) and len(named) == 2,
       "both missing-field messages name the command that writes them",
       str(named)[:120])

    print("\nVERDICT: {}".format(
        "every planted defect is caught" if rc == 0 else "codemap selftest has failures above"))
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("write", "check", "prior-art", "selftest"))
    ap.add_argument("--project", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    args.project = os.path.abspath(args.project)
    return {"write": cmd_write, "check": cmd_check, "prior-art": cmd_prior_art,
            "selftest": cmd_selftest}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
