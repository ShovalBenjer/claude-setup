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
  refute.py run --allow-broken        # named escape hatch, see below
  refute.py add --id C-042 --claim "..." --verify "..." --shell pwsh
  refute.py list
  refute.py selftest                  # prove this file's own verdicts can fail

Exit code, and why it counts more than refutations
--------------------------------------------------
Exit is the number of claims you may NOT assert: REFUTED plus BROKEN, capped at
125. A verifier that could not run leaves its claim UNKNOWN, and unknown must not
be green, or the cheapest way to make this tool quiet is to break its commands.
Two real exit-0-while-checking-nothing defects in this very file were found on
2026-07-25 and are now regression-checked by `selftest`:

  - `--only` is a substring match. A caller passing "C-019,C-020" matched nothing
    and got "no claims to check" with exit 0 against a 20-claim ledger. A filter
    that matched nothing now exits 2, separately from an empty ledger, which is a
    fresh install and stays 0.
  - BROKEN was printed as "not a pass" and then excluded from the exit code, so a
    timed-out or unlaunchable verifier read as success to anything binding on it.

`--allow-broken` is the deliberate hatch for a caller that genuinely wants only
refutations (bisecting one claim on a machine missing an unrelated tool). It is a
flag someone has to type, which is the point: the quiet path is not the default.
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
    total = len(claims)
    if a.only:
        q = a.only.lower()
        claims = [
            c for c in claims
            if q in str(c.get("id", "")).lower()
            or q in str(c.get("claim", "")).lower()
            or q in str(c.get("tag", "")).lower()
        ]
    # An empty ledger and a filter that matched nothing are different facts and
    # used to print the same sentence and exit 0. That is the defect this whole
    # tool exists to catch: examining zero things and reporting success. A caller
    # who asked for specific claims and silently got none has been told its
    # claims held when none were checked, so a missed filter now fails.
    if not claims and total:
        print("--only {!r} matched none of the {} claims in {}. Nothing was checked."
              .format(a.only, total, CLAIMS), file=sys.stderr)
        print("--only is a SUBSTRING match on id, claim text, or tag; it is not a "
              "list. Try one id, or a tag.", file=sys.stderr)
        return 2
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
            print("broken verifiers are NOT passes. The claim stays unknown, and "
                  "unknown counts toward the exit code.")
            if getattr(a, "allow_broken", False):
                print("--allow-broken: not counting them, as asked.")

    # Refuted and broken both mean "you cannot assert this claim". Counting only
    # refutations made a verifier that could not launch indistinguishable from one
    # that passed, which rewards breaking the command over fixing the claim.
    countable = refuted if getattr(a, "allow_broken", False) else refuted + broken
    return min(countable, 125)


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


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Check this file against planted ledgers, where the right answer is known.

    A refutation engine whose own verdicts nobody checks is the thing it exists to
    reject. Every case below plants a ledger, runs cmd_run against it, and asserts
    the exit code, because the exit code is the only part a hook or CI job reads.

    The real ledger is never touched: CLAIMS, RESULTS and LESSONS are repointed at
    a temp directory and their original paths are asserted unchanged at the end. A
    selftest that appended to state/refutations.jsonl would be manufacturing the
    evidence the rest of the system trusts.
    """
    global CLAIMS, RESULTS, LESSONS
    import io
    import shutil
    import tempfile
    import traceback
    from contextlib import redirect_stdout, redirect_stderr

    # Deliberately not 0, 1 or 2: a crash must not satisfy any check that asserts a
    # real exit code.
    CRASH_RC = -99
    real = (CLAIMS, RESULTS, LESSONS)
    real_sizes = [p.stat().st_size if p.exists() else -1 for p in real]
    tmp = Path(tempfile.mkdtemp(prefix="refute-selftest-"))
    failures: list[str] = []

    # A trivial always-pass / always-fail command in whichever shell is present.
    gitbash = Path(r"C:\Program Files\Git\bin\bash.exe")
    sh = "bash" if gitbash.exists() or _which("bash") else "pwsh"

    def check(what: str, ok: bool, detail: str = "") -> None:
        print(("[ok]   " if ok else "[FAIL] ") + what + (f"  <- {detail}" if not ok and detail else ""))
        if not ok:
            failures.append(what)

    def plant(*claims: dict) -> None:
        """Point the module at a fresh ledger holding exactly these claims."""
        global CLAIMS, RESULTS, LESSONS
        d = Path(tempfile.mkdtemp(dir=tmp))
        CLAIMS, RESULTS, LESSONS = d / "claims.jsonl", d / "res.jsonl", d / "les.jsonl"
        CLAIMS.write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in claims),
            encoding="utf-8")

    def run(only: str | None = None, allow_broken: bool = False) -> tuple[int, str]:
        """Run cmd_run against the planted ledger, turning a crash into a verdict.

        An escaping exception used to take this whole selftest down: the case that
        raised got no verdict, every case after it never ran, and the process still
        exited nonzero. Under tools/audit/mutate.py that reads as "caught" with no
        failing check named, which is indistinguishable from being caught for the
        intended reason, and it hides however many later checks were never reached.
        So a raise becomes CRASH_RC plus the traceback as output: the check that
        asserted an exit code fails and says why, and the rest still run.
        """
        buf, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                rc = cmd_run(argparse.Namespace(only=only, json=False, record=False,
                                                allow_broken=allow_broken))
        except BaseException:                # noqa: BLE001 - a crash is a verdict here
            return CRASH_RC, (buf.getvalue() + err.getvalue()
                              + "\nRAISED: " + traceback.format_exc())
        return rc, buf.getvalue() + err.getvalue()

    def claim(cid: str, cmd: str, expect: str = "pass", tag: str = "t") -> dict:
        return {"id": cid, "claim": cid + " body", "verify": cmd, "shell": sh,
                "expect": expect, "tag": tag}

    ok_cmd = "exit 0"
    bad_cmd = "exit 1"

    try:
        # An empty ledger is a fresh install, not a failure. This is the ONLY case
        # where checking nothing is allowed to exit 0, so it is pinned explicitly.
        plant()
        rc, out = run()
        check("an empty ledger exits 0 and says what to seed",
              rc == 0 and "seed state/claims-verify.jsonl" in out, f"rc={rc} out={out!r}")

        # The regression that started this: a filter matching nothing against a
        # populated ledger used to print the empty-ledger sentence and exit 0.
        plant(claim("C-1", ok_cmd), claim("C-2", ok_cmd))
        rc, out = run(only="C-1,C-2")
        check("a filter that matched nothing exits nonzero",
              rc != 0, f"rc={rc}: a caller asking for specific claims and silently "
                       f"getting none was told its claims held")
        check("the matched-nothing message says how many claims were skipped and why",
              "matched none of the 2 claims" in out and "SUBSTRING" in out, out.strip()[:200])
        check("matched-nothing is NOT reported as an empty ledger",
              "seed state/claims-verify.jsonl" not in out,
              "the two conditions used to print the same sentence")

        # And the filter must still work, or the fix above would be a filter that
        # never matches anything.
        rc, out = run(only="C-1")
        check("a filter that matches one claim checks exactly that one",
              rc == 0 and "1 claims:" in out and "C-2" not in out, out.strip()[:200])

        # A refuted claim must be counted, and counted once.
        plant(claim("C-1", ok_cmd), claim("C-2", bad_cmd), claim("C-3", bad_cmd))
        rc, out = run()
        check("the exit code is the number of claims that cannot be asserted",
              rc == 2 and "1 held, 2 REFUTED" in out, f"rc={rc} out={out.strip()[:200]!r}")

        # expect=fail is for absence claims, where the natural command searches for
        # the thing that must not be there. Inverting it must invert the verdict.
        plant(claim("C-1", bad_cmd, expect="fail"))
        rc, out = run()
        check("expect=fail treats a nonzero command as the claim HOLDING",
              rc == 0 and "1 held" in out, f"rc={rc} out={out.strip()[:200]!r}")
        plant(claim("C-1", ok_cmd, expect="fail"))
        rc, out = run()
        check("expect=fail treats a zero command as REFUTED",
              rc == 1 and "1 REFUTED" in out, f"rc={rc} out={out.strip()[:200]!r}")

        # The second hole: a verifier that could not run used to be printed as
        # "not a pass" and then left out of the exit code, so breaking a command
        # was the cheapest way to silence this tool.
        plant({"id": "C-1", "claim": "no verifier at all", "tag": "t"})
        rc, out = run()
        check("a claim with no verify command is BROKEN, not held",
              "0 held" in out and "1 broken" in out, out.strip()[:200])
        check("a broken verifier makes the run exit nonzero",
              rc == 1, f"rc={rc}: an unrunnable command read as success")
        rc, out = run(allow_broken=True)
        check("--allow-broken is a real hatch and restores exit 0",
              rc == 0 and "not counting them, as asked" in out,
              f"rc={rc} out={out.strip()[:200]!r}")

        # An unknown shell is the other way a verifier fails to launch.
        plant({"id": "C-1", "claim": "bad shell", "verify": "exit 0", "shell": "fish"})
        rc, out = run()
        check("an unknown shell is BROKEN rather than silently skipped",
              rc == 1 and "unknown shell" in out, f"rc={rc} out={out.strip()[:200]!r}")

        # A timeout must not read as a pass either. 1s ceiling against a sleep.
        slow = "Start-Sleep -Seconds 5" if sh == "pwsh" else "sleep 5"
        plant({"id": "C-1", "claim": "slow verifier", "verify": slow,
               "shell": sh, "timeout": 1})
        rc, out = run()
        check("a verifier that times out is BROKEN and counted",
              rc == 1 and "timed out" in out, f"rc={rc} out={out.strip()[:200]!r}")

        # An unparseable ledger line must be skipped loudly, not crash the run and
        # not take the rest of the ledger with it.
        plant(claim("C-1", ok_cmd))
        with CLAIMS.open("a", encoding="utf-8") as fh:
            fh.write("{not json\n")
        rc, out = run()
        check("a torn ledger line is skipped and named, and the rest still runs",
              rc == 0 and "1 held" in out and "unparseable" in out, out.strip()[:200])

        # An unreadable ledger is a real failure mode (a directory where a file was
        # expected, a permissions change) and it must produce an attributable
        # verdict rather than an escaping traceback. Without this, one crash ends
        # the selftest early and every check below it silently goes unrun, while
        # the nonzero exit still looks like a caught mutation.
        plant(claim("C-1", ok_cmd))
        CLAIMS = Path(tempfile.mkdtemp(dir=tmp))          # a directory, not a file
        rc, out = run()
        check("an unreadable ledger is a reported failure, not an escaping traceback",
              rc == CRASH_RC and "RAISED" in out, f"rc={rc} out={out.strip()[-200:]!r}")
        check("checks after a crash still run",
              True, "reaching this line is the assertion")

    finally:
        CLAIMS, RESULTS, LESSONS = real
        shutil.rmtree(tmp, ignore_errors=True)

    now_sizes = [p.stat().st_size if p.exists() else -1 for p in real]
    check("the real ledger and results file were not written by this selftest",
          now_sizes == real_sizes, f"{real_sizes} -> {now_sizes}")

    print()
    if failures:
        print(f"FAILED {len(failures)} check(s):")
        for f in failures:
            print("  - " + f)
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="refute.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--only", help="substring filter on id, claim, or tag")
    r.add_argument("--json", action="store_true")
    r.add_argument("--record", action="store_true", help="log refutations to lessons.jsonl")
    r.add_argument("--allow-broken", action="store_true",
                   help="do not count verifiers that could not run toward the exit "
                        "code. Named hatch; the default is that unknown is not green")
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

    st = sub.add_parser("selftest", help="prove this file's own verdicts can fail")
    st.set_defaults(func=cmd_selftest)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
