# -*- coding: utf-8 -*-
"""Build the daily digest (Claude OS L4, PRD #6). Aggregates real OS state into a
<200-char push line + a fuller digest.md. Deterministic — no model call. The cron
fires a prompt that runs this, reads push.txt, and sends it via PushNotification.

Sources (all real, all local): TODO.md, branch health json, repo graph db, git state.
"""
import json, os, re, subprocess, sys, pathlib

OS = pathlib.Path(os.environ.get("CLAUDE_OS_DIR", pathlib.Path.home() / "claude-setup"))
OUT = OS / "tools" / "digest" / "out"
OUT.mkdir(parents=True, exist_ok=True)


def sh(*a):
    try:
        return subprocess.run(a, cwd=OS, capture_output=True, text=True, timeout=30,
                              encoding="utf-8", errors="replace").stdout.strip()
    except Exception:
        return ""


def todo_counts():
    p = OS / "TODO.md"
    if not p.exists():
        return 0, 0, None
    t = p.read_text(encoding="utf-8", errors="replace")
    done = len(re.findall(r"^\s*- \[x\]", t, re.M))
    openn = len(re.findall(r"^\s*- \[ \]", t, re.M))
    nxt = re.search(r"^\s*- \[ \] (.+)$", t, re.M)
    return done, openn, (nxt.group(1) if nxt else None)


def branch_health():
    p = OS / "tools" / "health" / "out" / "branch_health.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    merged = drift = 0
    for repo in (d if isinstance(d, list) else d.get("repos", [])):
        for b in repo.get("branches", []):
            if b.get("classification") == "MERGED":
                merged += 1
        if repo.get("default") == "master":
            drift += 1
    return {"merged_deletable": merged, "drift": drift}


def git_state():
    dirty = sh("git", "status", "--porcelain")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
    return {"branch": branch, "dirty": bool(dirty), "changes": len(dirty.splitlines())}


def main():
    done, openn, nxt = todo_counts()
    bh = branch_health()
    gs = git_state()

    push = f"Claude OS: {done} done / {openn} open."
    if nxt:
        push += f" Next: {nxt[:70]}."
    if bh and bh["merged_deletable"]:
        push += f" {bh['merged_deletable']} merged branches deletable."
    push = push[:190]

    md = [f"# Claude OS Daily Digest", "",
          f"- TODO: {done} done, {openn} open" + (f"; next: {nxt}" if nxt else ""),
          f"- claude-setup repo: {gs['branch']}, " + ("dirty (%d)" % gs["changes"] if gs["dirty"] else "clean")]
    if bh:
        md.append(f"- Branch health: {bh['merged_deletable']} merged-deletable, {bh['drift']} default-branch drift")

    # AUTO-16: open lessons surface in EVERY digest until their enforcement lands
    lessons = OS / "state" / "lessons.jsonl"
    if lessons.exists():
        rows = [json.loads(l) for l in lessons.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        open_rows = [r for r in rows if r.get("status") != "closed"]
        if open_rows:
            md.append("")
            md.append(f"- OPEN LESSONS ({len(open_rows)}) — unenforced until closed:")
            for r in open_rows:
                md.append(f"  - {r['id']}: {r['lesson'][:90]} -> {r['enforcement'][:70]}")
            push += f" {len(open_rows)} open lessons."

    md.append("")
    md.append("Pending operator decisions: model default, key rotation, PR repo list, WhatsApp cadence, OAuth token.")

    (OUT / "push.txt").write_text(push, encoding="utf-8")
    (OUT / "digest.md").write_text("\n".join(md), encoding="utf-8")
    print(push)


if __name__ == "__main__":
    main()
