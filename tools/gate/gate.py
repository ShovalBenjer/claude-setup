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
  security    no credential material in the change, dependency audit if the
              stack has one
  docs        the change is described where a reader would look: README or docs
              for behaviour, CHANGELOG for the fact it changed
  pipeline    CI runs these same checks, so local-green cannot diverge from
              merged-green
  review      an independent reviewer looked at THIS commit and said so in an
              artifact; self-assessment does not satisfy this
  perf        only when the contract sets a budget; otherwise not applicable
              with that reason printed

WAIVERS EXPIRE

A waiver needs a reason and an until-date. An expired waiver is a failure, not a
skip, because a permanent waiver is just a disabled check with better manners.

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
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

CONTRACT_NAME = "quality-contract.json"
LEDGER = os.path.join("state", "gate-runs.jsonl")

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

def run(cmd: str, cwd: str, timeout: int = 900) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8",
                           errors="replace")
        return p.returncode, ((p.stdout or "") + (p.stderr or ""))
    except subprocess.TimeoutExpired:
        return 124, "timed out after {}s: {}".format(timeout, cmd)
    except Exception as exc:
        return 127, "could not run: {}".format(exc)


def git(args: str, cwd: str) -> str:
    rc, out = run("git " + args, cwd, timeout=60)
    return out.strip() if rc == 0 else ""


def tree_fingerprint(cwd: str) -> tuple[str, bool, str]:
    """Commit, dirty flag, and a hash of the working tree's tracked content.

    The fingerprint is what makes a green run non-reusable. Without it an agent
    can pass the gate, make three more edits, and cite the earlier pass; the
    fingerprint changes the moment the tree does, so the Stop hook can tell.
    """
    sha = git("rev-parse HEAD", cwd) or "no-commit"
    status = git("status --porcelain", cwd)
    dirty = bool(status.strip())
    h = hashlib.sha256()
    h.update(sha.encode())
    # git diff of tracked files plus the names of untracked ones: enough to
    # notice any edit, cheap enough to run on every gate invocation.
    h.update(git("diff HEAD", cwd).encode("utf-8", "replace"))
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


BUILTINS = {
    "secret_scan": secret_scan,
    "docs_touched": docs_touched,
    "ci_runs_gate": ci_runs_gate,
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
        else:
            out["status"] = WAIVED
            out["evidence"] = "waived until {}: {}".format(until, reason)
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
        # artifact, run it once and re-read. The verdict still comes from the
        # artifact, never from the command's exit code, because a reviewer that
        # approves by exiting zero is not a reviewer.
        if st == UNCOVERED and spec.get("cmd"):
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
    out["status"] = PASS if rc == 0 else FAIL
    out["evidence"] = "exit {} from `{}`\n{}".format(rc, cmd, indent(tail))
    return out


def indent(text: str, pad: str = "    ") -> str:
    return "\n".join(pad + l for l in text.splitlines()) if text else pad + "(no output)"


def cmd_run(args: argparse.Namespace) -> int:
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
    todo = [args.domain] if args.domain else DOMAINS

    print("ship gate: {}".format(contract.get("project") or os.path.basename(project)))
    print("  commit {}{}   tree {}".format(sha[:12], "  (dirty)" if dirty else "", fp))
    print("")

    results = []
    for name in todo:
        if args.verbose:
            print("  [{}]".format(name), file=sys.stderr)
        results.append(eval_domain(name, declared.get(name), project, contract, args.verbose))

    width = max(len(r["domain"]) for r in results)
    blocking = []
    for r in results:
        print("  {:<{w}}  {}".format(r["domain"], r["status"], w=width))
        for line in r["evidence"].splitlines():
            print("      " + line)
        print("")
        required = (declared.get(r["domain"]) or {}).get("required")
        if required is None:
            required = r["domain"] in ALWAYS_REQUIRED
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
    r.add_argument("--domain", choices=DOMAINS, help="run one domain only")
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
