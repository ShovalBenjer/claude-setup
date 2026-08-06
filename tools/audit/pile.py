#!/usr/bin/env python3
"""Name every duplicate and every fork in the pile, before anything is deleted.

WHY THIS EXISTS

claude-setup accumulated by absorbing past work directories, and nothing ever
reconciled them. Measured 2026-08-06 on 1,864 tracked files:

  984 tracked .md files, 111 distinct contents appearing more than once,
  118 redundant copies. `master-plans/`, `research-papers/home-md/` and
  `work-docs/root-cleanup-2026-05-28/` are three copies of one 2026-05 snapshot.

  118 distinct skill names across the three payload trees. 36 are byte-identical
  across trees, 43 genuinely DIVERGE, 39 exist once.

Those two numbers need opposite treatment and that is the whole point of this
tool. A byte-identical copy is waste and collapsing it loses nothing. A fork is a
decision: somebody changed one copy and not the other, and picking a survivor by
policy rather than by reading would destroy work. `shoval-voice-draft` is 10,935
bytes in the repo and 27,878 live; a naive "repo wins" merge deletes 17KB of the
newer thing.

So this tool does not merge. It emits the manifest that a merge would need, one
row per duplicate group, naming a PROPOSED survivor and the evidence for it. The
deletion happens afterwards, against the manifest, so the ledger is the record of
what was collapsed rather than a git diff nobody reads.

WHY NOT JUST SYNC

`skills_sync.py` keeps trees in agreement, which is the right tool if you intend
to keep several trees. The operator's instruction on 2026-08-06 was the opposite:
merge them, because parallel trees are how the same skill drifts into three
versions and how a routed persona ends up pointing at the one copy that cannot
load.

RELATIONSHIP TO tools/corpus/extract.py

They are different corpora and must not be confused. `extract.py` (written in a
parallel session the same day) extracts CONVERSATION turns from session
transcripts under ~/.claude/projects, for embedding the operator's own words.
This one indexes the repository's DOCUMENTS and skills. Neither subsumes the
other, and both feed analysis rather than performing it.

WHAT IT DOES NOT DO

It does not read content to judge which fork is better. The proposed survivor is
chosen by a stated, dumb rule (newest git touch, then largest, then tree order),
and the row carries every candidate so a human can overrule it. `proposed` is not
`decided`; nothing in this file should be deleted on its say-so alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PAYLOAD_TREES = ["dot-claude/skills", "dot-agents/skills", "dot-codex/skills"]
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv"}

# Identical content is not always redundant. A runtime looks for its instructions
# at a fixed filename, so the same bytes at two such paths is deliberate
# placement, not waste. Found the hard way on 2026-08-06: the first manifest
# proposed deleting `dot-codex/AGENTS.md` because it is byte-identical to the
# root `CLAUDE.md`. That file IS how Codex gets its instructions, and collapsing
# it would have silently unconfigured a whole runtime. Never propose these for
# removal, however many copies exist.
PROTECTED_BASENAMES = {"AGENTS.md", "CLAUDE.md", "SKILL.md", "README.md",
                       "LICENSE.md", "CODEOWNERS.md"}


def git_files(project: Path, pattern: str = "") -> list[str]:
    cmd = ["git", "-C", str(project), "ls-files"]
    if pattern:
        cmd.append(pattern)
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [f for f in out.split("\n") if f.strip()]


def last_touch(project: Path, path: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(project), "log", "-1", "--format=%ad", "--date=short",
         "--", path], capture_output=True, text=True).stdout.strip()
    return out or "unknown"


def file_hash(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def dir_signature(d: Path) -> str:
    """Content hash of a whole skill directory, ignoring build noise."""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in sorted(dirs) if x not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            p = Path(root) / f
            h.update(str(p.relative_to(d)).encode())
            try:
                h.update(p.read_bytes())
            except OSError:
                pass
    return h.hexdigest()


def doc_groups(project: Path) -> list[dict]:
    """Groups of .md files whose CONTENT is identical. Pure waste, safe to collapse.

    Files under the payload skill trees are excluded and handled by
    skill_groups instead. Without that, every duplicated SKILL.md is reported
    twice, once as a loose document and again as part of its skill, and the two
    counts then disagree about the same file. The selftest pins it: a planted
    identical pair of SKILL.md files must not appear in the document groups.
    """
    by_hash: dict[str, list[str]] = {}
    for f in git_files(project, "*.md"):
        if any(f.startswith(t + "/") for t in PAYLOAD_TREES):
            continue
        if os.path.basename(f) in PROTECTED_BASENAMES:
            continue
        h = file_hash(project / f)
        if h:
            by_hash.setdefault(h, []).append(f)
    rows = []
    for h, paths in by_hash.items():
        if len(paths) < 2:
            continue
        dated = [(p, last_touch(project, p)) for p in sorted(paths)]
        # Survivor rule, stated so it can be argued with: prefer the path under
        # docs/, else the shallowest path, else alphabetical. Deliberately not
        # "newest", because identical content has no newest.
        def rank(pd: tuple[str, str]) -> tuple[int, int, str]:
            p = pd[0]
            return (0 if p.startswith("docs/") else 1, p.count("/"), p)
        ordered = sorted(dated, key=rank)
        rows.append({
            "kind": "duplicate-doc", "sha256": h[:16],
            "copies": len(paths),
            "proposed_survivor": ordered[0][0],
            "proposed_removals": [p for p, _ in ordered[1:]],
            "last_touch": {p: d for p, d in dated},
            "rule": "prefer docs/, then shallowest path, then alphabetical",
        })
    return sorted(rows, key=lambda r: -r["copies"])


def skill_groups(project: Path) -> list[dict]:
    """Skill names present in more than one payload tree, split copy versus fork."""
    seen: dict[str, dict[str, str]] = {}
    for t in PAYLOAD_TREES:
        base = project / t
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                seen.setdefault(d.name, {})[t] = dir_signature(d)
    rows = []
    for name, sigs in sorted(seen.items()):
        if len(sigs) < 2:
            continue
        identical = len(set(sigs.values())) == 1
        dated = {t: last_touch(project, f"{t}/{name}") for t in sigs}
        sizes = {t: sum(f.stat().st_size for f in (project / t / name).rglob("*")
                        if f.is_file()) for t in sigs}
        # For a fork the survivor is a proposal only: newest git touch, then
        # largest. For an identical set any copy will do, so tree order decides.
        winner = (min(sigs, key=lambda t: PAYLOAD_TREES.index(t)) if identical
                  else sorted(sigs, key=lambda t: (dated[t], sizes[t]),
                              reverse=True)[0])
        rows.append({
            "kind": "identical-skill" if identical else "forked-skill",
            "skill": name, "trees": sorted(sigs),
            "signatures": {t: s[:12] for t, s in sigs.items()},
            "last_touch": dated, "bytes": sizes,
            "proposed_survivor": winner,
            "rule": ("any copy, tree order" if identical
                     else "newest git touch, then largest; PROPOSAL ONLY, read before acting"),
        })
    return rows


def cmd_scan(a: argparse.Namespace) -> int:
    project = Path(a.project).resolve()
    docs = doc_groups(project)
    skills = skill_groups(project)
    rows = docs + skills
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"schema": "pile.v1", **r}) + "\n")
        print(f"wrote {len(rows)} rows to {a.out}")
    redundant = sum(r["copies"] - 1 for r in docs)
    forks = [r for r in skills if r["kind"] == "forked-skill"]
    ident = [r for r in skills if r["kind"] == "identical-skill"]
    print(f"documents: {len(docs)} duplicate group(s), {redundant} redundant copies")
    print(f"skills:    {len(ident)} identical across trees (safe to collapse), "
          f"{len(forks)} forked (each needs a decision)")
    if a.verbose:
        for r in docs[:10]:
            print(f"  x{r['copies']}  keep {r['proposed_survivor']}")
        for r in forks:
            print(f"  fork {r['skill']:<24} proposed {r['proposed_survivor']}"
                  f"  ({', '.join(r['trees'])})")
    return 1 if (a.strict and forks) else 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    fails = []
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        subprocess.run(["git", "init", "-q", str(proj)], check=True)
        subprocess.run(["git", "-C", str(proj), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(proj), "config", "user.name", "t"], check=True)
        (proj / "docs").mkdir()
        (proj / "old").mkdir()
        (proj / "docs" / "a.md").write_text("same body\n")
        (proj / "old" / "a.md").write_text("same body\n")
        (proj / "docs" / "b.md").write_text("unique\n")
        (proj / "AGENTS.md").write_text("runtime instructions\n")
        (proj / "CLAUDE.md").write_text("runtime instructions\n")
        for t in PAYLOAD_TREES:
            (proj / t).mkdir(parents=True)
        (proj / PAYLOAD_TREES[0] / "twin").mkdir()
        (proj / PAYLOAD_TREES[1] / "twin").mkdir()
        (proj / PAYLOAD_TREES[0] / "twin" / "SKILL.md").write_text("identical\n")
        (proj / PAYLOAD_TREES[1] / "twin" / "SKILL.md").write_text("identical\n")
        # A duplicated NON-SKILL.md file inside two skills. SKILL.md alone cannot
        # test the payload-tree filter, because PROTECTED_BASENAMES already covers
        # that name, so a mutation disabling the filter survived until this existed.
        (proj / PAYLOAD_TREES[0] / "twin" / "reference.md").write_text("shared ref\n")
        (proj / PAYLOAD_TREES[1] / "twin" / "reference.md").write_text("shared ref\n")
        (proj / PAYLOAD_TREES[0] / "split").mkdir()
        (proj / PAYLOAD_TREES[1] / "split").mkdir()
        (proj / PAYLOAD_TREES[0] / "split" / "SKILL.md").write_text("version one\n")
        (proj / PAYLOAD_TREES[1] / "split" / "SKILL.md").write_text("version two, longer\n")
        subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(proj), "commit", "-qm", "x"], check=True)

        d = doc_groups(proj)
        if len(d) != 1:
            fails.append(f"{len(d)} duplicate doc groups, want 1")
        elif d[0]["proposed_survivor"] != "docs/a.md":
            fails.append(f"survivor {d[0]['proposed_survivor']}, want docs/a.md (docs/ preferred)")
        elif d[0]["proposed_removals"] != ["old/a.md"]:
            fails.append("the non-surviving copy was not named for removal")

        s = {r["skill"]: r for r in skill_groups(proj)}
        if s.get("twin", {}).get("kind") != "identical-skill":
            fails.append(f"twin -> {s.get('twin',{}).get('kind')}, want identical-skill")
        if s.get("split", {}).get("kind") != "forked-skill":
            fails.append(f"split -> {s.get('split',{}).get('kind')}, want forked-skill")
        if "b.md" in json.dumps(d):
            fails.append("a file with unique content was reported as a duplicate")
        if "SKILL.md" in json.dumps(d):
            fails.append("a skill's SKILL.md was double-counted as a loose document")
        if "reference.md" in json.dumps(d):
            fails.append("a file inside a skill directory was counted as a loose "
                         "document; skills are reconciled by skill_groups")
        if "AGENTS.md" in json.dumps(d) or "CLAUDE.md" in json.dumps(d):
            fails.append("a runtime instruction file was proposed for removal; "
                         "identical bytes at a runtime path are placement, not waste")
        strict = argparse.Namespace(project=str(proj), out=None, verbose=False, strict=True)
        if cmd_scan(strict) != 1:
            fails.append("--strict exited 0 with a fork present")
    for f in fails:
        print(f"[FAIL] {f}")
    print("PASS pile selftest" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="emit the duplicate and fork manifest")
    s.add_argument("--project", default=".")
    s.add_argument("--out", default="")
    s.add_argument("-v", "--verbose", action="store_true")
    s.add_argument("--strict", action="store_true", help="exit 1 while any fork is unresolved")
    s.set_defaults(func=cmd_scan)
    t = sub.add_parser("selftest", help="prove copy/fork/unique on a planted repo")
    t.set_defaults(func=cmd_selftest)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
