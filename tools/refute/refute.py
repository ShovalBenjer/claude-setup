#!/usr/bin/env python3
"""Refutation engine: every claim about this setup carries a command that can kill it.

Why this exists
---------------
2026-07-20: Levent Alpoge used Fable 5 to find a counterexample to the Jacobian
Conjecture, open since Keller posed it in 1939. The counterexample is 216
characters. Mathematicians verified it independently within hours.

The transferable part is NOT that a model read a lot of mathematics. It is that
"is this a counterexample" is CHEAP TO CHECK: substitute, expand, compare. Where
a predicate is mechanically checkable you can point enormous cheap compute at
generate-and-check, and the proposer is allowed to be wrong almost every time.
Where there is no cheap checker, more compute produces more plausible prose.

This repo is full of claims with no checker. Personas "deployed", a bus "wired",
skills "installed", docs "current", a hook "active". Each is exactly as checkable
as a Jacobian counterexample and none of them was being checked. Concretely, on
2026-07-25 the PreToolUse pre_push_gate hook was failing on every single Bash
call and had been reporting nothing.

The rule this enforces
----------------------
A claim without a verifier is not a claim, it is a wish. Adding a row to
state/claims-verify.jsonl REQUIRES a command that would fail if the claim were
false. If you cannot write that command, you do not have a claim yet, and saying
so is the honest move (calibrated-claims: ASSUMED is respected, hiding it is not).

Refutation is the product. A run that refutes nothing is a run that found
nothing; it does not mean everything is fine, it means the claim set is too weak.
Prefer verifiers that are specific enough to fail.

Usage
-----
  refute.py run                       # check every claim, print the verdict table
  refute.py run --only bus            # substring filter on id/claim/tag
  refute.py run --json                # machine output for CI or the bus
  refute.py run --record              # append refutations to state/lessons.jsonl
  refute.py add --id C-042 --claim "..." --verify "..." --shell pwsh
  refute.py list

Exit code is the number of REFUTED claims (capped at 125), so CI can bind on it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIMS = ROOT / "state" / "claims-verify.jsonl"
RESULTS = ROOT / "state" / "refutations.jsonl"
LESSONS = ROOT / "state" / "lessons.jsonl"

DEFAULT_TIMEOUT = 25

HELD = "HELD"
REFUTED = "REFUTED"
BROKEN = "BROKEN"  # the verifier itself could not run; the claim stays unknown


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_claims() -> list[dict]:
    if not CLAIMS.exists():
        return []
    out = []
    for n, line in enumerate(CLAIMS.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"claims-verify.jsonl:{n}: unparseable, skipped ({e})", file=sys.stderr)
            continue
        out.append(rec)
    return out


def run_verifier(rec: dict) -> tuple[str, int, str]:
    """Execute one verifier. Returns (verdict, returncode, captured output).

    expect="pass" (default): exit 0 means the claim HOLDS.
    expect="fail":           nonzero means the claim HOLDS. Use for absence
                             claims where the natural command searches for the
                             thing that must NOT be there.
    """
    cmd = rec.get("verify", "")
    if not cmd:
        return BROKEN, -1, "no verify command on this claim"

    shell = (rec.get("shell") or "pwsh").lower()
    timeout = int(rec.get("timeout") or DEFAULT_TIMEOUT)

    if shell in ("pwsh", "powershell", "ps"):
        exe = "pwsh" if _which("pwsh") else "powershell"
        argv = [exe, "-NoProfile", "-NonInteractive", "-Command", cmd]
    elif shell == "bash":
        gitbash = Path(r"C:\Program Files\Git\bin\bash.exe")
        exe = str(gitbash) if gitbash.exists() else "bash"
        argv = [exe, "-lc", cmd]
    else:
        return BROKEN, -1, f"unknown shell {shell!r}"

    try:
        p = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout,
            cwd=str(ROOT), errors="replace",
        )
    except subprocess.TimeoutExpired:
        return BROKEN, -1, f"verifier timed out after {timeout}s"
    except OSError as e:
        return BROKEN, -1, f"could not launch {shell}: {e}"

    out = ((p.stdout or "") + (p.stderr or "")).strip()
    expect = (rec.get("expect") or "pass").lower()
    ok = (p.returncode == 0) if expect == "pass" else (p.returncode != 0)
    return (HELD if ok else REFUTED), p.returncode, out


def _which(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def cmd_run(a: argparse.Namespace) -> int:
    claims = load_claims()
    if a.only:
        q = a.only.lower()
        claims = [
            c for c in claims
            if q in str(c.get("id", "")).lower()
            or q in str(c.get("claim", "")).lower()
            or q in str(c.get("tag", "")).lower()
        ]
    if not claims:
        print("no claims to check. seed state/claims-verify.jsonl first.", file=sys.stderr)
        return 0

    results, refuted, broken = [], 0, 0
    for rec in claims:
        verdict, rc, out = run_verifier(rec)
        if verdict == REFUTED:
            refuted += 1
        elif verdict == BROKEN:
            broken += 1
        results.append({
            "ts": now_iso(),
            "id": rec.get("id", "?"),
            "claim": rec.get("claim", ""),
            "tag": rec.get("tag", ""),
            "lane": rec.get("lane", ""),
            "source": rec.get("source", ""),
            "verdict": verdict,
            "rc": rc,
            "evidence": out[:1200],
        })

    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_table(results)

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    if a.record and refuted:
        with LESSONS.open("a", encoding="utf-8") as fh:
            for r in results:
                if r["verdict"] != REFUTED:
                    continue
                fh.write(json.dumps({
                    "ts": r["ts"],
                    "kind": "calibration-loss",
                    "source": "refute.py",
                    "claim_id": r["id"],
                    "lesson": f"Claim refuted mechanically: {r['claim']}",
                    "evidence": r["evidence"][:400],
                }, ensure_ascii=False) + "\n")

    if not a.json:
        held = len(results) - refuted - broken
        print()
        print(f"{len(results)} claims: {held} held, {refuted} REFUTED, {broken} broken verifier")
        print(f"appended to {RESULTS}")
        if broken:
            print("broken verifiers are NOT passes. The claim stays unknown.")

    return min(refuted, 125)


def _print_table(results: list[dict]) -> None:
    width = max((len(r["id"]) for r in results), default=4)
    for r in results:
        mark = {HELD: "  held", REFUTED: "REFUTED", BROKEN: " broken"}[r["verdict"]]
        print(f"{mark}  {r['id']:<{width}}  {r['claim']}")
        if r["verdict"] != HELD:
            for ln in (r["evidence"] or "(no output)").splitlines()[:6]:
                print(f"          | {ln}")
            if r["source"]:
                print(f"          | source: {r['source']}")


def cmd_add(a: argparse.Namespace) -> int:
    rec = {
        "id": a.id,
        "claim": a.claim,
        "verify": a.verify,
        "shell": a.shell,
        "expect": a.expect,
        "tag": a.tag or "",
        "lane": a.lane or "",
        "source": a.source or "",
        "added": now_iso(),
    }
    CLAIMS.parent.mkdir(parents=True, exist_ok=True)
    with CLAIMS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    verdict, rc, out = run_verifier(rec)
    print(f"added {a.id}  -> {verdict} (rc={rc})")
    if out:
        print(out[:600])
    return 0


def cmd_list(_a: argparse.Namespace) -> int:
    for c in load_claims():
        print(f"{c.get('id','?'):<10} [{c.get('tag','')}] {c.get('claim','')}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="refute.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--only", help="substring filter on id, claim, or tag")
    r.add_argument("--json", action="store_true")
    r.add_argument("--record", action="store_true", help="log refutations to lessons.jsonl")
    r.set_defaults(func=cmd_run)

    ad = sub.add_parser("add")
    ad.add_argument("--id", required=True)
    ad.add_argument("--claim", required=True)
    ad.add_argument("--verify", required=True)
    ad.add_argument("--shell", default="pwsh", choices=["pwsh", "bash"])
    ad.add_argument("--expect", default="pass", choices=["pass", "fail"])
    ad.add_argument("--tag")
    ad.add_argument("--lane")
    ad.add_argument("--source")
    ad.set_defaults(func=cmd_add)

    ls = sub.add_parser("list")
    ls.set_defaults(func=cmd_list)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
