#!/usr/bin/env python3
"""self-improve.py -- G1: the gastown self-improvement loop (score -> curate -> reflect -> report).

Read-only and ADVISORY: it writes a dated report for human approval and NEVER mutates config.
Substrate already on disk:
  - ~/.intent/intent.db          via the `intent` CLI (intents, evidence, evals)
  - ~/.claude/cache/a2a/audit.jsonl   Codex a2a usage
  - ~/.claude/hooks/prompt-router.sh  the router's skill routes (reachability)
  - ~/.claude/skills               skill inventory
Patterns: GEPA (reflective rewrite), Hermes (create-curate-evolve), Google Agent Quality Flywheel.
Run: python3 ~/.claude/bin/self-improve.py   (SELF_IMPROVE_NO_CODEX=1 to skip the Codex reflect step)
"""
import json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
OUT_DIR = HOME / ".claude" / "cache" / "self-improve"
INTENT = shutil.which("intent") or str(HOME / ".local" / "bin" / "intent")
A2A = str(HOME / ".claude" / "bin" / "a2a-codex-call.sh")
AUDIT = HOME / ".claude" / "cache" / "a2a" / "audit.jsonl"
SKILLS = HOME / ".claude" / "skills"

# Reachability + reflect-prompt logic lives in the tested intent-control-plane package
# (src/intent_control_plane/harness/self_improve.py), so it is regression-guarded, not
# duplicated untested glue. This file keeps the I/O and imports the pure functions.
#
# This file is payload (dot-claude/bin/self-improve.py) deployed to ~/.claude/bin/, but it
# is also runnable straight out of a claude-setup checkout at dot-claude/bin/self-improve.py,
# two levels below the repo root, matching tools/bus/backfill_session_telemetry.py and
# tools/intent/capture_turn.py. It used to insert $HOME/projects/intent-control-plane/src,
# a path that has never existed on this machine (there is no ~/projects at all), so the
# import below always raised ModuleNotFoundError with no indication of what was tried.
# Resolve repo-relatively instead, and fail loudly and specifically if that resolution is
# wrong, rather than falling through to a confusing import error two lines down.
_ICP_SRC = Path(__file__).resolve().parents[2] / "intent-control-plane" / "src"
if not _ICP_SRC.is_dir():
    raise SystemExit(
        f"self-improve.py: intent-control-plane/src not found at {_ICP_SRC} "
        f"(resolved as ../../intent-control-plane/src from {Path(__file__).resolve()}). "
        "This script must run from inside a claude-setup checkout that still has that "
        "layout; a deployed ~/.claude/bin/self-improve.py with no adjacent repo cannot "
        "resolve it and should not silently import nothing."
    )
sys.path.insert(0, str(_ICP_SRC))
from intent_control_plane.harness.router import routed_skill_names
from intent_control_plane.harness.self_improve import build_reflect_prompt, unreachable_skills


def jq(*args, timeout=25):
    try:
        r = subprocess.run([INTENT, *args], capture_output=True, text=True, timeout=timeout)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date = now[:10]
    rep = [f"# Gastown self-improvement report ({now})",
           "Advisory only. Review, then apply by hand. This loop never mutates config.", ""]

    # 1) SCORE
    eval_res = jq("eval", "smoke")
    intents = jq("list", "intents", "--limit", "30").get("items", [])
    evidence = jq("list", "evidence", "--limit", "100").get("items", [])
    ev_by = {}
    for e in evidence:
        ev_by.setdefault(e.get("intent_id"), []).append(e)
    scored = []
    for it in intents:
        iid = it.get("intent_id")
        proof = [p.get("type") for p in (it.get("proof_required") or []) if p.get("type")]
        has_pass = any(x.get("status") == "pass" for x in ev_by.get(iid, []))
        scored.append((iid, (it.get("goal") or "")[:70], proof, (not proof) or has_pass))
    total = len(scored)
    met = sum(1 for *_, m in scored if m)
    failing = [s for s in scored if not s[3]]
    eg = []
    try:
        for ln in (OUT_DIR / "eval-runs.jsonl").read_text().splitlines()[-40:]:
            eg.append(json.loads(ln))
    except Exception:
        pass
    # eval-runs.jsonl is a GLOBAL log: any repo's `git push` eval-gate hook writes to it, so a single
    # aggregate conflates one repo's failing promptfoo suite with the harness. Report per repo, honestly.
    by_repo = {}
    for e in eg:
        bucket = by_repo.setdefault(str(e.get("repo", "?")), [0, 0])
        bucket[0 if e.get("status") == "pass" else 1] += 1
    eg_line = "; ".join(f"{r} {p}/{p + f}" for r, (p, f) in sorted(by_repo.items())) or "no runs"
    rep += ["## Score",
            f"- eval smoke: {eval_res.get('status', '?')} "
            f"(passed={eval_res.get('passed', '?')} failed={eval_res.get('failed', '?')})",
            f"- eval-gate runs by repo (last {len(eg)}): {eg_line}",
            f"- intents with proof satisfied: {met}/{total}"]
    if failing:
        rep.append(f"- unsatisfied (proof required, no passing evidence): {len(failing)}")
        for iid, goal, proof, _ in failing[:10]:
            rep.append(f"    - {iid}  {goal}  proof={proof}")
    rep.append("")

    # 2) CURATE: skill reachability via the router (Hermes-style prune/wire signal)
    inv = sorted([d.name for d in SKILLS.iterdir() if (d / "SKILL.md").exists()]) if SKILLS.exists() else []
    try:
        unreachable = unreachable_skills(inv, routed_skill_names())
    except Exception:
        unreachable = []
    rep += ["## Curate (skills NOT reachable via the router = wire a route or prune)",
            f"- skills: {len(inv)} total, {len(inv) - len(unreachable)} routed, {len(unreachable)} unreachable"]
    if unreachable:
        rep.append("    " + ", ".join(unreachable[:50]))
    rep.append("")

    # usage
    calls = 0
    try:
        calls = sum(1 for _ in AUDIT.open())
    except Exception:
        pass
    rep += ["## Usage", f"- Codex a2a calls logged (all time): {calls}", ""]

    # 3) REFLECT: one GEPA-style proposal from Codex (read-only), on the top failure
    rep.append("## Reflect (GEPA-style proposal, Codex read-only)")
    if failing and os.access(A2A, os.X_OK) and not os.environ.get("SELF_IMPROVE_NO_CODEX"):
        f = failing[0]
        prompt = build_reflect_prompt(f[1], f[2])
        try:
            r = subprocess.run([A2A, prompt, "--sandbox", "read-only", "--effort", "low", "--timeout", "120"],
                               capture_output=True, text=True, timeout=140)
            txt = json.loads(r.stdout or "{}").get("response_text", "").strip()
            rep.append(txt or "(codex returned no proposal)")
        except Exception as e:
            rep.append(f"(reflect skipped: {type(e).__name__})")
    else:
        rep.append("(no failing signal, or Codex reflect disabled)")
    rep.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.md"
    out.write_text("\n".join(rep))
    print(f"self-improve report: {out}")
    print(f"score: proof-satisfied {met}/{total} | unreachable skills {len(unreachable)} | "
          f"eval {eval_res.get('status', '?')} | codex calls {calls}")


if __name__ == "__main__":
    main()
