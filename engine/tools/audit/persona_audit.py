#!/usr/bin/env python3
"""Can a routed persona actually execute, or is it only named.

WHY THIS EXISTS

The gastown registry is the routing map: 19 personas, 98 owned skills, and a
deterministic hook that names one of them on almost every prompt. Nothing checked
whether the thing being routed to can do anything. Measured 2026-08-06:

  98 owned skills declared, 95 resolve to a directory somewhere in the repo,
  23 load in a live Claude Code session. 7 personas have ZERO live skills.
  3 personas owned a skill that writes files and had no Edit or Write tool.
  0 spawns have ever been recorded in state/agent-spawns.jsonl.
  The corpus tree the registry tells personas to use does not exist at all.

The mechanism behind most of it is a tree mismatch. The registry was written
against the repo payload (dot-claude/skills, dot-agents/skills), and the runtime
loads ~/.claude/skills. `skills_sync.py check` measures that drift and exits 0
while reporting it, so nothing turned the drift into a failure.

WHAT IT CLASSIFIES, per persona

  operational   at least one owned skill loads live, and the persona's declared
                tools cover what its owned skills do.
  write-blocked owns a skill that produces files, has no Edit or Write tool. It
                can be routed to, spawned, and will fail at the last step.
  routed-dead   zero owned skills load live. The router can name it; nothing
                happens when it does.

WHAT IT DOES NOT DO

It does not check that a skill is any good, or that a persona would pick the
right one. `operational` is the floor, not a grade. The producer list is a
maintained set of skill names rather than an inference: a skill that writes files
without saying so reads as non-producing, so write-blocked is a floor too.

It reads the live tree, so its numbers describe THIS machine. On a different host
with a different ~/.claude, every count can differ, and that is the point.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Owned skills whose job is to produce a file. Curated, not inferred: each entry
# is here because the skill's own description says it writes, generates, or
# updates something on disk.
PRODUCERS = {
    "to-prd", "to-issues", "domain-model", "ubiquitous-language",
    "property-test-gen", "scaffold-exercises", "pre-ship-clean", "write-a-skill",
    "blog", "edit-article", "meeting-notes", "jira-task-draft",
    "azure-wiki-onepager", "shoval-voice-draft", "tdd", "code-simplifier",
}
WRITE_TOOLS = {"Edit", "Write", "*"}


def parse_registry(path: Path) -> dict[str, list[str]]:
    """Personas and their owned skills, straight out of the registry markdown."""
    personas: dict[str, list[str]] = {}
    cur = None
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^### (.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip()
            personas[cur] = []
        elif cur is not None:
            s = re.match(r"^- `([a-z0-9\-]+)`\s*$", ln.strip())
            if s:
                personas[cur].append(s.group(1))
    return {k: v for k, v in personas.items() if v}


def agent_tools(agents_dir: Path, persona: str) -> list[str] | None:
    """Declared tools for a persona's agent file, or None when there is no file."""
    slug = persona.lower().replace(" ", "-").replace("and-", "")
    for cand in (persona.lower().replace(" ", "-"), slug):
        f = agents_dir / f"{cand}.md"
        if f.exists():
            m = re.search(r"^tools:\s*(.+)$", f.read_text(encoding="utf-8",
                                                          errors="replace"), re.M)
            return [x.strip() for x in m.group(1).split(",")] if m else ["*"]
    return None


def audit(registry: Path, trees: list[Path], live: Path,
          agents_dir: Path) -> list[dict]:
    rows = []
    for persona, skills in parse_registry(registry).items():
        resolves = [s for s in skills if any((t / s).is_dir() for t in trees)]
        live_ok = [s for s in skills if (live / s).is_dir()]
        tools = agent_tools(agents_dir, persona)
        can_write = tools is None or bool(set(tools) & WRITE_TOOLS)
        blocked = sorted(set(skills) & PRODUCERS) if not can_write else []
        if not live_ok:
            verdict = "routed-dead"
        elif blocked:
            verdict = "write-blocked"
        else:
            verdict = "operational"
        rows.append({
            "persona": persona, "owned": len(skills), "resolves": len(resolves),
            "live": len(live_ok), "tools": tools, "can_write": can_write,
            "write_blocked_skills": blocked, "verdict": verdict,
            "unresolved": sorted(set(skills) - set(resolves)),
        })
    return rows


def corpus_gaps(registry: Path) -> list[str]:
    """Paths the registry tells personas to use that are not on this machine."""
    body = registry.read_text(encoding="utf-8", errors="replace")
    gaps = []
    for m in re.finditer(r"`(~[^`\s]+)`", body):
        p = Path(os.path.expanduser(m.group(1)))
        if not p.exists():
            gaps.append(m.group(1))
    return sorted(set(gaps))


def spawn_counts(ledger: Path) -> dict[str, int]:
    if not ledger.exists():
        return {}
    out: dict[str, int] = {}
    for ln in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        k = r.get("subagent_type") or r.get("agent") or r.get("persona")
        if k:
            out[k] = out.get(k, 0) + 1
    return out


