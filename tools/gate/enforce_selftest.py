#!/usr/bin/env python3
"""Prove the LIVE deployed Stop hook actually refuses a done-claim.

WHY THIS FILE EXISTS, GIVEN THAT gate.py ALREADY HAS A SELFTEST

gate.py selftest proves the gate computes correct verdicts. flow.py and panel.py
prove their detectors fire. All three are unit-level: they prove the instruments
work when something calls them.

Nothing proved the thing actually relied on, which is a different claim and an
integration one: that the hook registered in the live ~/.claude/settings.json,
handed a real Stop payload, refuses a completion claim on a tree that has not
been gated. Every part of that sentence can fail independently of the gate being
correct. The hook can be deployed but stale. It can resolve no gate.py and fail
open. It can read the payload's inline message key in a test while production
Stop payloads carry the message only in the transcript. It can block on a red
tree and then keep honouring that block after the tree changes, or, worse, keep
honouring an old PASS.

Until that had an executable oracle, "the standard is in force" was a belief
about configuration, which is the exact category of claim this whole subsystem
was built because an agent got wrong.

ISOLATION

The hook reads the ledger at gate.setup_root()/state/gate-runs.jsonl, and
setup_root() is derived from gate.py's own __file__. So pointing
CLAUDE_SETUP_ROOT at a temp tree containing a copy of gate.py moves the ledger
there too, and this test never writes a row into the real one. That matters more
than convenience: a test that hand-wrote PASS rows into the real ledger would be
manufacturing the exact evidence the Stop hook trusts.

The green in case 5 is EARNED by running the real gate, not fabricated. Case 6
then edits the tree and requires that same green to stop counting.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_GATE = os.path.join(HERE, "gate.py")
LIVE_HOOK = os.path.join(os.path.expanduser("~"), ".claude", "hooks", "ship_gate_stop.py")

DOMAINS = ["build", "unit", "types", "e2e", "a11y_ux",
           "security", "docs", "pipeline", "review", "perf"]

CLAIM = "All done. The feature is implemented and verified, everything works."
NEUTRAL = "Here is what I found in the router; I have not changed anything yet."

failures: list[str] = []
skipped: list[str] = []


def check(name: str, ok: bool, why: str) -> None:
    print("[{}] {}".format("ok  " if ok else "FAIL", name))
    if not ok:
        print("       " + why)
        failures.append(name)


def skip(name: str, why: str) -> None:
    print("[skip] {}".format(name))
    print("       " + why)
    skipped.append(name)


def git(args: list[str], cwd: str) -> None:
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")


def make_setup_root(root: str) -> str:
    """A temp setup tree whose gate.py is a copy of the real one.

    A copy, not an import: setup_root() reads __file__, so the ledger location
    follows the file. Copying is what redirects the ledger.
    """
    gdir = os.path.join(root, "tools", "gate")
    os.makedirs(gdir, exist_ok=True)
    shutil.copy2(REAL_GATE, os.path.join(gdir, "gate.py"))
    os.makedirs(os.path.join(root, "state"), exist_ok=True)
    return root


def make_project(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "app.py"), "w", encoding="utf-8") as fh:
        fh.write("def add(a, b):\n    return a + b\n")
    git(["init", "-q"], path)
    git(["add", "-A"], path)
    git(["-c", "user.email=selftest@local", "-c", "user.name=selftest",
         "commit", "-q", "-m", "initial"], path)


def write_contract(path: str, waived: bool) -> None:
    """A contract that either passes honestly or is silent about every domain.

    waived=True uses live waivers with a far-future expiry, which the gate
    accepts as a real PASS. That is the only way to earn a green in a scratch
    repo with no build system, and it is the same shape gate.py's own selftest
    uses for its all-waived case.
    """
    if waived:
        domains = {d: {"required": True,
                       "waived": {"reason": "enforcement integration selftest",
                                  "until": "2099-01-01"}}
                   for d in DOMAINS}
    else:
        domains = {d: {"required": True,
                       "uncovered_note": "nothing configured for {}".format(d)}
                   for d in DOMAINS}
    with open(os.path.join(path, "quality-contract.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": 1, "project": os.path.basename(path),
                   "domains": domains}, fh, indent=2)


def run_hook(payload: dict, setup_root: str | None,
             hook: str = LIVE_HOOK, extra_env: dict | None = None) -> dict:
    """Drive the hook exactly as Claude Code does: JSON on stdin, JSON on stdout."""
    env = dict(os.environ)
    if setup_root is not None:
        env["CLAUDE_SETUP_ROOT"] = setup_root
    else:
        env.pop("CLAUDE_SETUP_ROOT", None)
    if extra_env:
        env.update(extra_env)
    r = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=120)
    if r.returncode != 0:
        raise AssertionError("hook exited {}: {}".format(r.returncode, r.stderr[-800:]))
    body = (r.stdout or "").strip()
    if not body:
        raise AssertionError("hook produced no stdout at all")
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise AssertionError("hook stdout is not JSON ({}): {!r}".format(e, body[:400]))


def earn_green(setup_root: str, project: str) -> tuple[bool, str]:
    """Run the real gate for real and report whether it recorded a PASS."""
    gate = os.path.join(setup_root, "tools", "gate", "gate.py")
    r = subprocess.run([sys.executable, gate, "run", "--project", project],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    ledger = os.path.join(setup_root, "state", "gate-runs.jsonl")
    if not os.path.exists(ledger):
        return False, ("the gate ran (exit {}) but wrote no ledger at {}; the isolation "
                       "assumption in this test is wrong\n{}".format(
                           r.returncode, ledger, (r.stdout or "")[-600:]))
    rows = [json.loads(l) for l in open(ledger, encoding="utf-8") if l.strip()]
    mine = [x for x in rows if x.get("project_path") == os.path.abspath(project)]
    if not any(x.get("verdict") == "PASS" for x in mine):
        return False, ("no PASS row recorded for this project (exit {}, {} row(s)): {}\n{}".format(
            r.returncode, len(mine),
            [x.get("verdict") for x in mine], (r.stdout or "")[-600:]))
    return True, ""


def main() -> int:
    if not os.path.exists(LIVE_HOOK):
        print("live hook is not deployed at {}".format(LIVE_HOOK))
        print("that is itself the finding: nothing is enforcing at the Stop boundary")
        return 1
    if not os.path.exists(REAL_GATE):
        print("gate.py missing at {}".format(REAL_GATE))
        return 1

    tmp = tempfile.mkdtemp(prefix="enforce-selftest-")
    try:
        setup_root = make_setup_root(os.path.join(tmp, "setup"))

        # ---- 1. a project with no contract is none of the hook's business ----
        bare = os.path.join(tmp, "bare")
        make_project(bare)
        got = run_hook({"cwd": bare, "last_assistant_message": CLAIM}, setup_root)
        check("no contract, hook passes through",
              got == {},
              "a project that never opted in must not be gated, got {}".format(got))

        # ---- the gated project, used by the rest ----
        proj = os.path.join(tmp, "proj")
        make_project(proj)
        write_contract(proj, waived=False)

        # ---- 2. the recursion guard ----
        got = run_hook({"cwd": proj, "last_assistant_message": CLAIM,
                        "stop_hook_active": True}, setup_root)
        check("stop_hook_active short-circuits",
              got == {},
              "without this the block would re-enter itself forever, got {}".format(got))

        # ---- 3. the load-bearing case: a claim on an ungated tree ----
        got = run_hook({"cwd": proj, "last_assistant_message": CLAIM}, setup_root)
        blocked = got.get("decision") == "block"
        check("done-claim on an ungated tree is BLOCKED",
              blocked,
              "this is the entire purpose of the hook. got {}".format(got))
        if blocked:
            reason = got.get("reason") or ""
            check("the block explains itself and names the command",
                  "gate.py run" in reason.replace("\\", "/") or "run --project" in reason,
                  "a block with no remedy just looks like a broken tool: {!r}".format(
                      reason[:300]))

        # ---- 4. no claim means a nudge, not a wall ----
        got = run_hook({"cwd": proj, "last_assistant_message": NEUTRAL}, setup_root)
        check("no done-claim gets a note, not a block",
              got.get("decision") != "block" and bool(got.get("systemMessage")),
              "mid-work turns must not be blocked, but silence would hide the gate. "
              "got {}".format(got))

        # ---- 5. the production path: message only in the transcript ----
        # Stop payloads do not reliably carry the assistant message inline. If only
        # the inline path worked, this hook would be hollow in production while
        # passing every test that fed it an inline key.
        tpath = os.path.join(tmp, "transcript.jsonl")
        with open(tpath, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "user", "message": {"content": "go"}}) + "\n")
            fh.write(json.dumps({"type": "assistant", "message": {"content": [
                {"type": "text", "text": CLAIM}]}}) + "\n")
        got = run_hook({"cwd": proj, "transcript_path": tpath}, setup_root)
        check("blocks on a transcript-only payload (the production shape)",
              got.get("decision") == "block",
              "production Stop payloads carry the message in the transcript, not "
              "inline; got {}".format(got))

        # ---- 6. a green EARNED by the real gate is honoured ----
        write_contract(proj, waived=True)
        ok, why = earn_green(setup_root, proj)
        if not ok:
            check("the real gate can reach PASS on an all-waived contract", False, why)
        else:
            got = run_hook({"cwd": proj, "last_assistant_message": CLAIM}, setup_root)
            check("a green earned for THIS tree is honoured",
                  got == {},
                  "a gate that blocks even when green is a gate nobody will keep "
                  "installed, got {}".format(got))

            # ---- 7. and it does not survive an edit. the crown property. ----
            with open(os.path.join(proj, "sneaky.py"), "w", encoding="utf-8") as fh:
                fh.write("# three more edits after the green\n")
            got = run_hook({"cwd": proj, "last_assistant_message": CLAIM}, setup_root)
            check("the green does NOT survive a change to the tree",
                  got.get("decision") == "block",
                  "if an old PASS still counts after further edits, the gate can be "
                  "passed once and then cited forever, which is the loophole that "
                  "makes every other check decorative. got {}".format(got))

        # ---- 8. an unreachable gate must announce itself, never fail open ----
        # The deployed hook falls back to ~/claude-setup, so making it fail to
        # resolve needs HOME redirected as well as the env override. HERE comes
        # from __file__, so candidate 2 is <userprofile>/tools/gate/gate.py.
        blind = os.path.join(tmp, "blind")
        os.makedirs(blind, exist_ok=True)
        collide = os.path.join(os.path.dirname(os.path.expanduser("~")),
                              os.path.basename(os.path.expanduser("~")),
                              "tools", "gate", "gate.py")
        if os.path.exists(collide):
            skip("unreachable gate announces enforcement is OFF",
                 "cannot construct the unreachable case: {} exists, so the hook's "
                 "second candidate resolves regardless of env".format(collide))
        else:
            got = run_hook({"cwd": proj, "last_assistant_message": CLAIM}, None,
                           extra_env={"CLAUDE_SETUP_ROOT": blind,
                                      "USERPROFILE": blind, "HOME": blind})
            msg = got.get("systemMessage") or ""
            check("unreachable gate announces enforcement is OFF",
                  got != {} and "OFF" in msg,
                  "a guard that cannot run must say so. Failing open silently is how "
                  "three 45-byte hooks went unnoticed for months. got {}".format(got))

        print()
        real_ledger = os.path.join(HERE, "..", "..", "state", "gate-runs.jsonl")
        print("real ledger untouched by this test: {}".format(
            os.path.abspath(real_ledger)))
        if skipped:
            print("{} case(s) skipped: {}".format(len(skipped), skipped))
        if failures:
            print("{} case(s) FAILED: {}".format(len(failures), failures))
            print("the Stop boundary is not enforcing what it claims to enforce")
            return 1
        print("all checks passed")
        print("the live Stop hook blocks a done-claim on an ungated tree, honours a "
              "green it earned, and stops honouring it after the next edit")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
