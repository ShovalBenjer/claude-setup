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


def git(args: str, cwd: str) -> str:
    p = subprocess.run("git " + args, cwd=cwd, shell=True, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=120)
    return p.stdout.strip() if p.returncode == 0 else ""


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
    p = subprocess.run("git ls-files -z", cwd=project, shell=True,
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
            out.append("{}: prior-art record expired {}. Re-run its recheck: {}".format(
                component, until.isoformat(), rec.get("recheck")))
    for component in sorted(records):
        if component not in dirs:
            out.append("{}: prior-art record for a directory that is not in the "
                       "repository".format(component))
    return out, {"owing": owing, "recorded": sorted(records), "loc": loc,
                 "excluded": excluded}


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
        print("prior art current: {} component(s) over {} lines, all with an unexpired "
              "record".format(len(detail["owing"]), PRIOR_ART_LOC))
        return 0
    for p in found:
        print("FAIL " + p)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("write", "check", "prior-art"))
    ap.add_argument("--project", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    args.project = os.path.abspath(args.project)
    return {"write": cmd_write, "check": cmd_check, "prior-art": cmd_prior_art}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
