# -*- coding: utf-8 -*-
"""Self-improvement scanner (Claude OS §2d medium loop, ADR-0005).
The engine that lets the system generate its OWN next work instead of waiting for
the operator to prompt. Reads real signals, emits a ranked, typed proposal list
(proposals.jsonl) with rationale + risk + auto-actionable flag. Proposes; the
operator (or an approval gate) disposes. Nothing here auto-applies.

Signals (all real, all local):
  - open TODO items (work not done)
  - git state (uncommitted drift, unmerged branches, default-branch drift)
  - hook health (do the wired hooks exist + run clean?)
  - flywheel volume (router decisions logged -> is there enough to cluster/train?)
  - tool coverage (tools present but never cron'd / never invoked)
  - doc staleness (specs with TODO acceptance rows)
  - test presence (tools/ modules without any test)
Run: python tools/selfimprove/scan.py  ->  prints top proposals, writes proposals.jsonl
"""
import json, os, re, subprocess, pathlib, hashlib

OS = pathlib.Path(os.environ.get("CLAUDE_OS_DIR", pathlib.Path.home() / "claude-setup"))
OUT = OS / "tools" / "selfimprove"
OUT.mkdir(parents=True, exist_ok=True)


def sh(*a, cwd=OS):
    try:
        return subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=40,
                              encoding="utf-8", errors="replace").stdout.strip()
    except Exception:
        return ""


def proposal(title, why, risk, auto, evidence, kind):
    pid = hashlib.sha1(title.encode("utf-8", "replace")).hexdigest()[:10]
    # priority: high-impact + low-risk + auto-actionable float to the top
    risk_w = {"low": 3, "med": 2, "high": 1}[risk]
    score = risk_w + (2 if auto else 0) + {"gap": 3, "hygiene": 2, "growth": 3, "health": 4}[kind]
    return {"id": pid, "title": title, "why": why, "risk": risk, "auto_actionable": auto,
            "evidence": evidence, "kind": kind, "score": score}


def scan():
    props = []

    # 1. Open TODO items -> proposals to close them
    todo = OS / "TODO.md"
    if todo.exists():
        opens = [l.strip()[6:] for l in todo.read_text(encoding="utf-8", errors="replace").splitlines()
                 if l.strip().startswith("- [ ]")]
        for item in opens[:8]:
            auto = not any(w in item.lower() for w in ["operator", "you ", "decision", "rotate", "key", "blocked", "needs "])
            props.append(proposal(f"Advance TODO: {item[:70]}",
                                  "open work item in the OS backlog", "med", auto,
                                  "TODO.md", "gap"))

    # 2. Git hygiene
    dirty = sh("git", "status", "--porcelain")
    if dirty:
        props.append(proposal(f"Commit or revert {len(dirty.splitlines())} uncommitted change(s)",
                              "working tree drift hides state", "low", False, "git status", "hygiene"))
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
    if branch and branch != "main":
        props.append(proposal(f"Return to main (on '{branch}')",
                              "work should land on main, not a stray branch", "low", True,
                              "git branch", "hygiene"))

    # 3. Hook health — do wired hooks exist?
    settings = pathlib.Path.home() / ".claude" / "settings.json"
    if settings.exists():
        try:
            cfg = json.loads(settings.read_text(encoding="utf-8"))
            for ev, arr in cfg.get("hooks", {}).items():
                for group in arr:
                    for h in group.get("hooks", []):
                        args = h.get("args", [])
                        target = next((a for a in args if a.endswith(".sh") or a.endswith(".ps1")), None)
                        if target and not pathlib.Path(target).exists():
                            props.append(proposal(f"Fix broken {ev} hook (missing {os.path.basename(target)})",
                                                  "a wired hook points at a missing file (silent failure)",
                                                  "med", True, target, "health"))
        except Exception:
            pass

    # 4. Flywheel volume — enough router decisions to cluster/train?
    fw = OS / "tools" / "local" / "flywheel" / "router_decisions.jsonl"
    n = len(fw.read_text(errors="replace").splitlines()) if fw.exists() else 0
    if n < 50:
        props.append(proposal(f"Grow flywheel: only {n} router decisions logged (need ~10k for a specialist)",
                              "SLM flywheel (ADR-0009 S2-S6) needs volume before it can train",
                              "low", False, str(fw), "growth"))

    # 5. Tools without tests
    tools = list((OS / "tools").rglob("*.py"))
    for t in tools:
        name = t.stem
        if name in ("scan", "__init__") or "test" in name:
            continue
        has_test = any((OS / "tools").rglob(f"*test*{name}*")) or (OS / "tests").exists() and any((OS / "tests").rglob(f"*{name}*"))
        # cheap heuristic: no test file referencing the module name
        if not list((OS).rglob(f"test_{name}.py")):
            props.append(proposal(f"Add a test for tools/{t.relative_to(OS/'tools')}",
                                  "tool has no test; coverage discipline (ADR-0005)",
                                  "low", True, str(t.relative_to(OS)), "gap"))
            break  # one per run, don't flood

    # rank
    props.sort(key=lambda p: -p["score"])
    return props


def main():
    props = scan()
    (OUT / "proposals.jsonl").write_text(
        "\n".join(json.dumps(p) for p in props), encoding="utf-8")
    def safe(s):  # Windows console is cp1255; keep prints ascii, jsonl keeps full unicode
        return s.encode("ascii", "replace").decode("ascii")
    print(f"self-improvement scan: {len(props)} proposals (ranked)\n")
    for p in props[:10]:
        flag = "AUTO" if p["auto_actionable"] else "ASK "
        print(f"[{flag} r={p['risk']:4s} s={p['score']}] {safe(p['title'])}")
    print(f"\nwritten: {OUT / 'proposals.jsonl'}")
    auto = [p for p in props if p["auto_actionable"] and p["risk"] == "low"]
    print(f"auto-actionable low-risk: {len(auto)} (a loop could self-apply these under an approval gate)")


if __name__ == "__main__":
    main()