def cmd_scan(a: argparse.Namespace) -> int:
    reg = Path(os.path.expanduser(a.registry))
    if not reg.exists():
        print(f"registry not found at {a.registry}")
        return 1
    trees = [Path(os.path.expanduser(t)) for t in a.tree]
    live = Path(os.path.expanduser(a.live))
    rows = audit(reg, trees, live, Path(os.path.expanduser(a.agents)))
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"{'persona':<30}{'own':>4}{'repo':>5}{'live':>5}  verdict")
    for r in rows:
        print(f"{r['persona']:<30}{r['owned']:>4}{r['resolves']:>5}{r['live']:>5}"
              f"  {r['verdict']}"
              + (f"  (cannot write: {', '.join(r['write_blocked_skills'])})"
                 if r["write_blocked_skills"] else ""))
    dead = [r for r in rows if r["verdict"] == "routed-dead"]
    wb = [r for r in rows if r["verdict"] == "write-blocked"]
    owned = sum(r["owned"] for r in rows)
    print(f"\n{len(rows)} personas, {owned} owned skills, "
          f"{sum(r['resolves'] for r in rows)} resolve in the repo, "
          f"{sum(r['live'] for r in rows)} load live")
    print(f"{len(dead)} routed-dead, {len(wb)} write-blocked, "
          f"{len(rows) - len(dead) - len(wb)} operational")
    spawns = spawn_counts(Path(a.spawns))
    print(f"spawns ever recorded: {sum(spawns.values())} across {len(spawns)} personas")
    gaps = corpus_gaps(reg)
    if gaps:
        print(f"paths the registry names that do not exist here ({len(gaps)}):")
        for g in gaps:
            print(f"  {g}")
    return 1 if (a.strict and (dead or wb)) else 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        reg = root / "registry.md"
        reg.write_text(
            "### Alpha Office\n\n- `writes-things`\n- `ghost-skill`\n\n"
            "### Beta Desk\n\n- `writes-things`\n\n"
            "### Gamma Lab\n\n- `reads-only`\n\n"
            "corpus lives at `~/definitely-not-a-real-path-xyz/sources.json`\n")
        repo, live = root / "repo", root / "live"
        for s in ("writes-things", "reads-only"):
            (repo / s).mkdir(parents=True)
        (live / "writes-things").mkdir(parents=True)
        (live / "reads-only").mkdir(parents=True)
        agents = root / "agents"
        agents.mkdir()
        (agents / "alpha-office.md").write_text("---\ntools: Read, Bash\n---\n")
        (agents / "beta-desk.md").write_text("---\ntools: Read, Bash, Write\n---\n")
        (agents / "gamma-lab.md").write_text("---\ntools: Read, Bash\n---\n")
        PRODUCERS.add("writes-things")
        try:
            rows = {r["persona"]: r for r in audit(reg, [repo], live, agents)}
            if rows["Alpha Office"]["verdict"] != "write-blocked":
                fails.append(f"Alpha -> {rows['Alpha Office']['verdict']}, want write-blocked")
            if rows["Beta Desk"]["verdict"] != "operational":
                fails.append(f"Beta -> {rows['Beta Desk']['verdict']}, want operational")
            if rows["Alpha Office"]["unresolved"] != ["ghost-skill"]:
                fails.append("a skill resolving nowhere was not reported unresolved")
            # A persona whose skills exist in the repo but not live is the exact
            # failure this tool was written for, so it gets its own case.
            (repo / "repo-only").mkdir()
            reg.write_text(reg.read_text() + "\n### Delta Wing\n\n- `repo-only`\n")
            rows = {r["persona"]: r for r in audit(reg, [repo], live, agents)}
            d = rows["Delta Wing"]
            if d["verdict"] != "routed-dead" or d["resolves"] != 1 or d["live"] != 0:
                fails.append(f"repo-only persona -> {d['verdict']} "
                             f"resolves={d['resolves']} live={d['live']}, "
                             "want routed-dead 1 0")
            if corpus_gaps(reg) != ["~/definitely-not-a-real-path-xyz/sources.json"]:
                fails.append("an absent registry-named path was not reported")
        finally:
            PRODUCERS.discard("writes-things")
    for f in fails:
        print(f"[FAIL] {f}")
    print("PASS persona_audit selftest" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="classify every routed persona")
    s.add_argument("--registry", default="~/.claude/rules/gastown-company-registry.md")
    s.add_argument("--tree", action="append",
                   default=["payload/dot-claude/skills", "payload/dot-agents/skills",
                            "payload/dot-codex/skills"])
    s.add_argument("--live", default="~/.claude/skills")
    s.add_argument("--agents", default="~/.claude/agents")
    s.add_argument("--spawns", default="state/agent-spawns.jsonl")
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true",
                   help="exit 1 if any persona is routed-dead or write-blocked")
    s.set_defaults(func=cmd_scan)
    t = sub.add_parser("selftest", help="prove the classifier on a planted registry")
    t.set_defaults(func=cmd_selftest)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
