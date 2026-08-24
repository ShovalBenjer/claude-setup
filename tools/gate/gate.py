#!/usr/bin/env python3
"""Ship gate: the standard a change has to clear before anyone may call it done.

WHY THIS EXISTS

The complaint that produced this file was not "a test failed". It was that an
agent finished a web app, reported it working, and it was not working, because
nothing in the loop was capable of disagreeing with the agent. The repository
had a testing-pyramid skill, a ui-ux skill, a red-team skill, a coverage
enforcer and a completion gate, and every one of them was either advice or a
regex over the assistant's own prose. Three of those hooks turned out to be
45-byte files containing a Linux path that does not exist on this machine.

So the gate is built on one rule: a domain counts as covered only when a command
exits zero, or when a named artifact exists for the current commit. Anything
else is UNCOVERED, and UNCOVERED fails. There is no state in which the gate
passes because nobody got round to configuring a check, because that is exactly
the state the setup was already in.

THE DOMAINS

Fixed list, deliberately. A project cannot pass by declaring a contract with
three easy domains in it: every domain below must be satisfied, waived with a
reason and an expiry date, or declared not-applicable with a justification the
report prints in full.

  build       the thing actually assembles or installs from a clean state
  unit        automated tests, run, with their real exit code
  types       static analysis: typecheck, lint, whatever the stack has
  e2e         tools/e2e/flow.py against the running app, phone viewport, every
              control pressed; this is the domain that was missing entirely
  a11y_ux     the same run read at a stricter threshold: contrast, tap targets,
              labels, text size, since "looks fine on my monitor" is how the
              original defect shipped
  security    no credential material in the change. It does NOT audit
              dependencies, and this line said it did until 2026-08-06. The only
              builtin wired to this domain is secret_scan; grep this file for
              pip-audit, osv or safety and every one returns nothing. A gate
              whose own description promises a check it has never run is the
              exact defect class this gate exists to catch, sitting inside the
              thing that catches it.
              The dependency half runs, but not here: .github/workflows/
              ship-gate.yml has a separate `supply-chain` job on osv-scanner.
              It is deliberately NOT pulled into this domain, because that job
              needs the network and a scanner binary, and a domain that is red
              on every offline run is one that gets waived. Naming where it
              lives beats claiming it happens here.
  docs        the change is described where a reader would look: README or docs
              for behaviour, CHANGELOG for the fact it changed
  pipeline    CI runs these same checks, so local-green cannot diverge from
              merged-green
  review      an independent reviewer looked at THIS commit and said so in an
              artifact; self-assessment does not satisfy this
  perf        only when the contract sets a budget; otherwise not applicable
              with that reason printed

WAIVERS EXPIRE, AND THEY GO STALE BEFORE THEY EXPIRE

A waiver needs a reason and an until-date. An expired waiver is a failure, not a
skip, because a permanent waiver is just a disabled check with better manners.

An until-date only catches the waiver that ran out. It does not catch the one
that stopped being true, and a waiver is a claim about a measurement, so the
measurement moves under it. A waiver may therefore also carry `confirm`, a
string the domain's own command must still print. The gate runs that command
even though the domain is waived, ignores its exit code (a waived command is
expected to fail, which is usually why it was waived), and fails the domain if
the string is gone. See confirm_waiver for the run that made this necessary.

RUN RECORDS

Every run appends to state/gate-runs.jsonl with the commit, whether the tree was
dirty, the per-domain verdicts, and a fingerprint of the working tree. The Stop
hook reads that file and will not accept a green run recorded against a different
tree than the one being claimed done, so a pass cannot be reused after further
edits.

USAGE
  python tools/gate/gate.py init [--project .]        write a starter contract
  python tools/gate/gate.py run [--project .]         run every domain
  python tools/gate/gate.py run --domain e2e          run one domain
  python tools/gate/gate.py status [--project .]      last recorded verdict
  python tools/gate/gate.py selftest

EXIT CODES
  0  every required domain passed
  1  at least one domain failed or is uncovered
  2  the gate could not run at all (no contract, not a git repo)
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import tempfile

CONTRACT_NAME = "quality-contract.json"
LEDGER = os.path.join("state", "gate-runs.jsonl")

# The exit code a check uses to say it could not measure on this host, as opposed
# to measuring something and disliking it. tools/audit/skills_sync.py returns it
# when either skills tree is missing; rules_sync.py and pointers.py express the
# same idea by printing SKIP and staying at 0. Only the waiver confirmation reads
# it, and only to tell "unmeasurable here" apart from "the waiver went stale".
CANNOT_MEASURE = 2

DOMAINS = [
    "build", "unit", "types", "e2e", "a11y_ux",
    "security", "docs", "pipeline", "review", "perf",
]

PASS = "PASS"
FAIL = "FAIL"
UNCOVERED = "UNCOVERED"
WAIVED = "WAIVED"
NA = "N/A"

# Domains whose absence is never acceptable for a user-facing web application.
# perf is the only one that is genuinely optional, and only because a budget
# nobody set cannot be measured.
ALWAYS_REQUIRED = [d for d in DOMAINS if d != "perf"]


# ------------------------------------------------------------------ repo facts

#: The name every domain command in quality-contract.json spells. Ubuntu ships
#: `python3` and no `python`, so on WSL that name resolved to nothing and three
#: required domains returned exit 127 with no failing test behind them. The
#: contract text stays as `python` (see tests/test_gate_python_shim.py for why
#: rewriting it to `python3` just moves the breakage to Windows); the name is
#: supplied on PATH instead, pointing at whatever interpreter is running the gate.
PYTHON_SHIM_NAME = "python"
_SHIM_DIR: str | None = None
_SHIM_RESOLVED = False


def python_shim_dir(which=None, tmpdir=None) -> str | None:
    """A directory providing `python`, or None when the host already has one.

    `which`/`tmpdir` are injectable so the tests can drive both branches on a
    host that happens to disagree with the one being simulated.
    """
    which = shutil.which if which is None else which
    if which(PYTHON_SHIM_NAME):
        return None
    if os.name == "nt":
        # A Windows box without `python` on PATH is a broken install, not a
        # translation problem, and a .bat shim would hide it.
        return None
    d = pathlib.Path(tempfile.mkdtemp(prefix="gate-python-shim-")
                     if tmpdir is None else tmpdir)
    shim = d / PYTHON_SHIM_NAME
    shim.write_text('#!/bin/sh\nexec "{}" "$@"\n'.format(sys.executable),
                    encoding="utf-8")
    shim.chmod(0o755)
    return str(d)


#: `intent-control-plane/.venv` is a Windows virtualenv (Lib/, Scripts/, a
#: pyvenv.cfg naming Python313 under C:\). uv on Linux replaces the environment
#: before syncing and cannot remove that tree over DrvFs, so `build` died with
#: `os error 39` and `unit` and `types` inherited it. Two hosts, two directories.
POSIX_VENV_NAME = ".venv-linux"


def _domain_env() -> dict | None:
    """os.environ plus whatever this host needs, or None when it needs nothing.

    Cached, because run() is called once per domain and creating a temp dir each
    time would leave a trail of them. Never mutates os.environ: the parent's PATH
    is the operator's, and a gate that edits it has changed the machine.
    """
    global _SHIM_DIR, _SHIM_RESOLVED
    if not _SHIM_RESOLVED:
        _SHIM_DIR = python_shim_dir()
        _SHIM_RESOLVED = True

    overlay: dict[str, str] = {}
    if _SHIM_DIR is not None:
        overlay["PATH"] = _SHIM_DIR + os.pathsep + os.environ.get("PATH", "")
    if os.name != "nt" and not os.environ.get("UV_PROJECT_ENVIRONMENT"):
        overlay["UV_PROJECT_ENVIRONMENT"] = POSIX_VENV_NAME
    if not overlay:
        return None
    return dict(os.environ, **overlay)


def run(cmd: str, cwd: str, timeout: int = 900) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8",
                           errors="replace", env=_domain_env())
        out = ((p.stdout or "") + (p.stderr or ""))
        if p.returncode == 127 and "not found" in out:
            return CANNOT_MEASURE, "cannot run: command not found on this host\n{}".format(out)
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "timed out after {}s: {}".format(timeout, cmd)
    except Exception as exc:
        return 127, "could not run: {}".format(exc)


def git(args: str, cwd: str) -> str:
    rc, out = run("git " + args, cwd, timeout=60)
    return out.strip() if rc == 0 else ""


# Paths this gate WRITES while running. They are its output, never the change
# being gated, and hashing them makes the gate unable to pass at the Stop
# boundary: `gate.py run` records a fingerprint and then appends its verdict to
# state/gate-runs.jsonl, which is tracked here, so the recorded fingerprint no
# longer describes the tree the run left behind. Measured 2026-07-27 on this
# repository: one appended ledger row moved the fingerprint from 5dad68ca to
# 62951e50, so no run could ever match the tree it produced, green or not.
#
# state/reviews/ is here for the same reason one level out: the review domain
# shells out to panel.py, which writes state/reviews/<sha>.json. That file
# arrives untracked, so it entered the fingerprint through `git status` rather
# than through the diff, by a different route to the same effect.
#
# Nothing else belongs in this tuple. Every other path under state/ is ordinary
# content, and a change to it is a change to the tree. tests/test_gate_
# fingerprint.py asserts both halves: appends here are invisible, and edits
# anywhere else, tracked or untracked, still move the fingerprint.
GATE_OUTPUTS = ("state/gate-runs.jsonl", "state/reviews/")

# A SECOND class, kept separate because the reason is different and collapsing the
# two would lose it. These are not written by the gate. They are written by the
# harness on a schedule the gated change does not control: the UserPromptSubmit
# hook appends one row to state/prompt-tickets.jsonl for every operator turn, and
# that file is tracked on purpose (content-covered hashes, no prompt text in git),
# so it sits inside the fingerprint and moves it whenever the conversation
# continues.
#
# Measured 2026-07-30 across four consecutive turns of one session, each with a
# fully green run recorded against it: 76378e5f, 05fdfc73, b10cfce6, 9f0ccd38.
# Nothing in the repository changed between the second and third. The gate passed
# every time and the Stop boundary rejected every pass, which is the same
# unsatisfiable-check defect GATE_OUTPUTS above was written to fix, arriving by a
# different route. TODO.md records the same class fixed once already for
# state/handback-log.jsonl, there by untracking it. Untracking is wrong here: the
# ticket ledger is audit evidence and is meant to be in git.
#
# The distinction that keeps this from becoming a blanket state/ exemption: a path
# belongs here only if a turn of conversation alone can change it. An edit any
# agent or operator makes to content is still a change to the tree, including
# under state/.
#
# Found the same way twice on 2026-07-30: the ticket ledger first, then
# state/skill-use.jsonl, written by the live PostToolUse hook skill-usage-log.sh once
# per tool call, which moves the fingerprint faster than the ticket ledger does. The
# reproducible way to find the rest, rather than waiting for each one to block a turn:
#
#   git ls-files -z state/ | (report mtimes)     # tracked ledgers touched this turn
#   grep -rn "state/" ~/.claude/hooks/*.sh *.py  # what the live hooks write
#
# state/hook-fires.log is written by three hooks and is correctly gitignored, so it
# never enters the fingerprint and needs no entry here.
HARNESS_OUTPUTS = (
    "state/prompt-tickets.jsonl",
    "state/skill-use.jsonl",
    # Added 2026-08-06 with the two hooks that write them, and they are the worst
    # offenders yet. route.py runs on EVERY UserPromptSubmit and spawn_log.py on every
    # Agent call, and BOTH resolve their repo from CLAUDE_OS_DIR with a default of
    # ~/claude-setup. So a prompt typed in any project on this host appends to a tracked
    # file in THIS repo and moves its tree fingerprint. A green gate run here could be
    # invalidated by somebody typing in an unrelated repository, which is the
    # self-invalidation failure already on record, promoted from per-session to per-host.
    #
    # Third finding of the class, 2026-08-12, after the operator named the cost
    # ("the hook ... really slows me down"): one session was forced through three
    # full gate runs in 18 hours with no gated content changing between them.
    # route.py appends per prompt, spawn_log.py per Agent call, slop_lint.py per
    # lint invocation, and the agent-feed systemd timer appends the cursor on a
    # 30-minute clock. All four are the harness writing on its own schedule.
    # state/claims.jsonl, lessons.jsonl, resource-ledger.jsonl and bus.jsonl stay
    # IN the fingerprint on purpose: those rows are authored content.
    "state/routing.jsonl",
    "state/agent-spawns.jsonl",
    "state/prose-scores.jsonl",
    "state/telemetry-published.txt",
    # Fourth mover of the class, 2026-08-12 evening: the discussion publisher's
    # cursor, same writer-on-its-own-schedule shape as its sibling above. It
    # appended once mid-session and forced a full regate of an unchanged tree.
    "state/telemetry-published-discussion.txt",
)

_EXCLUDE = " ".join('":(exclude){}"'.format(p)
                    for p in GATE_OUTPUTS + HARNESS_OUTPUTS)


def tree_fingerprint(cwd: str) -> tuple[str, bool, str]:
    """Commit, dirty flag, and a hash of the working tree's tracked content.

    The fingerprint is what makes a green run non-reusable. Without it an agent
    can pass the gate, make three more edits, and cite the earlier pass; the
    fingerprint changes the moment the tree does, so the Stop hook can tell.

    It covers the gate's INPUTS only. See GATE_OUTPUTS above for why, and for
    the one way this can go wrong: an over-broad exclusion buys a satisfiable
    gate by going blind, which is the same defect wearing the opposite sign.
    """
    sha = git("rev-parse HEAD", cwd) or "no-commit"
    # `dirty` keeps reporting the whole tree. It is shown to a human, not
    # matched against anything, and hiding the gate's own writes from it would
    # make a tree with uncommitted output read as clean.
    dirty = bool(git("status --porcelain", cwd).strip())
    status = git("status --porcelain -- . " + _EXCLUDE, cwd)
    h = hashlib.sha256()
    # Fifth finding of the self-invalidation class, 2026-08-23: hashing the raw
    # HEAD sha meant a COMMIT containing nothing but excluded ledgers (the usual
    # "chore(state): gate row" before a merge) minted a new fingerprint and
    # invalidated the run it was recording; the exclusions below never got a say.
    # So the commit's contribution is the tracked content MINUS the exclusions:
    # `ls-files -s` lists every tracked path with its staged blob sha, honours
    # the same pathspec magic, and costs one index read. A ledger-only commit
    # leaves this listing byte-identical; any content commit changes a blob sha.
    h.update(git("ls-files -s -- . " + _EXCLUDE, cwd).encode("utf-8", "replace"))
    # git diff of tracked files plus the names of untracked ones: enough to
    # notice any edit, cheap enough to run on every gate invocation.
    h.update(git("diff HEAD -- . " + _EXCLUDE, cwd).encode("utf-8", "replace"))
    h.update(status.encode("utf-8", "replace"))
    return sha, dirty, h.hexdigest()[:16]


# ------------------------------------------------------------------ contract

def detect_stack(project: str) -> dict:
    has = lambda *names: any(os.path.exists(os.path.join(project, n)) for n in names)
    pkg = {}
    pj = os.path.join(project, "package.json")
    if os.path.exists(pj):
        try:
            pkg = json.load(open(pj, encoding="utf-8"))
        except Exception:
            pkg = {}
    scripts = (pkg.get("scripts") or {}) if isinstance(pkg, dict) else {}
    runner = "bun" if has("bun.lockb", "bun.lock") else (
        "pnpm" if has("pnpm-lock.yaml") else ("yarn" if has("yarn.lock") else "npm"))
    return {
        "node": bool(pkg),
        "scripts": sorted(scripts.keys()),
        "runner": runner,
        "python": has("pyproject.toml", "requirements.txt", "setup.py"),
        "uv": has("uv.lock"),
        "ci": [p for p in (".github/workflows",) if os.path.isdir(os.path.join(project, p))],
    }


def starter_contract(project: str) -> dict:
    st = detect_stack(project)
    s = set(st["scripts"])
    r = st["runner"]
    nx = "npx" if r == "npm" else ("bunx" if r == "bun" else r + " dlx")

    def script(name: str) -> str | None:
        return "{} run {}".format(r, name) if name in s else None

    def first(*names: str) -> str | None:
        for n in names:
            got = script(n)
            if got:
                return got
        return None

    c: dict = {
        "project": os.path.basename(os.path.abspath(project)),
        "created": datetime.date.today().isoformat(),
        "app": {
            "start": first("dev", "start") or None,
            "url": "http://localhost:3000",
            "routes": [],
            "_comment": "start is the command that serves the app; the e2e domain "
                        "needs the app already running at url. Leave routes empty "
                        "to let the audit discover them by crawling links, or list "
                        "them explicitly when routes are behind state.",
        },
        "domains": {},
    }

    def dom(name: str, cmd: str | None, note: str) -> dict:
        if cmd:
            return {"required": True, "cmd": cmd}
        return {"required": True, "uncovered_note": note}

    c["domains"]["build"] = dom("build", first("build"),
                                "no build script found; set a command that assembles the app")
    c["domains"]["unit"] = dom("unit", first("test", "test:unit"),
                               "no test script found; a project with no tests cannot pass this gate")
    types_cmd = first("typecheck", "lint", "check")
    if not types_cmd and st["node"]:
        types_cmd = "{} tsc --noEmit".format(nx)
    if not types_cmd and st["python"]:
        types_cmd = "python -m compileall -q ."
    c["domains"]["types"] = dom("types", types_cmd, "no typecheck or lint command found")
    c["domains"]["e2e"] = {
        "required": True,
        "cmd": ("python {}/tools/e2e/flow.py audit ${{APP_URL}} --viewport mobile "
                "--out state/e2e/last.json").format(setup_root().replace("\\", "/")),
        "_comment": "APP_URL is substituted from app.url. Add --strict once the "
                    "warning backlog is at zero.",
    }
    c["domains"]["a11y_ux"] = {
        "required": True,
        "read_report": "state/e2e/last.json",
        "max_warn": 0,
        "_comment": "reads the e2e report and fails on accessibility and mobile "
                    "layout warnings, which the e2e domain only reports.",
    }
    c["domains"]["security"] = {"required": True, "builtin": "secret_scan"}
    c["domains"]["docs"] = {"required": True, "builtin": "docs_touched",
                            "paths": ["README.md", "docs/", "CHANGELOG.md"]}
    c["domains"]["pipeline"] = {"required": True, "builtin": "ci_runs_gate"}
    c["domains"]["review"] = {
        "required": True,
        "artifact": "state/reviews/${SHA}.json",
        # No --out: panel.py defaults to state/reviews/<HEAD sha>.json, which is
        # exactly where the artifact check looks. Naming the path twice invites the
        # two to drift, and a ${SHA} left unexpanded by a shell would silently write
        # to state/reviews/.json.
        "cmd": "python {}/tools/review/panel.py run --project .".format(
            setup_root().replace("\\", "/")),
        "_comment": (
            "an independent review of THIS commit. The cmd above runs the local "
            "persona panel, which checks the added lines against 32 named defect "
            "patterns across security, correctness, mobile UX, release hygiene and "
            "data, and writes the artifact the gate then verifies. It reads syntax, "
            "not intent, and its own artifact says so. For a change where a wrong "
            "algorithm would matter, add a second pass that reads for meaning: "
            "`python tools/review/panel.py run --project . --allow-external` for a "
            "free-model opinion, or dot-claude/bin/external-review-judge.py review "
            "--repo . --provider codex for the bounded read-only Codex reviewer. The "
            "gate checks only that an artifact exists, names this commit, names a "
            "reviewer who is not the author, and reaches a verdict."),
    }
    c["domains"]["perf"] = {"required": False,
                            "na_reason": "no performance budget declared for this project"}
    return c


def setup_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def load_contract(project: str) -> dict | None:
    p = os.path.join(project, CONTRACT_NAME)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ builtins

SECRET_PATTERNS = [
    ("aws access key", r"AKIA[0-9A-Z]{16}"),
    ("private key block", r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    ("github token", r"gh[pousr]_[A-Za-z0-9]{30,}"),
    ("slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("google api key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("openai style key", r"sk-[A-Za-z0-9]{20,}"),
    ("anthropic key", r"sk-ant-[A-Za-z0-9\-_]{20,}"),
    ("bearer literal", r"(?i)authorization\s*[:=]\s*['\"]?bearer\s+[A-Za-z0-9._\-]{20,}"),
    ("assigned secret", r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*"
                       r"['\"][A-Za-z0-9/+_\-\.]{16,}['\"]"),
]

# KNOWN BLIND SPOT, named rather than left to be discovered. "assigned secret"
# is the only rule above that keys on the variable NAME instead of the value's
# own shape, so an author can walk out of it by renaming the left side. `\b`
# does not match before an underscore, so SECRET_NAME= is silent where SECRET=
# is not. Measured 2026-07-25: dot-claude/bin/*-launcher.sh held a Key Vault
# ENTRY NAME in a variable called SECRET, this fired on it correctly, and the
# repair was to rename the variable -- the same keystroke that would hide a
# live key. It is deliberately not widened to secret\w*, which would re-flag
# those launchers and every other honest SECRET_NAME, and a rule that cries
# wolf on correct code gets waived and then finds nothing at all. The
# value-shaped rules carry the real weight: AKIA, sk-, ghp_ and a PEM header
# match whatever they are assigned to.
SECRET_SKIP = re.compile(
    r"(?i)(^|/)(\.git|node_modules|dist|build|\.next|\.venv|venv|__pycache__|"
    r"coverage|\.turbo|target)(/|$)")

# Strings a vendor PUBLISHES in its own documentation as a worked example. They
# are not credentials; appearing in public is their entire purpose. A test that
# signs a vendor's documented example and asserts the vendor's documented
# signature has to carry the literal, so a scanner with no way to say "this one
# is public" leaves a project two bad options: weaken its own oracle, or waive
# the whole security domain and stop looking for real keys. A narrow named
# allowlist is better than either.
#
# The bar for adding an entry: the exact string appears in the vendor's own
# public documentation as an example, and it authenticates nothing anywhere.
#
# Deliberately plaintext rather than hashed. A hash would keep this file free of
# key-shaped strings, but it would also let someone allowlist a REAL secret with
# nothing for a reviewer to look at. The literal is auditable; the hash is not.
# The cost is that this file matches its own scanner, which is fine: the scan
# below suppresses it by the same rule as anywhere else, and says so out loud.
PUBLIC_TEST_VECTORS = [
    ("aws docs example access key", "AKIAIOSFODNN7EXAMPLE"),
    ("aws sigv4 test-suite access key", "AKIDEXAMPLE"),
    ("aws docs example secret key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
    ("aws sigv4 test-suite secret key", "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"),
]


def _first_pattern_hit(line: str) -> str | None:
    for name, pat in SECRET_PATTERNS:
        if re.search(pat, line):
            return name
    return None


def _vector_allowlist(spec: dict | None) -> tuple[list[tuple[str, str]], list[str]]:
    """Built-in vectors plus any the contract declares, and complaints about the latter.

    A contract entry must carry a `why`. An allowlist entry with no stated reason
    is indistinguishable from someone silencing a real finding, so it is refused
    rather than honoured, and the refusal is a gate failure rather than a warning.
    """
    vectors = list(PUBLIC_TEST_VECTORS)
    problems: list[str] = []
    for i, entry in enumerate(list((spec or {}).get("public_vectors") or [])):
        if not isinstance(entry, dict):
            problems.append("public_vectors[{}] is not an object".format(i))
            continue
        value = entry.get("value")
        why = str(entry.get("why") or "").strip()
        if not value:
            problems.append("public_vectors[{}] declares no value".format(i))
            continue
        if not why:
            problems.append(
                "public_vectors[{}] declares a value with no `why`, so it is refused".format(i))
            continue
        vectors.append(("contract: " + why[:60], value))
    return vectors, problems


def secret_scan(project: str, contract: dict, spec: dict | None = None) -> tuple[str, str]:
    """Look for credential material in tracked files. Never print what it finds.

    Reports file, line number and which pattern matched. The matched text is
    never echoed, because a gate that prints the secret it found has leaked it
    into a log, a transcript and possibly a commit message.

    Published test vectors are suppressed by removing them from the line and
    scanning what is left. That ordering matters: a real key sitting on the same
    line as an example one still fires, because the line minus the example still
    matches. Suppressions are counted and named in the evidence either way, so
    an allowlisted hit is never a silent one.
    """
    vectors, problems = _vector_allowlist(spec)
    vector_values = [v for _, v in vectors]
    files = [f for f in git("ls-files", project).splitlines() if f.strip()]
    hits: list[str] = list(problems)
    suppressed: list[str] = []
    scanned = 0
    for rel in files:
        if SECRET_SKIP.search(rel):
            continue
        path = os.path.join(project, rel)
        try:
            if os.path.getsize(path) > 2_000_000:
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except (OSError, ValueError):
            continue
        scanned += 1
        for i, line in enumerate(lines, 1):
            if len(line) > 4000:
                continue
            name = _first_pattern_hit(line)
            if not name:
                continue
            redacted = line
            used: list[str] = []
            for vname, value in vectors:
                if value and value in redacted:
                    redacted = redacted.replace(value, "")
                    used.append(vname)
            if used:
                residual = _first_pattern_hit(redacted)
                if residual is None:
                    suppressed.append("{}:{}  {}".format(rel, i, ", ".join(sorted(set(used)))))
                    continue
                # Something else on this line still matches once the published
                # example is taken out, so the example was not the finding.
                name = residual
            hits.append("{}:{}  {} (value withheld)".format(rel, i, name))
    # A tracked .env is a finding on its own, whatever is inside it.
    for rel in files:
        base = os.path.basename(rel)
        if base == ".env" or base.startswith(".env."):
            if not base.endswith((".example", ".sample", ".template")):
                hits.append("{}  tracked env file, so its contents are in git history".format(rel))
    note = ""
    if suppressed:
        note = "\n  {} match(es) suppressed as published test vectors:\n    ".format(
            len(suppressed)) + "\n    ".join(suppressed[:20])
    if hits:
        return FAIL, "{} finding(s) across {} tracked files:\n  ".format(
            len(hits), scanned) + "\n  ".join(hits[:20]) + note
    return PASS, "{} tracked files scanned, no credential patterns matched".format(scanned) + note


def _porcelain_paths(out: str) -> list[str]:
    """Every path named by `git status --porcelain`, both sides of a rename.

    Porcelain v1 lines are `XY path`, or `XY orig -> path` for a rename or copy,
    and a path holding a special or non-ASCII character comes back C-quoted. The
    old parse was `line.split(None, 1)[-1]`, which handed back the whole string
    `orig -> path` as one pseudo-path for a rename, kept the quotes on a quoted
    name, and split a path containing a space in the wrong place. All three make
    a path that matches nothing and exists nowhere, so they quietly drop real
    changes out of the comparison.
    """
    paths = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        # Porcelain reserves two columns for the status and one for a space, so
        # `line[3:]` is the path -- except on the first line, because `git()`
        # strips the whole output and an unstaged change leads with a space. So
        # ` D README.md` arrives as `D README.md` and a fixed slice returns
        # `EADME.md`, a path that exists nowhere and matches nothing. Check the
        # column is really a space before trusting it. The selftest below caught
        # this: the fix for the deletion bug reported `deleted: EADME.md`.
        rest = line[3:] if line[2] == " " else line.split(None, 1)[-1]
        rest = rest.strip()
        halves = rest.split(" -> ") if " -> " in rest else [rest]
        for half in halves:
            half = half.strip()
            if len(half) >= 2 and half.startswith('"') and half.endswith('"'):
                body = half[1:-1]
                try:
                    # git C-quotes as octal escapes of the UTF-8 bytes.
                    half = body.encode("ascii", "backslashreplace").decode(
                        "unicode_escape").encode("latin-1").decode("utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    half = body
            if half:
                paths.append(half)
    return paths


def docs_touched(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    """Did this change say anywhere a human would look that it changed?

    Compares the change against the documentation paths. A code change with no
    documentation change is the normal case for a typo and a defect for a
    behaviour change, so the rule is proportional: it only fires once the change
    is large enough that a reader would need telling.
    """
    paths = spec.get("paths") or ["README.md", "docs/", "CHANGELOG.md"]
    base = spec.get("base") or default_base(project)
    changed = [l for l in git("diff --name-only {}...HEAD".format(base), project).splitlines() if l]
    changed += _porcelain_paths(git("status --porcelain", project))
    changed = sorted(set(c.strip() for c in changed if c.strip()))
    if not changed:
        return PASS, "no change to document relative to {}".format(base)

    code = [c for c in changed if re.search(
        r"\.(ts|tsx|js|jsx|py|go|rs|java|kt|swift|rb|php|cs|sql|sh|ps1)$", c)]
    # Documentation only counts if it is still there to read. Both source lists
    # above name deleted files too, which is right for `code` -- deleting a
    # module is a change a reader needs told about -- and backwards for `docs`,
    # because the one change guaranteed to leave a reader with less to read
    # would otherwise be the change that satisfies the check. Found live on
    # new-recruit 2026-07-25: the domain reported PASS citing six
    # `.claude/rules/*.md` files by name while all thirteen files in that
    # directory were deleted from the working tree.
    root = git("rev-parse --show-toplevel", project) or project
    named = [c for c in changed if any(
        c == p or c.startswith(p.rstrip("/") + "/") or c.endswith(".md") for p in paths)]
    docs = [c for c in named if os.path.exists(os.path.join(root, c))]
    gone = [c for c in named if c not in docs]
    if not code:
        return PASS, "no source files changed, so nothing to document"
    if docs:
        ev = "{} source file(s) changed, documented in: {}".format(
            len(code), ", ".join(docs[:6]))
        if gone:
            ev += "\n  {} documentation file(s) deleted, not counted: {}".format(
                len(gone), ", ".join(gone[:6]))
        return PASS, ev
    if gone:
        return FAIL, ("{} source file(s) changed and the only documentation touched was "
                      "{} file(s) that no longer exist on disk. Deleting documentation is "
                      "not writing it.\n  deleted: {}\n  changed: {}".format(
                          len(code), len(gone), ", ".join(gone[:10]), ", ".join(code[:10])))
    if len(code) <= 2:
        return PASS, ("{} source file(s) changed with no doc change, which is under the "
                      "threshold where a reader needs telling: {}".format(
                          len(code), ", ".join(code)))
    return FAIL, ("{} source files changed and nothing in {} was touched. Say what "
                  "changed where a reader would look.\n  changed: {}".format(
                      len(code), ", ".join(paths), ", ".join(code[:10])))


def default_base(project: str) -> str:
    for cand in ("origin/main", "origin/master", "main", "master"):
        if git("rev-parse --verify --quiet " + cand, project):
            return cand
    return "HEAD~1"


def ci_runs_gate(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    """Does CI run the same checks this gate ran locally?

    The failure this prevents is the one where local is green, CI is green, and
    they are green about different things. A pipeline that does not invoke the
    gate cannot stop a regression the gate would catch.
    """
    wf_dir = os.path.join(project, ".github", "workflows")
    files = []
    if os.path.isdir(wf_dir):
        files = [os.path.join(wf_dir, f) for f in os.listdir(wf_dir)
                 if f.endswith((".yml", ".yaml"))]
    for extra in ("azure-pipelines.yml", ".gitlab-ci.yml", "Jenkinsfile"):
        p = os.path.join(project, extra)
        if os.path.exists(p):
            files.append(p)
    if not files:
        return FAIL, ("no CI configuration found, so nothing re-checks this on the way in. "
                      "Add a workflow that runs `gate.py run`.")

    blob = ""
    for f in files:
        try:
            blob += open(f, encoding="utf-8", errors="replace").read() + "\n"
        except OSError:
            continue
    if re.search(r"gate\.py\s+run", blob):
        return PASS, "CI invokes gate.py run ({})".format(
            ", ".join(os.path.basename(f) for f in files))

    # Fall back to per-domain command matching, which is weaker but honest about
    # being weaker.
    cmds = [d.get("cmd") for d in (contract.get("domains") or {}).values() if d.get("cmd")]
    missing = []
    for cmd in cmds:
        token = re.split(r"\s+", cmd.strip())[-1]
        if token and token not in blob:
            missing.append(cmd)
    if not cmds:
        return FAIL, "CI exists but the contract declares no commands for it to run"
    if missing:
        return FAIL, ("CI does not invoke gate.py run, and these contract commands do not "
                      "appear in it either, so local-green and CI-green are about different "
                      "things:\n  " + "\n  ".join(missing[:8]))
    return PASS, ("CI does not call gate.py directly but every contract command appears in "
                  "{}".format(", ".join(os.path.basename(f) for f in files)))


def read_e2e_report(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    path = os.path.join(project, spec.get("read_report", "state/e2e/last.json"))
    if not os.path.exists(path):
        return UNCOVERED, ("no e2e report at {}, so accessibility and mobile layout were "
                           "never measured".format(spec.get("read_report")))
    try:
        rep = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return FAIL, "e2e report is unreadable: {}".format(exc)

    kinds = ("contrast", "target", "label", "name", "text", "overflow", "image", "head", "layout")
    picked: list[dict] = []
    for routes in (rep.get("by_viewport") or {}).values():
        for r in routes:
            for f in r.get("findings", []):
                if f.get("kind") in kinds:
                    picked.append(f)
    fails = [f for f in picked if f.get("sev") == "fail"]
    warns = [f for f in picked if f.get("sev") == "warn"]
    max_warn = spec.get("max_warn", 0)

    # A report from a different tree is not evidence about this one.
    stamp = rep.get("fingerprint")
    _, _, fp = tree_fingerprint(project)
    stale = stamp and stamp != fp

    lines = ["{} fail, {} warn across accessibility and mobile layout".format(
        len(fails), len(warns))]
    for f in (fails + warns)[:12]:
        lines.append("  {}  {}  {}".format(f["sev"], f["kind"], f["msg"][:150]))
    if stale:
        lines.append("  report was produced against tree {} but the tree is now {}".format(
            stamp, fp))
    body = "\n".join(lines)
    if stale:
        return FAIL, body
    if fails or len(warns) > max_warn:
        return FAIL, body
    return PASS, body


def review_artifact(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    sha, dirty, fp = tree_fingerprint(project)
    tmpl = spec.get("artifact", "state/reviews/${SHA}.json")
    path = os.path.join(project, tmpl.replace("${SHA}", sha).replace("${FP}", fp))
    if not os.path.exists(path):
        # A dirty tree has no commit to review yet; say so precisely rather than
        # pretending a review of the parent commit covers uncommitted work.
        return UNCOVERED, ("no independent review artifact at {}. {}".format(
            os.path.relpath(path, project),
            "The tree is dirty, so commit first and have a reviewer that is not the "
            "author record a verdict for that commit."
            if dirty else
            "Have a reviewer that is not the author record a verdict for {}.".format(sha[:12])))
    try:
        art = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        return FAIL, "review artifact is unreadable: {}".format(exc)
    verdict = str(art.get("verdict", "")).lower()
    if art.get("commit") and art["commit"] != sha:
        return FAIL, "review artifact names commit {} but HEAD is {}".format(
            str(art["commit"])[:12], sha[:12])
    if art.get("reviewer") in (None, "", "self", "author"):
        return FAIL, ("review artifact does not name an independent reviewer; "
                      "self-review does not satisfy this domain")
    if verdict in ("pass", "approve", "approved", "lgtm"):
        return PASS, "reviewed by {}: {}".format(art.get("reviewer"),
                                                 str(art.get("summary", ""))[:200])
    return FAIL, "reviewer {} did not approve: {}".format(
        art.get("reviewer"), str(art.get("summary") or verdict)[:200])


def codemap(project: str, spec: dict, sub: str) -> tuple[str, str]:
    """Run tools/map/codemap.py and report what it reported.

    Shelling out rather than importing, so the evidence in this report is the
    output of the command a human runs to reproduce it, and the rule has one
    implementation instead of two that drift.
    """
    tool = "tools/map/codemap.py"
    if not os.path.exists(os.path.join(project, *tool.split("/"))):
        return FAIL, ("the contract asks for the {} check and {} is not in this "
                      "repository. Deleting the tool is the cheapest way to disable a "
                      "domain, so it reads as a failed domain, not an absent one.".format(
                          sub, tool))
    cmd = '"{}" {} {}'.format(sys.executable, tool, sub)
    rc, out = run(cmd, project, timeout=spec.get("timeout", 300))
    lines = [l for l in out.splitlines() if l.strip()]
    if rc == 0:
        # Everything, not the tail. On the prior-art pass path most of this output
        # is the list of components excluded from the audit with the reason for
        # each, and an exclusion the report hides is a silent suppression.
        return PASS, cap(lines, 20)
    fails = [l for l in lines if l.startswith("FAIL")]
    other = [l for l in lines if not l.startswith("FAIL")]
    body = cap(fails or lines, 14)
    if fails and other:
        # The rest is what the tool chose not to check and why. It belongs in the
        # failing report as much as the passing one: a reader deciding whether the
        # audit is honest needs the exclusions in front of them either way.
        body += "\n" + cap(other, 6)
    return FAIL, body + "\n  reproduce: {} {}".format(tool, sub)


def cap(lines: list[str], n: int) -> str:
    if len(lines) <= n:
        return "\n".join(lines)
    return "\n".join(lines[:n] + ["... and {} more".format(len(lines) - n)])


def dir_map(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    return codemap(project, spec, "check")


def prior_art(project: str, contract: dict, spec: dict) -> tuple[str, str]:
    return codemap(project, spec, "prior-art")


BUILTINS = {
    "secret_scan": secret_scan,
    "docs_touched": docs_touched,
    "ci_runs_gate": ci_runs_gate,
    "dir_map": dir_map,
    "prior_art": prior_art,
}


# ------------------------------------------------------------------ the run

def expired(until: str) -> bool:
    try:
        return datetime.date.fromisoformat(until) < datetime.date.today()
    except Exception:
        return True


def eval_domain(name: str, spec: dict, project: str, contract: dict,
                verbose: bool) -> dict:
    out = {"domain": name, "status": UNCOVERED, "evidence": "", "cmd": None}

    if spec is None:
        out["evidence"] = ("the contract does not mention this domain at all, so nothing "
                           "measured it")
        return out

    waiver = spec.get("waived")
    if waiver:
        reason = waiver.get("reason") or "no reason given"
        until = waiver.get("until") or ""
        if not until or expired(until):
            out["status"] = FAIL
            out["evidence"] = ("waiver {} on {}: {}. A waiver with no expiry, or a stale one, "
                               "is a disabled check.".format(
                                   "expired" if until else "has no until date", until or "-", reason))
            return out
        out["status"] = WAIVED
        out["evidence"] = "waived until {}: {}".format(until, reason)
        if waiver.get("confirm"):
            st, ev, confirmed = confirm_waiver(project, spec, waiver["confirm"], verbose)
            out["status"] = st
            out["cmd"] = spec.get("cmd")
            out["evidence"] += "\n" + ev
            out["confirmed"] = confirmed
        return out

    if spec.get("na_reason"):
        out["status"] = NA
        out["evidence"] = "not applicable: {}".format(spec["na_reason"])
        return out

    if spec.get("read_report"):
        st, ev = read_e2e_report(project, contract, spec)
        out["status"], out["evidence"] = st, ev
        return out

    if spec.get("artifact"):
        st, ev = review_artifact(project, contract, spec)
        # A domain that can only ever say "no artifact here" pushes the real work
        # onto a human remembering an incantation, and what humans do with that is
        # waive the domain. So if the contract also names a command that produces the
        # artifact, run it and read what it wrote. The verdict still comes from the
        # artifact, never from the command's exit code, because a reviewer that
        # approves by exiting zero is not a reviewer.
        #
        # Unconditionally, not only when the artifact is missing. The artifact is
        # keyed by commit SHA, so on a dirty tree every edit makes a new tree under
        # the same key and the previous review answers for code it never saw. That
        # is not theoretical: on 2026-07-25 this domain reported seven high findings
        # that had already been fixed, from an artifact written before the fix, while
        # the same producer run by hand reported none. Read the other way it is a
        # false green, a review from three edits ago standing in for code nobody has
        # read, which is the one thing this domain exists to prevent. Freshness by
        # construction beats a staleness check, because the check needs the producer
        # and the gate to agree on a tree hash and two implementations of one rule
        # drift.
        #
        # The cost is that a richer artifact for this same commit gets overwritten by
        # the contract's producer: run `panel.py --allow-external` by hand and the
        # next gate run replaces it with the local panel's. That is the right trade
        # while external review is unwired, and the wrong one once it is, so when an
        # external reviewer becomes part of the contract this needs to preserve a
        # non-approval it did not produce rather than re-running over it.
        if spec.get("cmd"):
            producer = spec["cmd"].replace(
                "${APP_URL}", (contract.get("app") or {}).get("url") or "http://localhost:3000")
            if verbose:
                print("    $ " + producer, file=sys.stderr)
            rc, output = run(producer, project, timeout=spec.get("timeout", 900))
            out["cmd"] = producer
            st, ev = review_artifact(project, contract, spec)
            if st == UNCOVERED:
                short = "\n".join([l for l in output.splitlines() if l.strip()][-8:])
                ev = ("{} The producer ran (exit {}) and still left no readable "
                      "artifact.\n{}".format(ev, rc, indent(short)))
        out["status"], out["evidence"] = st, ev
        return out

    builtin = spec.get("builtin")
    if builtin:
        fn = BUILTINS.get(builtin)
        if not fn:
            out["status"] = FAIL
            out["evidence"] = "contract names an unknown builtin: {}".format(builtin)
            return out
        st, ev = fn(project, contract, spec)
        out["status"], out["evidence"] = st, ev
        return out

    cmd = spec.get("cmd")
    if not cmd:
        out["evidence"] = spec.get("uncovered_note") or (
            "the contract declares this domain with no command, artifact or builtin, "
            "so nothing measured it")
        return out

    app = contract.get("app") or {}
    cmd = cmd.replace("${APP_URL}", app.get("url") or "http://localhost:3000")
    out["cmd"] = cmd
    if verbose:
        print("    $ " + cmd, file=sys.stderr)
    rc, output = run(cmd, project, timeout=spec.get("timeout", 900))
    tail = "\n".join([l for l in output.splitlines() if l.strip()][-14:])
    if rc == CANNOT_MEASURE and "cannot run" in output:
        # Host-shaped check on the wrong host (skills_sync on a CI runner with no
        # live ~/.claude): measurable-or-not is a different question from
        # pass-or-fail, the same exception confirm_waiver() already carries
        # (L-2026-07-31-g). BOTH signals are required: exit 2 alone is argparse's
        # usage-error code, and the phrase alone is a marker matched by existence
        # (L-2026-08-05-a). Surfaced 2026-08-12 when the skills waiver was
        # removed on a locally-CLEAN check and every CI gate run went red.
        # The `unmeasured` flag feeds the ledger row (merged from the branch-side
        # copy of this fix): a PASS with unmeasurable required domains records
        # which checks never measured, distinguishable from a full local PASS.
        out["status"] = NA
        out["unmeasured"] = True
        out["evidence"] = ("unmeasurable on this host: exit {} from `{}`\n{}"
                           .format(rc, cmd, indent(tail)))
        return out
    out["status"] = PASS if rc == 0 else FAIL
    out["evidence"] = "exit {} from `{}`\n{}".format(rc, cmd, indent(tail))
    return out


def confirm_waiver(project: str, spec: dict, confirm: str,
                   verbose: bool = False) -> tuple[str, str, str]:
    """Run a waived domain's own command and check the waiver still describes it.

    A waiver is a claim about a measurement: 51 items, 3 failing tests, one
    unported check. The measurement moves and the claim does not, so a waiver
    that was honest when written turns into a disabled check somewhere between
    the day it was written and the day it expires. `until` only catches the
    second of those.

    Measured here, 2026-08-07. The `skills` waiver ends with its own confirmation
    step in prose: "CONFIRM BY RUNNING: python tools/audit/skills_sync.py check
    -- expect 'DRIFT: 51'. If it prints a different number this waiver is stale."
    A gate run that day printed that sentence verbatim as the domain's evidence,
    reported WAIVED, and returned VERDICT: PASS. The checker, run by hand ninety
    seconds later, printed DRIFT: 29 and exited 1. So the gate recited a
    falsifier, did not run it, and went green. Nothing in the run was false; the
    output simply asserted more than the run had measured, which is the class the
    whole contract exists to catch.

    The fix is not to un-waive the domain. It is that a waiver may carry a
    `confirm` string, and the gate runs the domain's command anyway and looks for
    it. A stale waiver then fails exactly like an expired one, and for the same
    reason: what is left is a check nobody runs and a justification that no
    longer describes it.

    Pass or fail is not read from the exit code. A waived domain's command is
    expected to be non-zero, since that is usually why it was waived; what is
    being tested is whether the waiver's own description of the failure still
    holds. Exit code CANNOT_MEASURE is the one exception, and it is a different
    question: measurable or not, rather than pass or fail.

    That exception exists because the first version of this function did not have
    it and shipped a host-shaped check, the class already on the ledger as
    L-2026-07-31-g. `skills_sync.py check` compares the repo tree against the live
    `~/.claude/skills`, which does not exist on a CI runner, so it printed
    "cannot run: no live skills tree" and exited 2. The confirm string was absent
    from that output for a reason that has nothing to do with the waiver, and the
    gate called the waiver STALE and failed the branch on 2026-08-07. The same
    commit had passed locally an hour earlier, where the live tree is real.

    The signal is the exit code rather than a marker string in the output, because
    a marker matched by substring is an oracle validated by existence rather than
    content (L-2026-08-05-a): reword the tool's message and unmeasurable silently
    becomes stale, or write the marker too loosely and real drift becomes a skip.
    Exit 2 is the convention its sibling checks already keep, and a tool's own
    selftest can pin it. What this cannot do is tell a genuinely unmeasurable host
    from a check that has quietly stopped being able to measure anywhere, so the
    unconfirmed state is printed on the domain and recorded on the run, never
    folded into an ordinary WAIVED.
    """
    cmd = spec.get("cmd")
    if not cmd:
        return FAIL, ("the waiver carries a confirm string and the domain names no command "
                      "that could produce it, so the confirmation can never run"), "no-cmd"
    if verbose:
        print("    $ " + cmd + "   (confirming the waiver)", file=sys.stderr)
    rc, output = run(cmd, project, timeout=spec.get("timeout", 900))
    tail = "\n".join([l for l in output.splitlines() if l.strip()][-8:])
    if rc == CANNOT_MEASURE:
        return WAIVED, ("waiver NOT confirmed on this host: `{}` exited {}, the convention for "
                        "a check that cannot measure here rather than one that failed. The "
                        "waiver is still live, and this run asserts strictly less about it "
                        "than a run where the confirmation completed.\n{}".format(
                            cmd, CANNOT_MEASURE, indent(tail))), "unmeasurable"
    if confirm in output:
        return WAIVED, "waiver confirmed: `{}` still reports {}".format(cmd, confirm), "yes"
    return FAIL, ("waiver STALE: `{}` no longer reports {}, so the waiver describes a "
                  "measurement that has moved. Restate it with the current numbers or "
                  "clear it.\n{}".format(cmd, confirm, indent(tail))), "stale"


def indent(text: str, pad: str = "    ") -> str:
    return "\n".join(pad + l for l in text.splitlines()) if text else pad + "(no output)"


def cmd_run(args: argparse.Namespace) -> int:
    started = time.monotonic()
    project = os.path.abspath(args.project)
    contract = load_contract(project)
    if contract is None:
        print("no {} in {}".format(CONTRACT_NAME, project))
        print("The gate has nothing to enforce. Write one with:")
        print("  python {} init --project {}".format(
            os.path.relpath(__file__, project), project))
        print("VERDICT: CANNOT RUN. Exiting 2 rather than 0, because a missing contract "
              "is the absence of a standard, not a passing one.")
        return 2
    if not git("rev-parse --git-dir", project):
        print("VERDICT: CANNOT RUN. {} is not a git repository, and every freshness check "
              "here is anchored to a commit.".format(project))
        return 2

    sha, dirty, fp = tree_fingerprint(project)
    declared = contract.get("domains") or {}
    # DOMAINS is the floor, not the ceiling. A project may declare more, and until
    # this line existed the extra ones were read from the contract and then
    # dropped, so a repository could carry a check that only ever ran as text.
    # Extras can add failures and can never remove one, which is why widening the
    # list here does not reopen the "declare three easy domains" hole the fixed
    # list closes.
    extra = [k for k in declared if k not in DOMAINS]
    known = DOMAINS + extra
    if args.domain and args.domain not in known:
        print("no domain called {} here. This contract has: {}".format(
            args.domain, ", ".join(known)))
        print("VERDICT: CANNOT RUN. Exiting 2 rather than reporting the typo as an "
              "uncovered domain, which would read as a real gap.")
        return 2
    todo = [args.domain] if args.domain else known

    print("ship gate: {}".format(contract.get("project") or os.path.basename(project)))
    print("  commit {}{}   tree {}".format(sha[:12], "  (dirty)" if dirty else "", fp))
    print("")

    results = []
    for name in todo:
        if args.verbose:
            print("  [{}]".format(name), file=sys.stderr)
        domain_started = time.monotonic()
        result = eval_domain(name, declared.get(name), project, contract, args.verbose)
        result["seconds"] = round(time.monotonic() - domain_started, 1)
        results.append(result)

    width = max(len(r["domain"]) for r in results)
    blocking = []
    for r in results:
        print("  {:<{w}}  {}".format(r["domain"], r["status"], w=width))
        for line in r["evidence"].splitlines():
            print("      " + line)
        print("")
        required = (declared.get(r["domain"]) or {}).get("required")
        if required is None:
            # A domain the contract went out of its way to declare is required
            # unless it says otherwise in as many words. The alternative default
            # makes writing a check and having its failure ignored the quiet path.
            required = r["domain"] in ALWAYS_REQUIRED or r["domain"] not in DOMAINS
        if required and r["status"] in (FAIL, UNCOVERED):
            blocking.append(r)

    ok = not blocking
    verdict = "PASS" if ok else "FAIL"
    print("VERDICT: {}".format(verdict))
    if blocking:
        print("  blocking: {}".format(", ".join(
            "{} {}".format(r["domain"], r["status"]) for r in blocking)))
        print("  A done-claim is not available until each of those either passes or carries "
              "a waiver with a reason and an expiry date.")
    unconfirmed = [r["domain"] for r in results if r.get("confirmed") == "unmeasurable"]
    if unconfirmed:
        print("  waiver(s) not confirmed here: {}. Their checks could not measure on this "
              "host, so this verdict says less than one from a host that can."
              .format(", ".join(unconfirmed)))
    if args.domain:
        print("  Only the {} domain ran. This is not a gate pass; the other {} domains were "
              "not measured.".format(args.domain, len(DOMAINS) - 1))

    record = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "project": os.path.basename(project), "project_path": project,
        "commit": sha, "dirty": dirty, "fingerprint": fp,
        "partial": bool(args.domain),
        "verdict": verdict if not args.domain else "PARTIAL",
        "domains": {r["domain"]: r["status"] for r in results},
        "blocking": [r["domain"] for r in blocking],
        # A waiver the run could not confirm is recorded by name. Without this the
        # ledger writes WAIVED for a confirmed waiver and for one whose confirmation
        # never ran, and a CI PASS reads as identical to a local PASS that asserted
        # more. That is the same class as the run this feature was built to catch,
        # one level up: the record claiming more than the run measured.
        "waivers_unconfirmed": [r["domain"] for r in results
                                if r.get("confirmed") == "unmeasurable"],
        # Same principle for unwaived domains whose command exited CANNOT_MEASURE:
        # their NA is a fact about this host, not about the domain, and a PASS row
        # that hides which checks never measured claims more than the run did.
        "unmeasured": [r["domain"] for r in results if r.get("unmeasured")],
        # How long the run took, and per domain. Added 2026-08-08 because the
        # contract already carries a duration budget that nothing could check.
        # The unit domain's _timeout_note raised the timeout 300 to 900 on
        # 2026-07-31 and wrote its own falsifier: "if the suite passes 600s this
        # number is hiding growth again and the split is overdue." The 8571 rows
        # recorded before this line have no duration in them, so that falsifier
        # could not be evaluated against a single one of them. A budget with a
        # falsifier nobody can run is the same disabled check as a waiver whose
        # confirmation never fires, one field short.
        "duration_seconds": round(time.monotonic() - started, 1),
        "domain_seconds": {r["domain"]: r["seconds"] for r in results
                           if r.get("seconds") is not None},
    }
    ledger = os.path.join(setup_root(), LEDGER)
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    print("  recorded in {}".format(os.path.relpath(ledger, setup_root())))

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"record": record, "results": results}, fh, indent=1)

    return 0 if ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    project = os.path.abspath(args.project)
    path = os.path.join(project, CONTRACT_NAME)
    if os.path.exists(path) and not args.force:
        print("{} already exists. Pass --force to overwrite it.".format(path))
        return 1
    c = starter_contract(project)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(c, fh, indent=2)
    print("wrote " + path)
    st = detect_stack(project)
    print("detected: runner={} node={} python={} scripts={}".format(
        st["runner"], st["node"], st["python"], ",".join(st["scripts"][:10]) or "-"))
    gaps = [k for k, v in c["domains"].items() if v.get("uncovered_note")]
    if gaps:
        print("\nThese domains have no command yet and will report UNCOVERED, which fails "
              "the gate:")
        for g in gaps:
            print("  {:<10} {}".format(g, c["domains"][g]["uncovered_note"]))
        print("That is intentional. Fill them in rather than deleting them.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    project = os.path.abspath(args.project)
    ledger = os.path.join(setup_root(), LEDGER)
    if not os.path.exists(ledger):
        print("no gate run has ever been recorded ({} does not exist)".format(
            os.path.relpath(ledger, setup_root())))
        return 1
    sha, dirty, fp = tree_fingerprint(project)
    rows = []
    with open(ledger, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("project_path") == project or r.get("project") == os.path.basename(project):
                rows.append(r)
    if not rows:
        print("no gate run recorded for {}".format(project))
        return 1
    last = rows[-1]
    print("last run  {}  verdict {}  commit {}  tree {}".format(
        last["ts"], last["verdict"], str(last["commit"])[:12], last["fingerprint"]))
    print("current tree {}{}".format(fp, "  (dirty)" if dirty else ""))
    current = [r for r in rows if r.get("fingerprint") == fp and not r.get("partial")]
    green = [r for r in current if r.get("verdict") == "PASS"]
    if green:
        print("VERDICT: this exact tree has a full green gate run at {}".format(green[-1]["ts"]))
        return 0
    if current:
        print("VERDICT: this tree has been gated and it FAILED on {}".format(
            ", ".join(current[-1].get("blocking") or [])))
        return 1
    print("VERDICT: this tree has never been gated. The {} recorded run(s) are against "
          "other trees and say nothing about the current one.".format(len(rows)))
    return 1


def cmd_selftest(args: argparse.Namespace) -> int:
    """Prove the gate fails an unconfigured project and the waiver logic holds."""
    import tempfile
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        run("git init -q .", td)
        run('git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base', td)
        open(os.path.join(td, "app.py"), "w").write("print('hi')\n")

        # 1. no contract at all
        args1 = argparse.Namespace(project=td, domain=None, verbose=False, json=None)
        got = cmd_run(args1)
        ok = got == 2
        print("\n[{}] no contract exits 2, got {}".format("ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        # 2. starter contract fails, because a starter contract is not a standard met
        cmd_init(argparse.Namespace(project=td, force=True))
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] starter contract fails the gate, got {}".format(
            "ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        # 3. an expired waiver is a failure, not a skip
        c = load_contract(td)
        for d in DOMAINS:
            c["domains"][d] = {"required": True,
                               "waived": {"reason": "selftest", "until": "2099-01-01"}}
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 0
        print("\n[{}] all-waived contract passes while the waivers are live, got {}".format(
            "ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        c["domains"]["e2e"] = {"required": True,
                               "waived": {"reason": "selftest", "until": "2020-01-01"}}
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] an expired waiver fails rather than skips, got {}".format(
            "ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        # 3b. a live waiver carrying a confirm string is checked against the domain's
        # own command, so a waiver that stopped describing its measurement fails on
        # the day it stops rather than on its expiry date.
        for d in DOMAINS:
            c["domains"][d] = {"required": True,
                               "waived": {"reason": "selftest", "until": "2099-01-01"}}
        c["domains"]["e2e"] = {
            "required": True,
            "cmd": "echo DRIFT: 29; exit 1",
            "waived": {"reason": "selftest", "until": "2099-01-01",
                       "confirm": "DRIFT: 51"}}
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        # These three print [FAIL] rather than [MISS] on purpose: mutate.py reads
        # lines starting with [FAIL] to name which check caught a mutation, so a
        # case that fails under any other marker is caught by exit code alone and
        # reports WEAK SIGNAL.
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] a live waiver whose confirm string no longer appears fails, got {}"
              .format("ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1

        # ...and the same waiver passes while its confirm string still holds, which is
        # what keeps this from being a check that simply fails every waiver.
        c["domains"]["e2e"]["waived"]["confirm"] = "DRIFT: 29"
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 0
        print("\n[{}] a confirmed waiver still passes, on a command that exits non-zero, got {}"
              .format("ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1

        # ...and a confirm string the domain gives no way to produce is a contract
        # error, not a pass. Without this case, deleting the domain's cmd is the
        # cheapest way to make the confirmation unrunnable and therefore satisfied.
        del c["domains"]["e2e"]["cmd"]
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] a confirm string with no command to produce it fails, got {}"
              .format("ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1
        c["domains"]["e2e"]["cmd"] = "echo DRIFT: 29; exit 1"

        # ...and a command that cannot measure on this host is not a stale waiver.
        # Exit 2 is the convention; the confirm string is deliberately absent from
        # the output here, which is exactly the shape that failed CI on 2026-08-07.
        c["domains"]["e2e"]["cmd"] = "echo cannot run: no live tree; exit 2"
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        # The same shape on a PLAIN domain (no waiver): unmeasurable-here must
        # read NA, not FAIL. This is the 2026-08-12 CI red: the skills waiver was
        # removed on a locally-CLEAN check and skills_sync's exit-2 "cannot run"
        # on the runner failed every branch. Both signals required; exit 2 with
        # ordinary output stays FAIL (argparse usage errors must not go green).
        c2 = json.loads(json.dumps(c))
        c2["domains"]["e2e"].pop("waived", None)
        json.dump(c2, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 0
        print("\n[{}] an unwaived cannot-measure-here domain is NA, got {}".format(
            "ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1
        c2["domains"]["e2e"]["cmd"] = "echo usage: wrong flag; exit 2"
        json.dump(c2, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] exit 2 without the cannot-run phrase still fails, got {}".format(
            "ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        said = "not confirmed" in out.getvalue()
        ok = got == 0 and said
        print("\n[{}] a confirmation that cannot measure here passes and says so, got {} "
              "said-so {}".format("ok  " if ok else "FAIL", got, said))
        rc |= 0 if ok else 1

        # ...and the run it records names that waiver, so a PASS from a host that
        # could not confirm is distinguishable in the ledger from one that did.
        last = json.loads(open(os.path.join(setup_root(), LEDGER),
                               encoding="utf-8").read().strip().splitlines()[-1])
        ok = last.get("waivers_unconfirmed") == ["e2e"]
        print("\n[{}] the ledger row names the unconfirmed waiver, got {}".format(
            "ok  " if ok else "FAIL", last.get("waivers_unconfirmed")))
        rc |= 0 if ok else 1
        c["domains"]["e2e"]["cmd"] = "echo DRIFT: 29; exit 1"

        # 3c. the same exit-2 convention holds WITHOUT a waiver: a required plain
        # domain whose command cannot measure on this host is N/A with evidence,
        # not FAIL. Added 2026-08-12: with the skills waiver removed because its
        # reason ended, CI (no live ~/.claude) turned red on a domain that was
        # CLEAN everywhere it could be measured, so the only way to keep a
        # satisfied waiver removed was to re-add it, which is the waiver-as-
        # permanent-fixture failure this file exists to prevent.
        c["domains"]["e2e"] = {"required": True,
                               "cmd": "echo cannot run: no live tree; exit 2"}
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        said = "unmeasurable on this host" in out.getvalue()
        ok = got == 0 and said
        print("\n[{}] an unwaived domain that cannot measure here is N/A and says so, "
              "got {} said-so {}".format("ok  " if ok else "FAIL", got, said))
        rc |= 0 if ok else 1

        # ...and exit 2 is not a general escape hatch: exit 1 on the same shape
        # still fails, so a check cannot go green by dying with the right number.
        c["domains"]["e2e"]["cmd"] = "echo broken; exit 1"
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] the same unwaived domain exiting 1 still fails, got {}".format(
            "ok  " if ok else "FAIL", got))
        rc |= 0 if ok else 1
        c["domains"]["e2e"] = {"required": True, "cmd": "echo DRIFT: 29; exit 1",
                               "waived": {"reason": "selftest", "until": "2099-01-01",
                                          "confirm": "DRIFT: 29"}}

        # 4. a domain deleted from the contract is UNCOVERED, not absent
        del c["domains"]["e2e"]
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        got = cmd_run(argparse.Namespace(project=td, domain=None, verbose=False, json=None))
        ok = got == 1
        print("\n[{}] deleting a domain from the contract does not remove it, got {}".format(
            "ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        # 5. the review domain produces its own artifact rather than only complaining
        # that one is missing. A domain whose single possible answer is "no artifact
        # here" gets waived by whoever hits it, so the producer has to run.
        c = load_contract(td)
        c["domains"] = {"review": starter_contract(td)["domains"]["review"]}
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        open(os.path.join(td, "feature.py"), "w").write("def go():\n    return 1\n")
        run("git add -A && git -c user.email=t@t -c user.name=t commit -q -m feature", td)
        got = cmd_run(argparse.Namespace(project=td, domain="review", verbose=False, json=None))
        sha = git("rev-parse HEAD", td)
        art = os.path.join(td, "state", "reviews", "{}.json".format(sha))
        made = os.path.exists(art)
        named = False
        if made:
            with open(art, encoding="utf-8") as fh:
                a = json.load(fh)
            named = a.get("commit") == sha and a.get("reviewer") not in (None, "", "self", "author")
        ok = got == 0 and made and named
        print("\n[{}] the review domain runs its producer and passes on the artifact, got {}"
              .format("ok  " if ok else "MISS", got))
        if not ok:
            print("      artifact_written={} names_commit_and_reviewer={}".format(made, named))
        rc |= 0 if ok else 1

        # ...and a producer that writes nothing must leave the domain red, not green.
        c["domains"]["review"]["cmd"] = "python -c \"pass\""
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        os.remove(art)
        got = cmd_run(argparse.Namespace(project=td, domain="review", verbose=False, json=None))
        ok = got == 1
        print("\n[{}] a producer that writes no artifact leaves review red, got {}".format(
            "ok  " if ok else "MISS", got))
        rc |= 0 if ok else 1

        # ...and an artifact left over from an earlier tree is not a review of this
        # one. The artifact is keyed by commit SHA, so on a dirty tree every edit
        # produces a new tree under the same key and the old review answers for it.
        #
        # Measured 2026-07-25: panel.py's false positives were fixed and the panel
        # passed cleanly when run by hand, while this domain went on reporting the
        # old 7 high findings from an artifact written before the fix. That direction
        # is only a false red and it wastes an hour. The same mechanism run the other
        # way is a false green, where a review written three edits ago is accepted as
        # a review of code nobody has read, which is the failure this domain exists
        # to prevent.
        c["domains"]["review"]["cmd"] = starter_contract(td)["domains"]["review"]["cmd"]
        json.dump(c, open(os.path.join(td, CONTRACT_NAME), "w"), indent=2)
        json.dump({"commit": sha, "reviewer": "earlier-run/local", "verdict": "fail",
                   "summary": "STALEMARK a tree that no longer exists"},
                  open(art, "w", encoding="utf-8"))
        got = cmd_run(argparse.Namespace(project=td, domain="review", verbose=False, json=None))
        with open(art, encoding="utf-8") as fh:
            refreshed = fh.read()
        ok = got == 0 and "STALEMARK" not in refreshed
        print("\n[{}] a leftover artifact is refreshed, not trusted, got {}".format(
            "ok  " if ok else "MISS", got))
        if not ok:
            print("      still_stale={}".format("STALEMARK" in refreshed))
        rc |= 0 if ok else 1

        # 6. the secret scanner sees a planted credential and does not print it
        planted = "AKIA" + "A" * 16
        open(os.path.join(td, "conf.py"), "w").write("KEY = '{}'\n".format(planted))
        run("git add -A", td)
        st, ev = secret_scan(td, {})
        ok = st == FAIL and planted not in ev
        print("\n[{}] secret scan catches a planted key and withholds the value".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} leaked={}".format(st, planted in ev))
        rc |= 0 if ok else 1

        os.remove(os.path.join(td, "conf.py"))
        run("git add -A", td)

        # 7. a vendor's published example is suppressed, and the suppression is
        # visible. Silence would be the bug here: an allowlist nobody can see in
        # the evidence is how a real finding gets buried under a plausible name.
        aws_key = "AKIA" + "IOSFODNN7EXAMPLE"
        aws_secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        vec = os.path.join(td, "vec.py")
        open(vec, "w").write("ACCESS = '{}'\nSECRET = '{}'\n".format(aws_key, aws_secret))
        run("git add -A", td)
        st, ev = secret_scan(td, {})
        ok = st == PASS and "suppressed" in ev and "aws docs example" in ev
        print("\n[{}] a published aws example vector is suppressed and named".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

        # ...and the allowlist must not cover for its neighbours. A real key on
        # the SAME LINE as an example one still has to fire, which is the whole
        # reason the scan re-runs on the line with the example removed rather
        # than skipping the line.
        neighbour = "AKIA" + "B" * 16
        open(vec, "a").write("BOTH = '{}' # near '{}'\n".format(aws_key, neighbour))
        run("git add -A", td)
        st, ev = secret_scan(td, {})
        ok = st == FAIL and neighbour not in ev and "vec.py:3" in ev
        print("\n[{}] a real key sharing a line with an example still fires".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} leaked={} evidence={}".format(
                st, neighbour in ev, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

        # 8. a project can declare its own vector, but only with a reason. No
        # reason means refused, not honoured, because an unexplained allowlist
        # entry and a silenced real finding look exactly the same from here.
        open(vec, "w").write("TOKEN = '{}'\n".format("sk-" + "Z" * 24))
        run("git add -A", td)
        st, ev = secret_scan(td, {}, {"public_vectors": [{"value": "sk-" + "Z" * 24}]})
        ok = st == FAIL and "no `why`" in ev
        print("\n[{}] a contract vector with no reason is refused, not honoured".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

        st, ev = secret_scan(td, {}, {"public_vectors": [
            {"value": "sk-" + "Z" * 24, "why": "rfc example token"}]})
        ok = st == PASS and "rfc example token" in ev
        print("\n[{}] a contract vector with a reason is suppressed and quotes the reason"
              .format("ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

    # 9. Deleting documentation must not read as writing it.
    #
    # Found live on new-recruit 2026-07-25, where the docs domain reported PASS
    # with "documented in: .claude/rules/boundary-contracts.md, ..." while all
    # thirteen of those files were deleted from the working tree. docs_touched
    # builds its file list from `git status --porcelain`, which lists deletions,
    # and then counted any `.md` path as documentation without asking whether it
    # still existed. So the one change guaranteed to leave a reader with less to
    # read was the change that satisfied the check.
    with tempfile.TemporaryDirectory() as td2:
        run("git init -q .", td2)
        open(os.path.join(td2, "README.md"), "w").write("# it\n")
        for n in ("a.py", "b.py", "c.py"):
            open(os.path.join(td2, n), "w").write("x = 1\n")
        run("git add -A", td2)
        run("git -c user.email=t@t -c user.name=t commit -q -m base", td2)

        spec = {"paths": ["README.md", "docs/"], "base": "HEAD"}
        for n in ("a.py", "b.py", "c.py"):
            open(os.path.join(td2, n), "w").write("x = 2\n")
        os.remove(os.path.join(td2, "README.md"))
        st, ev = docs_touched(td2, {}, spec)
        ok = st == FAIL
        print("\n[{}] deleting the only doc does not satisfy the docs domain".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

        # The other half, so the fix cannot be "always fail". A doc that really
        # was edited still counts.
        open(os.path.join(td2, "README.md"), "w").write("# it, and what changed\n")
        st, ev = docs_touched(td2, {}, spec)
        ok = st == PASS and "README.md" in ev
        print("\n[{}] a doc that was really edited still counts".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

        # Third half: a real edit alongside a deletion still passes, but the
        # deletion has to be visible in the evidence. Otherwise the fix trades
        # one silent reading for another.
        os.makedirs(os.path.join(td2, "docs"), exist_ok=True)
        open(os.path.join(td2, "docs", "old.md"), "w").write("# old\n")
        run("git add -A", td2)
        run("git -c user.email=t@t -c user.name=t commit -q -m docs", td2)
        os.remove(os.path.join(td2, "docs", "old.md"))
        # The commit above made README.md clean, so re-edit it: this half is
        # about a live edit sitting beside a deletion, and without the edit
        # there is no live doc and the FAIL would be correct.
        open(os.path.join(td2, "README.md"), "w").write("# it, and old.md is gone\n")
        for n in ("a.py", "b.py", "c.py"):
            open(os.path.join(td2, n), "w").write("x = 3\n")
        st, ev = docs_touched(td2, {}, spec)
        ok = st == PASS and "README.md" in ev and "docs/old.md" in ev and "not counted" in ev
        print("\n[{}] a deletion beside a real edit passes but is named in the evidence"
              .format("ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={}".format(st, ev.replace("\n", " | ")[:300]))
        rc |= 0 if ok else 1

    # 10. A renamed document is still a document.
    #
    # `git status --porcelain` writes a rename as `R  old -> new`, and the old
    # parse took the whole right-hand side as one path. It ends in `.md`, so it
    # counted as documentation, and no such file exists, so under the existence
    # rule above it would now be counted as a deletion and fail the domain. The
    # parse has to split the arrow before either rule can be right.
    with tempfile.TemporaryDirectory() as td3:
        run("git init -q .", td3)
        os.makedirs(os.path.join(td3, "docs"), exist_ok=True)
        open(os.path.join(td3, "docs", "guide.md"), "w").write("# guide\n")
        for n in ("a.py", "b.py", "c.py"):
            open(os.path.join(td3, n), "w").write("x = 1\n")
        run("git add -A", td3)
        run("git -c user.email=t@t -c user.name=t commit -q -m base", td3)

        spec3 = {"paths": ["README.md", "docs/"], "base": "HEAD"}
        run("git mv docs/guide.md docs/handbook.md", td3)
        open(os.path.join(td3, "docs", "handbook.md"), "a").write("and what changed\n")
        for n in ("a.py", "b.py", "c.py"):
            open(os.path.join(td3, n), "w").write("x = 2\n")
        st, ev = docs_touched(td3, {}, spec3)
        ok = st == PASS and "docs/handbook.md" in ev
        print("\n[{}] a renamed doc counts under the name it now has".format(
            "ok  " if ok else "MISS"))
        if not ok:
            print("      status={} evidence={} porcelain={}".format(
                st, ev.replace("\n", " | ")[:300],
                git("status --porcelain", td3).replace("\n", " | ")))
        rc |= 0 if ok else 1

    # expired() decides whether a waiver is still live, and the docstring calls a
    # permanent waiver "a disabled check with better manners". Until 2026-07-27 the
    # only coverage was one whole-gate run with an obviously-past date, so mutation
    # testing walked straight through the two cases that actually bite: a malformed
    # date, and the boundary day itself.
    def check(cond: bool, what: str, detail: str = "") -> None:
        nonlocal rc
        print("\n[{}] {}{}".format("ok  " if cond else "FAIL", what,
                                   "" if cond else "  <- " + detail))
        rc |= 0 if cond else 1

    today = datetime.date.today()
    check(expired((today - datetime.timedelta(days=1)).isoformat()),
          "a waiver that ran out yesterday is expired")
    check(not expired((today + datetime.timedelta(days=1)).isoformat()),
          "a waiver good until tomorrow is live")
    # The boundary is the day it matters: `until` is inclusive, so today is live.
    check(not expired(today.isoformat()),
          "a waiver expiring today is still live on the day itself")
    # Fail CLOSED on garbage. If a malformed date read as live, the cheapest way to
    # disable a domain forever would be to typo the date.
    for bad in ("soon", "", "2026-13-45", "next tuesday", "2026/08/01"):
        check(expired(bad),
              "an unparseable until-date {!r} is treated as EXPIRED, not live".format(bad))

    print("\nVERDICT: {}".format(
        "gate refuses unconfigured and expired-waiver projects, and its scanner works"
        if rc == 0 else "gate selftest has failures above"))
    return rc


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="gate.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the gate")
    r.add_argument("--project", default=".")
    # No choices= here. The valid set is the fixed list plus whatever the
    # contract declares, and argparse cannot see the contract. cmd_run validates
    # the name once it has read one, and names the real options in the error.
    r.add_argument("--domain", help="run one domain only")
    r.add_argument("--json", help="write the full result here")
    r.add_argument("-v", "--verbose", action="store_true")
    r.set_defaults(fn=cmd_run)

    i = sub.add_parser("init", help="write a starter contract")
    i.add_argument("--project", default=".")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_init)

    s = sub.add_parser("status", help="is the current tree gated green")
    s.add_argument("--project", default=".")
    s.set_defaults(fn=cmd_status)

    t = sub.add_parser("selftest")
    t.set_defaults(fn=cmd_selftest)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
