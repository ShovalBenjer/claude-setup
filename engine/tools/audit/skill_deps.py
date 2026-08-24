#!/usr/bin/env python3
"""Decide whether a skill can run HERE, before deciding whether it is good.

WHY THIS EXISTS

The operator named the failure directly: do not come back with Linear, Notion
and Obsidian skills. All three are well written. All three are useless on this
machine, because none of the three products is installed, subscribed to, or
authenticated. A skill for a SaaS account you do not hold is not a weak skill,
it is a skill that cannot start, and no amount of star count changes that.

The uncomfortable half of the same check is that it does not only reject
outsiders. `az` is not on this machine. `dot-claude/skills` ships skills that
open with `az keyvault secret show` and `az webapp restart`, and the gastown
registry routes an entire Azure persona at them. Those fail the identical test
that rejects Notion. So does every skill that pipes through `jq`, which is also
absent. A filter that only ever points outward is a preference; this one is
allowed to point at us, which is the only reason to trust it.

WHAT IT CLASSIFIES

  runnable    every external requirement this skill names is present here.
  blocked     at least one named requirement is absent. The skill may be
              excellent. It cannot start.
  unbound     no external requirement detected. The skill is prose, method or
              checklist, and runs anywhere. DORA-shaped candidates land here,
              which is exactly why the operator used DORA as his example of the
              good kind.

WHAT IT DOES NOT DO

It does not judge quality, and it must not be read as doing so. `unbound` is not
praise, it only means nothing blocks a trial. It also does not detect a
requirement a skill never writes down: a skill whose SKILL.md says "use the API"
without naming a binary reads as unbound and is not. Detection is by named
invocation, so the count is a floor on blockage, never a ceiling.

A binary on PATH is not a binary that is authenticated, and `runnable` must not be
read as "verified to start". `gh` present with no login passes probe_binary and
fails at first call; the same is true of az, gcloud and docker. Probes are local
only: no network call, no auth attempt, nothing that could mutate a remote.
Absence here means absent on THIS host, which is the whole question being asked,
and presence here means installed, not ready.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# (requirement, kind, regex that means "this skill invokes it")
# Patterns match a real invocation, not a passing mention, so that a skill which
# merely discusses Azure is not counted as needing Azure.
REQUIREMENTS: list[tuple[str, str, str]] = [
    ("az", "binary", r"(?<![\w-])az +(?:login|account|keyvault|webapp|acr|devops|"
                     r"functionapp|cognitiveservices|storage|containerapp|tag|"
                     r"monitor|group|ad|resource|deployment|config)\b"),
    ("bun", "binary", r"(?<![\w-])bun +(?:run|install|add|x|test)\b"),
    ("jq", "binary", r"(?:\| *jq\b|(?<![\w-])jq +-)"),
    ("gh", "binary", r"(?<![\w-])gh +(?:api|pr|issue|repo|run|auth|workflow)\b"),
    ("uv", "binary", r"(?<![\w-])uv +(?:run|pip|sync|add|venv)\b"),
    ("docker", "binary", r"(?<![\w-])docker +(?:run|build|ps|compose|exec)\b"),
    ("ollama", "binary", r"(?<![\w-])ollama +(?:run|pull|list|serve)\b"),
    ("node", "binary", r"(?<![\w-])(?:node|npx) +[\w./-]"),
    ("pandoc", "binary", r"(?<![\w-])pandoc +[\w./-]"),
    ("ffmpeg", "binary", r"(?<![\w-])ffmpeg +-"),
    ("sqlite3", "binary", r"(?<![\w-])sqlite3 +[\w./-]"),
    ("psql", "binary", r"(?<![\w-])psql +-"),
    ("gcloud", "binary", r"(?<![\w-])gcloud +[a-z]+ +[a-z]"),
    ("pac", "binary", r"(?<![\w-])pac +(?:solution|auth|admin)\b"),
    ("azd", "binary", r"(?<![\w-])azd +(?:up|deploy|provision|env)\b"),
]

# Named third-party products. A skill that drives one of these needs the product
# itself, an account, or both. Detected by name because there is no binary to
# probe: the dependency is commercial, not executable.
PRODUCTS: list[tuple[str, str]] = [
    ("notion", r"(?i)\bnotion(?:\.so)?\b"),
    ("linear", r"(?i)\blinear\.app\b|\blinear (?:issue|ticket|workspace|api)\b"),
    ("obsidian", r"(?i)\bobsidian\b"),
    ("slack", r"(?i)\bslack (?:api|workspace|channel|token)\b"),
    ("jira", r"(?i)\batlassian\.net\b|\bjira (?:api|issue|ticket)\b"),
    ("trello", r"(?i)\btrello\b"),
    ("elevenlabs", r"(?i)\belevenlabs\b"),
    ("heygen", r"(?i)\bheygen\b"),
    ("apify", r"(?i)\bapify\b"),
    ("1password", r"(?i)\b1password\b|(?<![\w-])op +(?:read|item)\b"),
    ("spotify", r"(?i)\bspotify\b"),
    ("discord", r"(?i)\bdiscord (?:bot|api|webhook)\b"),
]

TEXT_SUFFIXES = {".md", ".sh", ".py", ".ts", ".js", ".json", ".yml", ".yaml", ".txt"}
MAX_BYTES = 400_000


def probe_binary(name: str) -> bool:
    return shutil.which(name) is not None


def probe_product(name: str, home: Path) -> bool:
    """Local evidence that a commercial product is actually usable here.

    Deliberately conservative: only a filesystem trace counts. No network, no
    token read. A false 'absent' costs a manual override; a false 'present'
    would put the exact recommendation back that the operator rejected.
    """
    traces = {
        "notion": ["~/.notion", "~/.config/Notion"],
        "linear": ["~/.linear", "~/.config/linear"],
        "obsidian": ["~/.config/obsidian", "~/Obsidian", "~/vaults"],
        "slack": ["~/.slack", "~/.config/Slack"],
        "trello": ["~/.trello"],
        "1password": ["~/.op", "~/.config/op"],
        "spotify": ["~/.config/spotify"],
        "discord": ["~/.config/discord"],
    }.get(name, [])
    return any(Path(os.path.expanduser(t)).exists() for t in traces)


def looks_like_wordlist(body: str) -> bool:
    """A dictionary is data, not an instruction, and must not read as a dependency.

    `voice-metrics` ships a 200k-line English lexicon. The first run of this
    scanner reported it as needing Notion and Obsidian, because those are both
    ordinary English words sitting in `en_words.txt`. The filter written to
    reject Notion skills had flagged a dictionary for containing the word
    notion, which is funny once and a false positive every time after.
    """
    lines = body.split("\n", 400)[:400]
    if len(lines) < 200:
        return False
    single = sum(1 for ln in lines if ln.strip() and " " not in ln.strip())
    return single / max(1, len([ln for ln in lines if ln.strip()])) > 0.9


def skill_text(skill_dir: Path) -> str:
    parts: list[str] = []
    total = 0
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if looks_like_wordlist(body):
            continue
        total += len(body)
        parts.append(body)
        if total > MAX_BYTES:
            break
    return "\n".join(parts)


def requirements_of(text: str) -> list[tuple[str, str, str]]:
    """Return (requirement, kind, the literal text that matched).

    The snippet is not decoration. A match means "this skill names an
    invocation", which is a proxy for "this skill needs it" and sometimes
    catches an illustrative example instead. Carrying the evidence is what lets
    a human downgrade a row instead of trusting the verdict.
    """
    found: list[tuple[str, str, str]] = []
    for name, kind, pat in REQUIREMENTS:
        m = re.search(pat, text)
        if m:
            found.append((name, kind, m.group(0).strip()[:60]))
    for name, pat in PRODUCTS:
        m = re.search(pat, text)
        if m:
            lo = max(0, m.start() - 30)
            found.append((name, "product", text[lo:m.end() + 30].replace("\n", " ")[:60]))
    return found


def classify(reqs: list[tuple[str, str, str]],
             home: Path) -> tuple[str, list[str], list[str], dict[str, str]]:
    present, absent, why = [], [], {}
    for name, kind, snip in reqs:
        ok = probe_binary(name) if kind == "binary" else probe_product(name, home)
        (present if ok else absent).append(name)
        why[name] = snip
    if not reqs:
        return "unbound", present, absent, why
    return ("blocked" if absent else "runnable"), present, absent, why


def scan_tree(tree: Path, home: Path) -> list[dict]:
    rows = []
    if not tree.is_dir():
        return rows
    for d in sorted(tree.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        reqs = requirements_of(skill_text(d))
        verdict, present, absent, why = classify(reqs, home)
        rows.append({"tree": str(tree), "skill": d.name, "verdict": verdict,
                     "present": sorted(set(present)), "absent": sorted(set(absent)),
                     "evidence": {k: why[k] for k in sorted(set(absent))}})
    return rows


def cmd_scan(a: argparse.Namespace) -> int:
    home = Path(os.path.expanduser("~"))
    rows: list[dict] = []
    for t in a.tree:
        rows.extend(scan_tree(Path(os.path.expanduser(t)), home))
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    counts = {"runnable": 0, "blocked": 0, "unbound": 0}
    for r in rows:
        counts[r["verdict"]] += 1
    for r in rows:
        if r["verdict"] == "blocked":
            print(f"  blocked  {r['skill']:<28} absent: {', '.join(r['absent'])}")
    print(f"\n{len(rows)} skills across {len(a.tree)} tree(s): "
          f"{counts['runnable']} runnable, {counts['blocked']} blocked, "
          f"{counts['unbound']} unbound")
    missing: dict[str, int] = {}
    for r in rows:
        for m in r["absent"]:
            missing[m] = missing.get(m, 0) + 1
    if missing:
        print("blocking requirement, by how many skills it stops:")
        for k, v in sorted(missing.items(), key=lambda kv: -kv[1]):
            print(f"  {k:<12} {v}")
    return 1 if a.strict and counts["blocked"] else 0


def cmd_counts(a: argparse.Namespace) -> int:
    """Emit every number the analysis doc quotes, so the doc cannot drift from the data.

    Commit 3aa56ce landed the sibling repo ledger with this same discipline, after
    its first draft disagreed with itself in three places.
    """
    home = Path(os.path.expanduser("~"))
    for t in a.tree:
        rows = scan_tree(Path(os.path.expanduser(t)), home)
        if not rows:
            print(f"{t}: not present on this host")
            continue
        c = {"runnable": 0, "blocked": 0, "unbound": 0}
        for r in rows:
            c[r["verdict"]] += 1
        print(f"{t}: {len(rows)} skills, {c['blocked']} blocked, "
              f"{c['unbound']} unbound, {c['runnable']} runnable")
    led = Path(a.ledger)
    if led.exists():
        rows = [json.loads(ln) for ln in led.read_text().splitlines() if ln.strip()]
        by: dict[str, int] = {}
        for r in rows:
            by[r["verdict"]] = by.get(r["verdict"], 0) + 1
        print(f"{a.ledger}: {len(rows)} decision rows, "
              + ", ".join(f"{v} {k}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))
        blocked = [r for r in rows if r.get("needs_absent")]
        print(f"  {len(blocked)} of {len(rows)} rejected on a dependency absent here")
    return 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Prove the three verdicts on planted skills, including a self-pointing one."""
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "skills"
        absent_bin = "definitely-not-a-real-binary-xyz"
        REQUIREMENTS.append((absent_bin, "binary", rf"(?<![\w-]){absent_bin} +run\b"))
        try:
            (root / "prose-only").mkdir(parents=True)
            (root / "prose-only" / "SKILL.md").write_text(
                "Compare throughput against an instability counter. No tooling.")
            (root / "needs-ghost").mkdir(parents=True)
            (root / "needs-ghost" / "SKILL.md").write_text(
                f"Run `{absent_bin} run --all` to collect.")
            (root / "needs-git").mkdir(parents=True)
            (root / "needs-git" / "SKILL.md").write_text("Use `gh api repos/x/y`.")
            rows = {r["skill"]: r for r in scan_tree(root, Path(td))}
            if rows["prose-only"]["verdict"] != "unbound":
                fails.append(f"prose-only -> {rows['prose-only']['verdict']}, want unbound")
            if rows["needs-ghost"]["verdict"] != "blocked":
                fails.append(f"needs-ghost -> {rows['needs-ghost']['verdict']}, want blocked")
            if absent_bin not in rows["needs-ghost"]["absent"]:
                fails.append("needs-ghost did not name the absent binary")
            want = "runnable" if shutil.which("gh") else "blocked"
            if rows["needs-git"]["verdict"] != want:
                fails.append(f"needs-git -> {rows['needs-git']['verdict']}, want {want}")
            mention = "This skill talks about Azure and az generally."
            if requirements_of(mention):
                fails.append("a bare mention counted as an invocation")
            # --strict is the only path proposed for a gate domain (TODO SKILLDEP-03),
            # so it is the last one that may go unexercised. Exit code, not output.
            quiet = contextlib.redirect_stdout(io.StringIO())
            strict = argparse.Namespace(tree=[str(root)], json=False, strict=True)
            with quiet:
                rc_strict = cmd_scan(strict)
            if rc_strict != 1:
                fails.append("--strict exited 0 with a blocked skill present")
            lax = argparse.Namespace(tree=[str(root)], json=False, strict=False)
            with contextlib.redirect_stdout(io.StringIO()):
                rc_lax = cmd_scan(lax)
            if rc_lax != 0:
                fails.append("a blocked skill failed the run without --strict")
            clean = Path(td) / "clean"
            (clean / "prose-only").mkdir(parents=True)
            (clean / "prose-only" / "SKILL.md").write_text("A method. No tooling.")
            ok = argparse.Namespace(tree=[str(clean)], json=False, strict=True)
            with contextlib.redirect_stdout(io.StringIO()):
                rc_ok = cmd_scan(ok)
            if rc_ok != 0:
                fails.append("--strict exited nonzero with nothing blocked")
            wordlist = "\n".join(["notion", "obsidian"] + [f"word{i}" for i in range(400)])
            if requirements_of("" if looks_like_wordlist(wordlist) else wordlist):
                fails.append("a dictionary wordlist counted as a product dependency")
            if not rows["needs-ghost"]["evidence"].get(absent_bin):
                fails.append("blocked row carried no evidence snippet")
        finally:
            REQUIREMENTS.pop()
    for f in fails:
        print(f"[FAIL] {f}")
    print("PASS skill_deps selftest" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="classify skills by whether they can run here")
    s.add_argument("--tree", action="append", default=[],
                   help="a directory of skill directories; repeatable")
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true", help="exit 1 if any skill is blocked")
    s.set_defaults(func=cmd_scan)
    c = sub.add_parser("counts", help="emit the numbers the analysis doc quotes")
    c.add_argument("--tree", action="append",
                   default=["payload/dot-claude/skills", "payload/dot-agents/skills",
                            "~/.claude/skills"])
    c.add_argument("--ledger", default="state/external-skills.jsonl")
    c.set_defaults(func=cmd_counts)
    t = sub.add_parser("selftest", help="prove the classifier on planted skills")
    t.set_defaults(func=cmd_selftest)
    a = ap.parse_args()
    if a.cmd == "scan" and not a.tree:
        a.tree = ["payload/dot-claude/skills"]
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
