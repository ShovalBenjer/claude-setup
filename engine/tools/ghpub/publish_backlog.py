#!/usr/bin/env python
"""Publish state/github-backlog-*.json to GitHub issues, milestones, and a project board.

Why a script and not a session of `gh issue create` calls: a hand-clicked backlog cannot
be re-run, diffed, or corrected. This reads one JSON source, is idempotent by title, and
prints what it created versus what already existed, so a second run is safe and a partial
failure can be resumed rather than restarted.

Idempotency is by TITLE, not by id. That is the right key here because the JSON is the
source of truth and GitHub is the projection: renaming an epic in the JSON intentionally
creates a new issue rather than silently mutating an existing one, which keeps the audit
trail on GitHub's side.

Dry run by default. Pass --execute to write. Pass --project to also add each issue to the
project board named in the JSON.

Usage:
  python engine/tools/ghpub/publish_backlog.py --source knowledge/state/github-backlog-2026-07-30.json
  python engine/tools/ghpub/publish_backlog.py --source ... --execute --project
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def gh(args: list[str], check: bool = True) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode != 0:
        print("    gh failed: {}".format(out.strip()[:300]))
    return p.returncode, out.strip()


# ---------------------------------------------------------------- field sync
#
# The board carried seven custom fields that no code wrote. Measured 2026-07-31 on
# Zion (project 3): `Lane` held the letters ADR-0016 retired on 2026-07-30, and
# `Evidence` held one byte-identical string on 23 of 26 items. Neither defect is a
# typo. Both are what happens when a projection has a hand-maintained annex: there
# is no regeneration that would have corrected them, so they could only rot.
#
# This maps a backlog JSON key to the project field it owns. A field NOT in this
# table is not owned by the JSON and is never written here: `Status`, and anything
# that is a reaction to work happening, stay hand-set on GitHub. One writer per
# field is the property that makes drift detectable rather than merely regrettable.
FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("priority", "Priority"),
    ("session", "Ingestion"),
    ("lane", "Lane"),
    ("autonomy", "Autonomy"),
    ("evidence_state", "Evidence state"),
)


def item_key(field_name: str) -> str:
    """The key `gh project item-list` uses for a field, which is NOT the lowercased
    name. Measured 2026-07-31 with a disposable single-select field named `ZZ probe`:
    gh emitted the key `zZ probe`. It lowercases the FIRST character only. `.lower()`
    happens to be right for every field currently owned here because each is
    capitalised once, and would silently read None the first time one is not, which
    would make the idempotence check pass a write through on every run.
    """
    return field_name[:1].lower() + field_name[1:]


def resolve_option(field: dict, value: str) -> dict | None:
    """Resolve a JSON value to exactly one single-select option, or None.

    Three rules, tried in order, each requiring a unique winner:

      1. exact name  -- "agent-drafts" -> "agent-drafts"
      2. leading token -- "S2" -> "S2 45min", "A" -> "A harness"
      3. case-insensitive prefix -- "a harness" -> "A harness"

    Ambiguity returns None rather than picking one. The backlog says `S2` and the
    board says `S2 45min`; those are the same fact written twice, and a resolver
    is cheaper than forcing the JSON to carry GitHub's label text, which would
    make the JSON break every time an option is renamed.
    """
    opts = field.get("options") or []
    for rule in (
        lambda o: o["name"] == value,
        lambda o: o["name"].split(" ")[0] == value,
        lambda o: o["name"].lower().startswith(value.lower()),
    ):
        hits = [o for o in opts if rule(o)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None
    return None


def plan_field_writes(epics: list[dict], fields: list[dict],
                      items: list[dict]) -> list[dict]:
    """Pure planner: what would be written, and why each row is or is not written.

    Separated from the gh calls so the decision logic is testable without a network
    or a token. Returns one row per (epic, owned field) pair with an `action` of
    set / skip / no-field / no-item / unresolved. Nothing is dropped silently: a
    field the board does not have produces a `no-field` row, not an absence.
    """
    by_name = {f["name"]: f for f in fields}
    by_title = {i["title"]: i for i in items}
    plan: list[dict] = []
    for epic in epics:
        for key, fname in FIELD_MAP:
            value = epic.get(key)
            if value in (None, ""):
                continue
            row = {"title": epic["title"], "key": key, "field": fname,
                   "value": value, "item_id": None, "field_id": None,
                   "option_id": None, "action": "set"}
            field = by_name.get(fname)
            item = by_title.get(epic["title"])
            if field is None:
                row["action"] = "no-field"
                plan.append(row)
                continue
            row["field_id"] = field["id"]
            if item is None:
                row["action"] = "no-item"
                plan.append(row)
                continue
            row["item_id"] = item["id"]
            if field["type"] == "ProjectV2SingleSelectField":
                opt = resolve_option(field, str(value))
                if opt is None:
                    row["action"] = "unresolved"
                    plan.append(row)
                    continue
                row["option_id"] = opt["id"]
                row["resolved"] = opt["name"]
                if item.get(item_key(fname)) == opt["name"]:
                    row["action"] = "skip"
            else:
                row["resolved"] = str(value)
                if item.get(item_key(fname)) == str(value):
                    row["action"] = "skip"
            plan.append(row)
    return plan


def exit_code_for(counts: dict) -> int:
    """Which plan outcomes mean the board cannot be made to match the source.

    `no-item` is deliberately NOT one of them: an epic absent from the board is the
    normal state before `--project --execute` has run, and failing on it would make
    the first run of a new backlog look broken. The three that do fail are a field
    the board lacks, a value no option can represent, and a write that errored.
    """
    return 1 if any(counts.get(k) for k in ("no-field", "unresolved", "failed")) else 0


def sync_project_fields(data: dict, execute: bool) -> int:
    """Read the board, plan the writes, and (with --execute) apply them.

    Idempotent by construction: a row whose current value already equals the
    resolved value is planned as `skip`, so a second run writes nothing. Reads are
    unconditional because a plan built from a stale local cache is not a plan.
    """
    proj = data["project"]
    num, owner = str(proj["number"]), proj["owner"]
    pv = gh_json(["project", "view", num, "--owner", owner, "--format", "json"])
    if not pv or "id" not in pv:
        print("  FIELD SYNC skipped: cannot read project id for {} #{}".format(
            owner, num))
        return 1
    fields = (gh_json(["project", "field-list", num, "--owner", owner,
                       "--format", "json"]) or {}).get("fields", [])
    items = (gh_json(["project", "item-list", num, "--owner", owner,
                      "--limit", "300", "--format", "json"]) or {}).get("items", [])
    plan = plan_field_writes(data["epics"], fields, items)

    counts: dict[str, int] = {}
    for row in plan:
        counts[row["action"]] = counts.get(row["action"], 0) + 1
    print("\nFIELD SYNC  {} field(s) owned by the JSON, {} planned row(s)".format(
        len(FIELD_MAP), len(plan)))
    for action in ("no-field", "unresolved", "no-item"):
        for row in [r for r in plan if r["action"] == action]:
            print("  {:<11} {:<20} {:<16} {}".format(
                action.upper(), row["field"], str(row["value"])[:16],
                row["title"][:40]))
    for row in [r for r in plan if r["action"] == "set"]:
        print("  set    {:<20} -> {:<18} {}".format(
            row["field"], str(row.get("resolved"))[:18], row["title"][:38]))
        if not execute:
            continue
        args = ["project", "item-edit", "--id", row["item_id"],
                "--project-id", pv["id"], "--field-id", row["field_id"]]
        if row["option_id"]:
            args += ["--single-select-option-id", row["option_id"]]
        else:
            args += ["--text", str(row["value"])]
        rc, _ = gh(args)
        if rc != 0:
            counts["failed"] = counts.get("failed", 0) + 1
    print("  totals  " + ", ".join(
        "{}={}".format(k, v) for k, v in sorted(counts.items())) or "  totals  none")
    return exit_code_for(counts)


def gh_json(args: list[str]):
    rc, out = gh(args, check=False)
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def build_body(epic: dict, source: str = "state/github-backlog.json") -> str:
    """Epic body: priority and ingestion header, grounding paragraph, task checklist.

    Tasks starting with DONE are rendered checked, so a published epic shows real
    progress rather than resetting to zero every time the JSON is regenerated.

    `source` is threaded through rather than hardcoded. It used to name
    state/github-backlog-2026-07-30.json unconditionally, so publishing any later
    backlog told every reader to go edit a file that was not the one it came from.
    """
    head = []
    if epic.get("priority"):
        head.append("**{}**".format(epic["priority"]))
    if epic.get("session"):
        head.append("**Ingestion {}**".format(epic["session"]))
    if epic.get("estimate"):
        head.append("~{}".format(epic["estimate"]))
    lines = []
    if head:
        lines += ["  |  ".join(head), ""]
    lines += [epic["body_intro"], "", "## Tasks", ""]
    for t in epic["tasks"]:
        done = t.startswith("DONE")
        lines.append("- [{}] {}".format("x" if done else " ", t))
    lines += [
        "",
        "---",
        "",
        "Generated from `{}` by ".format(source) +
        "`tools/ghpub/publish_backlog.py`. Edit the JSON, not this body: a hand edit here "
        "will not survive a regeneration and will read as drift.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--project", action="store_true",
                    help="also add each issue to the project named in the JSON")
    ap.add_argument("--fields", action="store_true",
                    help="sync the project field values the JSON owns (Priority, "
                         "Ingestion, Lane, Autonomy, Evidence state). Reads the "
                         "board first and plans; writes only with --execute")
    ap.add_argument("--update", action="store_true",
                    help="for a title that already exists, sync its body, labels and "
                         "milestone from the JSON instead of skipping it")
    a = ap.parse_args()

    src = Path(a.source)
    data = json.loads(src.read_text(encoding="utf-8"))
    repo = data["repo"]
    mode = "EXECUTE" if a.execute else "DRY RUN"
    print("{}  repo={}  source={}".format(mode, repo, src))

    # ---------------------------------------------------------------- labels
    existing = {l["name"] for l in (gh_json(["label", "list", "--repo", repo,
                                             "--limit", "200",
                                             "--json", "name"]) or [])}
    print("\nLABELS  existing={}".format(len(existing)))
    for lab in data["labels"]:
        if lab["name"] in existing:
            print("  skip   {}".format(lab["name"]))
            continue
        print("  create {}".format(lab["name"]))
        if a.execute:
            gh(["label", "create", lab["name"], "--repo", repo,
                "--color", lab["color"], "--description", lab["description"]])

    # ------------------------------------------------------------ milestones
    ms = gh_json(["api", "repos/{}/milestones?state=all&per_page=100".format(repo)]) or []
    ms_by_title = {m["title"]: m["number"] for m in ms}
    print("\nMILESTONES  existing={}".format(len(ms_by_title)))
    for m in data["milestones"]:
        if m["title"] in ms_by_title:
            print("  skip   {}".format(m["title"]))
            continue
        print("  create {}".format(m["title"]))
        if a.execute:
            r = gh_json(["api", "repos/{}/milestones".format(repo), "-X", "POST",
                         "-f", "title={}".format(m["title"]),
                         "-f", "description={}".format(m["description"])])
            if r:
                ms_by_title[m["title"]] = r["number"]

    # ---------------------------------------------------------------- issues
    open_issues = gh_json(["issue", "list", "--repo", repo, "--state", "all",
                           "--limit", "300", "--json", "number,title"]) or []
    by_title = {i["title"]: i["number"] for i in open_issues}
    print("\nISSUES  existing={}".format(len(by_title)))

    created = []
    for epic in data["epics"]:
        title = epic["title"]
        if title in by_title:
            num = by_title[title]
            if not a.update:
                print("  skip   #{} {}".format(num, title))
                created.append((num, title))
                continue
            # An epic that already exists is the normal case on every run after the
            # first, and skipping it means a task marked DONE in the JSON never
            # reaches the board. --update syncs the projection instead.
            ndone = sum(1 for t in epic["tasks"] if t.startswith("DONE"))
            print("  update #{} {}  ({}/{} done)".format(
                num, title[:58], ndone, len(epic["tasks"])))
            if a.execute:
                args = ["issue", "edit", str(num), "--repo", repo,
                        "--body", build_body(epic, str(src))]
                for lab in epic["labels"]:
                    args += ["--add-label", lab]
                if epic.get("milestone"):
                    args += ["--milestone", epic["milestone"]]
                gh(args)
            created.append((num, title))
            continue
        ntasks = len(epic["tasks"])
        print("  create {}  ({} tasks)".format(title, ntasks))
        if not a.execute:
            continue
        args = ["issue", "create", "--repo", repo, "--title", title,
                "--body", build_body(epic, str(src))]
        for lab in epic["labels"]:
            args += ["--label", lab]
        if epic.get("milestone"):
            args += ["--milestone", epic["milestone"]]
        rc, out = gh(args)
        if rc == 0:
            url = out.strip().splitlines()[-1]
            num = url.rstrip("/").split("/")[-1]
            print("         -> {}".format(url))
            created.append((num, title))

    # --------------------------------------------------------------- project
    if a.project and a.execute:
        proj = data["project"]
        print("\nPROJECT  adding {} issue(s) to {} #{}".format(
            len(created), proj["title"], proj["number"]))
        for num, title in created:
            url = "https://github.com/{}/issues/{}".format(repo, num)
            rc, out = gh(["project", "item-add", str(proj["number"]),
                          "--owner", proj["owner"], "--url", url], check=False)
            print("  {:>6} {}  {}".format(
                num, "added" if rc == 0 else "FAILED", title[:52]))
    elif a.project:
        print("\nPROJECT  skipped: --project requires --execute")

    # Field sync plans on a dry run rather than refusing to run. The plan is built
    # from reads only, so showing it costs nothing and is the whole point of a dry
    # run: seeing which of the 26 items would change before any of them do.
    rc = 0
    if a.fields:
        rc = sync_project_fields(data, a.execute)

    total_tasks = sum(len(e["tasks"]) for e in data["epics"])
    print("\nSUMMARY  {} milestone(s), {} epic(s), {} task checkbox(es)".format(
        len(data["milestones"]), len(data["epics"]), total_tasks))
    if not a.execute:
        print("DRY RUN: nothing was written. Re-run with --execute.")
    # Non-zero when the board cannot be made to match the source: a field the board
    # does not have, a value no option can represent, or a failed write. A detector
    # that always exits 0 is a detector nothing can be wired to.
    return rc


if __name__ == "__main__":
    sys.exit(main())
