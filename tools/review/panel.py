#!/usr/bin/env python3
"""Persona review panel: domain reviewers over the added lines of a change.

WHY THIS EXISTS

The gate's `review` domain wants an artifact saying somebody other than the
author looked at this commit. Left to a human that step gets skipped, and left to
the author's own model it is worthless, because a model reviewing its own diff
agrees with itself. There is already an external-review harness in this setup
(dot-claude/bin/external-review-judge.py) and both of its backends are shut on
this machine: the codex binary is not installed, and Gemini Free Tier is barred
for this repository's content by the project contract. So the default reviewer
here has to be one that always works and never sends anything anywhere.

WHAT A PERSONA IS HERE

Not a prompt saying "act as a security expert". A persona is a named set of
checks over the lines this change ADDED, each with a pattern, a reason a reader
would accept, and a severity. That is narrower than a human reviewer and it is
honest about being narrower: the artifact records its own coverage boundary, so
"the panel passed" can never be read as "a human would have no objection".

Every finding cites file and line. Every citation is verified against the parsed
diff before it is written out, so a reviewer that invents a location gets its
finding dropped and the drop is recorded. That check exists mostly for the
optional model backend, where invented line numbers are the normal failure.

BACKENDS

  local        (default) deterministic checks, no network, nothing leaves the box
  openrouter   adds a free-model second opinion for what a pattern cannot see.
               Opt-in with --allow-external, and it refuses outright if the diff
               contains anything resembling credential material.

USAGE
  python tools/review/panel.py run --project . [--base origin/main]
  python tools/review/panel.py run --project . --allow-external
  python tools/review/panel.py selftest

The artifact lands at <project>/state/reviews/<sha>.json, which is where
tools/gate/gate.py looks for it.

EXIT CODES
  0  panel reached a pass verdict
  1  panel found blocking issues, or could not reach a verdict
  2  could not run (not a git repo, no change to review)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SETUP = os.path.abspath(os.path.join(HERE, ".."))

HIGH = "high"
MED = "medium"
LOW = "low"


# ------------------------------------------------------------------ diff model

def sh(cmd: str, cwd: str, timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "")
    except Exception as exc:
        return 127, str(exc)


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def default_base(project: str) -> str:
    """A base with something between it and HEAD.

    The obvious loop (take the first of origin/main, main, ...) picks a ref that on
    the main branch IS HEAD, leaving an empty diff and a review domain that can
    never pass on a clean tree. So a candidate that resolves to HEAD is no base at
    all and gets skipped. The last resort is the empty tree, which makes the first
    commit in a repository reviewable instead of unreviewable.
    """
    head = sh("git rev-parse HEAD", project)[1].strip()
    for cand in ("origin/main", "origin/master", "main", "master", "HEAD~1"):
        rc, sha = sh("git rev-parse --verify --quiet " + cand, project)
        if rc != 0 or not sha.strip():
            continue
        if sha.strip() == head:
            continue
        return cand
    return EMPTY_TREE


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(project: str, base: str) -> list[dict]:
    """Every line this change adds, as {file, line, text}.

    Reviewing added lines rather than whole files is the difference between a
    review of the change and a review of the repository. A pre-existing problem
    is a separate conversation and blocking on it would make the gate impossible
    to ever turn on.
    """
    out: list[dict] = []
    # Three-dot against a branch base is what a reviewer wants: changes on this side
    # of the merge base, not changes that landed on main since. The empty tree has no
    # merge base with anything, so it needs the two-dot form.
    span = "{} HEAD".format(base) if base == EMPTY_TREE else "{}...HEAD".format(base)
    cmds = ["git diff -U0 " + span, "git diff -U0 HEAD", "git diff -U0 --cached"]
    seen: set[tuple[str, int]] = set()
    for cmd in cmds:
        rc, diff = sh(cmd, project, timeout=180)
        if rc != 0:
            continue
        path = None
        lineno = 0
        for raw in diff.splitlines():
            if raw.startswith("+++ "):
                p = raw[4:].strip()
                path = None if p == "/dev/null" else re.sub(r"^b/", "", p)
                continue
            m = HUNK.match(raw)
            if m:
                lineno = int(m.group(1))
                continue
            if raw.startswith("+") and not raw.startswith("+++") and path:
                key = (path, lineno)
                if key not in seen:
                    seen.add(key)
                    out.append({"file": path, "line": lineno, "text": raw[1:]})
                lineno += 1

    # Untracked files are part of the change too, and skipping them is how a whole
    # new module gets shipped unreviewed.
    rc, status = sh("git status --porcelain", project)
    if rc == 0:
        for row in status.splitlines():
            if not row.startswith("??"):
                continue
            rel = row[3:].strip().strip('"')
            full = os.path.join(project, rel)
            if os.path.isdir(full):
                for root, _dirs, files in os.walk(full):
                    if re.search(r"[\\/](\.git|node_modules|__pycache__|dist|build)([\\/]|$)", root):
                        continue
                    for f in files:
                        _collect_file(project, os.path.join(root, f), out, seen)
            else:
                _collect_file(project, full, out, seen)
    return out


def _collect_file(project: str, full: str, out: list, seen: set) -> None:
    rel = os.path.relpath(full, project).replace("\\", "/")
    if not re.search(r"\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|swift|rb|php|cs|sql|sh|"
                     r"ps1|yml|yaml|json|css|scss|html|md|toml|env\.example)$", rel):
        return
    try:
        if os.path.getsize(full) > 500_000:
            return
        with open(full, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                key = (rel, i)
                if key not in seen:
                    seen.add(key)
                    out.append({"file": rel, "line": i, "text": line.rstrip("\n")})
    except OSError:
        return


def lang_of(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "ts": "ts", "tsx": "ts", "js": "js", "jsx": "js", "mjs": "js", "cjs": "js",
        "py": "py", "go": "go", "rs": "rs", "java": "java", "kt": "kt", "cs": "cs",
        "rb": "rb", "php": "php", "sql": "sql", "sh": "sh", "ps1": "ps1",
        "css": "css", "scss": "css", "html": "html", "yml": "yaml", "yaml": "yaml",
        "json": "json", "md": "md",
    }.get(ext, ext)


# ------------------------------------------------------------------ the panel
#
# Each entry is (id, severity, langs, pattern, why). `langs` empty means any file.
# `why` is written for the person who has to decide whether to fix it, so it says
# what goes wrong, not which rule was violated.

CODE_LANGS = ["ts", "js", "py", "go", "rs", "java", "kt", "cs", "rb", "php",
              "sql", "sh", "ps1", "css", "html"]

PERSONAS: dict[str, dict] = {
    "security": {
        "owns": "credential exposure, injection surface, transport and access control",
        "checks": [
            ("shell-interpolation", HIGH, ["js", "ts"],
             r"(?:exec|execSync|spawnSync)\s*\(\s*[`\"'][^`\"']*\$\{",
             "a shell command built by string interpolation runs whatever the "
             "interpolated value contains"),
            ("py-shell-true", HIGH, ["py"],
             r"subprocess\.(?:run|call|Popen|check_output)\([^)]*shell\s*=\s*True",
             "shell=True with any non-literal argument is command injection"),
            ("sql-concat", HIGH, [],
             r"(?i)(?:SELECT|INSERT|UPDATE|DELETE)\s+.*(?:\+\s*\w+|\$\{|%\s*\(|%s['\"]\s*%|f['\"])",
             "SQL assembled from variables instead of bound parameters"),
            ("dangerous-html", HIGH, ["js", "ts"],
             r"dangerouslySetInnerHTML|\.innerHTML\s*=\s*[^'\"`]",
             "unsanitized markup insertion is stored XSS if the value ever comes "
             "from a user"),
            ("eval-added", HIGH, [],
             r"(?<![\w.])eval\s*\(|new\s+Function\s*\(",
             "eval executes whatever it is handed"),
            ("tls-off", HIGH, [],
             r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|verify\s*=\s*False|"
             r"rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true",
             "certificate verification disabled, so the connection is not "
             "authenticated"),
            ("cors-wildcard", MED, [],
             r"Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|origin\s*:\s*['\"]\*",
             "a wildcard origin lets any site call this with the user's session"),
            ("http-url", LOW, [],
             r"['\"]http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)",
             "plaintext HTTP to a remote host"),
            ("jwt-unverified", HIGH, ["js", "ts", "py"],
             r"jwt\.decode\((?![^)]*verify)|decode\([^)]*verify_signature['\"]?\s*:\s*False",
             "a token decoded without verifying its signature is attacker-controlled "
             "data, not identity"),
        ],
    },
    "correctness": {
        "owns": "error handling, type escapes, and silently swallowed failure",
        "checks": [
            ("empty-catch", MED, ["js", "ts"],
             r"catch\s*(?:\([^)]*\))?\s*\{\s*\}",
             "an empty catch turns a failure into a wrong result with no trace"),
            ("bare-except-pass", MED, ["py"],
             r"except\s*(?:Exception\s*)?:\s*(?:#.*)?$",
             "a bare except hides the failure it caught, including the ones you did "
             "not anticipate"),
            ("ts-escape", MED, ["ts"],
             r"@ts-(?:ignore|expect-error|nocheck)|\bas\s+any\b|:\s*any\b",
             "a type escape moves the failure from compile time to a user's screen"),
            ("py-type-ignore", LOW, ["py"],
             r"#\s*type:\s*ignore",
             "the typechecker was told to stop looking here"),
            ("float-money", MED, [],
             r"(?i)(?:(?:price|amount|total|balance|cost|salary)\w*\s*:\s*(?:float|number)\b"
             r"|(?:FLOAT|DOUBLE)\s*(?:\(|,|$).*(?:price|amount|total|balance))",
             "binary floating point cannot represent decimal currency exactly"),
            # The first version required `foo.bar.then(`, which cannot cross the
            # parentheses in `save(row).then(...)` — the shape the defect actually
            # takes. It matched nothing for its whole life and the selftest is what
            # said so.
            ("unawaited", MED, ["js", "ts"],
             r"^\s*(?!(?:return|await|void|const|let|var|export|import|yield)\b|[}/*)\]])"
             r"[\w.]+(?:\s*\([^;]*\))?\s*\.(?:then|catch)\s*\(",
             "a promise chain with nothing awaiting it fails after the response is "
             "already sent"),
            ("loose-equality-null", LOW, ["js", "ts"],
             r"==\s*(?:undefined)\b|!=\s*(?:undefined)\b",
             "comparing against undefined with loose equality"),
        ],
    },
    "ux_frontend": {
        "owns": "what a person on a phone actually experiences",
        "checks": [
            ("img-no-alt", MED, ["ts", "js", "html"],
             r"<img(?![^>]*\balt\s*=)[^>]*>",
             "an image with no alt is invisible to a screen reader and to anyone on "
             "a failed load"),
            ("click-on-div", MED, ["ts", "js"],
             r"<(?:div|span)(?![^>]*\brole\s*=)(?![^>]*\btabIndex)[^>]*onClick",
             "a clickable div cannot be reached by keyboard or announced as a control"),
            ("outline-none", MED, ["css"],
             r"outline\s*:\s*(?:none|0)\b",
             "removing the focus ring without replacing it leaves keyboard users with "
             "no idea where they are"),
            ("fixed-px-font", LOW, ["css"],
             r"font-size\s*:\s*(?:[0-9]|1[01])px",
             "text under 12px is not readable on a phone"),
            ("input-no-label", MED, ["ts", "js", "html"],
             r"<input(?![^>]*\b(?:aria-label|aria-labelledby|id)\s*=)[^>]*>",
             "an input with no label and no id to attach one to is unlabelled"),
            # A missing viewport meta is a real mobile defect and it is deliberately
            # not checked here: it is a property of a whole document, and this
            # scanner sees one line at a time, so any per-line pattern for it would
            # fire on every <head> in the repository. tools/e2e/flow.py checks the
            # rendered viewport in a real browser, which is the right instrument.
            ("px-width-large", LOW, ["css"],
             r"(?:min-)?width\s*:\s*(?:[4-9]\d{2}|\d{4,})px",
             "a hard pixel width wider than a phone viewport causes horizontal scroll"),
        ],
    },
    "ops_release": {
        "owns": "what happens after merge: config, noise, and half-landed changes",
        "checks": [
            ("debug-left", LOW, ["js", "ts"],
             r"console\.(?:log|debug|dir)\s*\(",
             "debug output left in shipped code"),
            ("py-print-debug", LOW, ["py"],
             r"^\s*print\s*\(\s*(?:f?['\"](?:DEBUG|TODO|XXX|here|test)|\w+\s*\))",
             "debug print left in shipped code"),
            ("test-only", HIGH, ["js", "ts"],
             r"\b(?:describe|it|test)\.only\s*\(",
             "a .only silently skips every other test in the file, so a green suite "
             "means almost nothing"),
            # `xit\(` without the boundary matched the tail of `SystemExit(` and
            # `sys.exit(`, which reported 50 ordinary Python entry points as
            # disabled tests. The boundary is the whole difference between a signal
            # and noise nobody reads.
            ("test-skipped", MED, ["js", "ts", "py"],
             r"\b(?:describe|it|test)\.skip\s*\(|@(?:pytest\.mark\.)?skip|\bxit\s*\(",
             "a test disabled in the same change that touches its subject"),
            # Scoped to code on purpose. Run unscoped against this repository it
            # returned 296 findings, 294 of them TODO lines inside markdown plans and
            # json state, where a TODO is the content rather than a defect. A
            # reviewer that reports 296 non-problems has taught its reader to skip it.
            ("todo-added", LOW, CODE_LANGS,
             r"(?:^|\s)(?:TODO|FIXME|XXX|HACK)\b",
             "unfinished work marked in the code"),
            ("commented-code", LOW, ["js", "ts", "py"],
             r"^\s*(?://|#)\s*(?:if|for|while|return|const|let|def |class |import )",
             "commented-out code, which future readers cannot tell from live code"),
        ],
    },
    "data": {
        "owns": "schema change safety and query cost",
        "checks": [
            ("select-star", LOW, ["sql", "py", "ts", "js"],
             r"(?i)SELECT\s+\*\s+FROM",
             "SELECT * breaks silently when a column is added and moves more data "
             "than the caller needs"),
            ("drop-in-migration", HIGH, ["sql"],
             r"(?i)\b(?:DROP\s+(?:TABLE|COLUMN)|TRUNCATE)\b",
             "a destructive schema change with no stated recovery path"),
            # `SET[^;]*` used to swallow the WHERE clause it was meant to require,
            # so every correctly-scoped UPDATE was reported as touching every row.
            # The negative lookahead has to reach the end of the statement.
            ("no-where", HIGH, ["sql"],
             r"(?i)^\s*(?:UPDATE|DELETE\s+FROM)\s+[\w.\"`\[\]]+(?![^;]*\bWHERE\b)",
             "an UPDATE or DELETE with no WHERE clause touches every row"),
            # NOT NULL can sit on either side of REFERENCES, so the lookahead has to
            # temper the scan in both directions rather than only looking rightward.
            # This sees the single-line column form only; a multi-line CREATE TABLE
            # is past what a line-level check can decide.
            ("nullable-fk", LOW, ["sql"],
             r"(?i)^(?:(?!NOT\s+NULL).)*REFERENCES\s+\w+\s*\([^)]*\)(?:(?!NOT\s+NULL).)*$",
             "a nullable foreign key permits orphan rows, on the single-line column "
             "form this check can actually see"),
        ],
    },
}

# Findings inside these paths are noise: a test may legitimately use eval, and a
# lockfile or vendored bundle is not hand-written code.
EXEMPT = re.compile(
    r"(?i)(^|/)(?:tests?|__tests__|spec|fixtures?|mocks?|vendor|node_modules|dist|build|"
    r"\.next|migrations?/archive)/|"
    r"(?:\.min\.(?:js|css)|\.lock|lock\.json|-lock\.yaml|\.map|\.snap)$")

# A pattern's own definition contains the thing it looks for, so a file that IS a
# scanner trips every check in it. That is not a finding, it is the tool reading
# itself.
SELF_REFERENTIAL = re.compile(r"(?i)(^|/)(?:tools/(?:review|gate|e2e|refute)/|"
                              r"dot-claude/hooks/)")


def run_local(lines: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for persona, spec in PERSONAS.items():
        for cid, sev, langs, pat, why in spec["checks"]:
            rx = re.compile(pat)
            for ln in lines:
                if EXEMPT.search(ln["file"]) or SELF_REFERENTIAL.search(ln["file"]):
                    continue
                if langs and lang_of(ln["file"]) not in langs:
                    continue
                if not rx.search(ln["text"]):
                    continue
                findings.append({
                    "persona": persona, "check": cid, "severity": sev,
                    "file": ln["file"], "line": ln["line"], "why": why,
                    "snippet": ln["text"].strip()[:160], "source": "local",
                })
    return findings


# ------------------------------------------------------------------ external

def redactable(lines: list[dict]) -> list[str]:
    """Credential-shaped content in the change. Fail closed if any is present."""
    pats = [
        r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"gh[pousr]_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9]{20,}", r"AIza[0-9A-Za-z_\-]{35}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
        r"(?i)\b(?:api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-\.]{16,}['\"]",
    ]
    hits = []
    for ln in lines:
        for p in pats:
            if re.search(p, ln["text"]):
                hits.append("{}:{}".format(ln["file"], ln["line"]))
                break
    return hits


def run_external(lines: list[dict], project: str, verbose: bool) -> tuple[list[dict], str]:
    """A free model reads the change for what a pattern cannot see.

    Returns (findings, note). Any finding whose citation is not a line this change
    actually added is dropped, because an invented file:line is the normal failure
    mode here and an unverifiable finding cannot be acted on.
    """
    leaks = redactable(lines)
    if leaks:
        return [], ("refused to send: the change contains credential-shaped content at {}. "
                    "Nothing was transmitted.".format(", ".join(leaks[:5])))
    sys.path.insert(0, os.path.join(SETUP, "openrouter"))
    try:
        import client as orc  # type: ignore
    except Exception as exc:
        return [], "openrouter client unavailable: {}".format(exc)

    valid = {(l["file"], l["line"]) for l in lines}
    budget = 60_000
    body, used = [], 0
    for l in lines:
        row = "{}:{}: {}".format(l["file"], l["line"], l["text"][:300])
        if used + len(row) > budget:
            break
        body.append(row)
        used += len(row)
    truncated = len(body) < len(lines)

    prompt = (
        "Review these added lines from one change. Report only defects a reader could "
        "act on: a wrong result, a broken flow, a security hole, or a mobile UI that "
        "will not work on a 390px screen. Do not report style. Do not report anything "
        "you cannot point at a specific line for.\n\n"
        "Return JSON only: {\"findings\":[{\"file\":..,\"line\":..,\"severity\":"
        "\"high|medium|low\",\"why\":..}],\"note\":\"what you could not assess\"}\n\n"
        "If the change looks correct, return an empty findings array and say in note "
        "what you checked.\n\n" + "\n".join(body))
    try:
        text, model = orc.chat(prompt, system=(
            "You are a reviewer who did not write this code. Cite a real line number for "
            "every finding. An empty findings array is a valid and common answer."))
    except Exception as exc:
        return [], "external review call failed: {}".format(exc)

    data = orc.extract_json(text) or {}
    raw = data.get("findings") or []
    out, dropped = [], 0
    for f in raw if isinstance(raw, list) else []:
        try:
            fl, li = str(f.get("file")), int(f.get("line"))
        except (TypeError, ValueError):
            dropped += 1
            continue
        if (fl, li) not in valid:
            dropped += 1
            continue
        sev = str(f.get("severity", MED)).lower()
        out.append({"persona": "external", "check": "model-review",
                    "severity": sev if sev in (HIGH, MED, LOW) else MED,
                    "file": fl, "line": li, "why": str(f.get("why", ""))[:400],
                    "snippet": "", "source": "openrouter:{}".format(model)})
    note = "model {} returned {} finding(s), {} dropped for citing a line this change did " \
           "not add. {}{}".format(model, len(out), dropped, str(data.get("note", ""))[:300],
                                  "  Input was truncated at 60k chars." if truncated else "")
    if verbose:
        print("    " + note, file=sys.stderr)
    return out, note


# ------------------------------------------------------------------ verdict

def cmd_run(args: argparse.Namespace) -> int:
    project = os.path.abspath(args.project)
    rc, _ = sh("git rev-parse --git-dir", project)
    if rc != 0:
        print("not a git repository: {}".format(project))
        return 2
    base = args.base or default_base(project)
    sha = sh("git rev-parse HEAD", project)[1].strip() or "no-commit"

    lines = added_lines(project, base)
    if not lines:
        print("no added lines relative to {}, so there is nothing to review".format(base))
        return 2

    files = sorted({l["file"] for l in lines})
    print("persona panel: {} added line(s) across {} file(s), base {}".format(
        len(lines), len(files), base))

    findings = run_local(lines)
    ext_note = "external backend not requested"
    if args.allow_external:
        ext, ext_note = run_external(lines, project, args.verbose)
        findings += ext

    blocking = [f for f in findings if f["severity"] == HIGH]
    med = [f for f in findings if f["severity"] == MED]
    low = [f for f in findings if f["severity"] == LOW]

    by_persona: dict[str, list] = {}
    for f in findings:
        by_persona.setdefault(f["persona"], []).append(f)
    for persona in list(PERSONAS) + (["external"] if args.allow_external else []):
        got = by_persona.get(persona, [])
        owns = PERSONAS.get(persona, {}).get("owns", "what patterns cannot see")
        print("\n  {:<12} {:<24} {}".format(
            persona, owns[:24], "{} finding(s)".format(len(got)) if got else "no finding"))
        for f in sorted(got, key=lambda x: {HIGH: 0, MED: 1, LOW: 2}[x["severity"]])[:12]:
            print("      {:<7} {}:{}  {}".format(f["severity"], f["file"], f["line"], f["check"]))
            print("              {}".format(f["why"]))
            if f["snippet"]:
                print("              > {}".format(f["snippet"]))
        if len(got) > 12:
            print("      ... {} more not printed, all of them are in the artifact".format(
                len(got) - 12))

    fail_at = {"high": [HIGH], "medium": [HIGH, MED], "low": [HIGH, MED, LOW]}[args.fail_on]
    blockers = [f for f in findings if f["severity"] in fail_at]
    verdict = "pass" if not blockers else "changes-requested"

    coverage = (
        "Reviewed {} added line(s) across {} file(s) against {} pattern checks in {} "
        "personas{}. This panel sees added lines only, not pre-existing code, and it sees "
        "syntax, not intent: a wrong algorithm that reads cleanly will pass it. It is not "
        "a substitute for a human reading the diff, and the artifact should not be cited "
        "as one.".format(
            len(lines), len(files),
            sum(len(p["checks"]) for p in PERSONAS.values()), len(PERSONAS),
            " plus one external model pass" if args.allow_external else ""))

    artifact = {
        "commit": sha,
        "base": base,
        "reviewer": "persona-panel/local" + ("+openrouter" if args.allow_external else ""),
        "reviewed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "summary": ("{} high, {} medium, {} low across {} personas".format(
            len(blocking), len(med), len(low), len(by_persona))
            + ("" if verdict == "pass" else "; blocking at --fail-on={}".format(args.fail_on))),
        "coverage_boundary": coverage,
        "external_note": ext_note,
        "counts": {"high": len(blocking), "medium": len(med), "low": len(low)},
        "findings": findings,
        "files": files,
    }
    dest = args.out or os.path.join(project, "state", "reviews", "{}.json".format(sha))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1)

    print("\nVERDICT: {}  ({} high, {} medium, {} low)".format(
        verdict.upper(), len(blocking), len(med), len(low)))
    print("  " + coverage)
    if args.allow_external:
        print("  external: " + ext_note)
    print("  artifact: {}".format(os.path.relpath(dest, project)))
    if sh("git status --porcelain", project)[1].strip():
        print("  note: the tree is dirty, so this artifact describes uncommitted work while "
              "naming commit {}. The gate's review domain wants an artifact for a committed "
              "tree; commit first and rerun.".format(sha[:12]))
    return 0 if verdict == "pass" else 1


def cmd_selftest(args: argparse.Namespace) -> int:
    """Plant one defect per persona and prove each is found, then prove a clean
    change is not decorated with invented findings."""
    import tempfile
    rc = 0
    # One planted line per check in the registry. A check with no positive case is
    # indistinguishable from a check that can never fire, so the assertion below
    # requires every registered check id to appear here.
    planted = {
        "app.ts": [
            "export function q(id: string) {",
            "  return db.query('SELECT * FROM users WHERE id = ' + id);",   # sql-concat
            "}",
            "  execSync(`rm -rf ${dir}`);",                                 # shell-interpolation
            "  el.innerHTML = untrusted;",                                  # dangerous-html
            "  eval(src);",                                                 # eval-added
            "  const a = { rejectUnauthorized: false };",                   # tls-off
            "  const c = { origin: '*' };",                                 # cors-wildcard
            "  fetch(\"http://api.example.com/v1\");",                      # http-url
            "  const who = jwt.decode(token);",                             # jwt-unverified
            "  try { risky(); } catch {}",                                  # empty-catch
            "  const x = y as any;",                                        # ts-escape
            "  let price: number = 0;",                                     # float-money
            "  save(row).then(done);",                                      # unawaited
            "  if (x == undefined) { return; }",                            # loose-equality-null
            "  console.log('debug');",                                      # debug-left
            "  // return 1;",                                               # commented-code
            "  // TODO: handle the empty case",                             # todo-added
            "const bad = <div onClick={go}>press</div>;",                    # click-on-div
            "const pic = <img src=\"/a.png\" />;",                           # img-no-alt
            "const f = <input type=\"text\" />;",                            # input-no-label
            "it.only('one test', () => {});",                               # test-only
            "it.skip('another', () => {});",                                # test-skipped
        ],
        "run.py": [
            "import subprocess  # type: ignore",                            # py-type-ignore
            "def go(cmd):",
            "    subprocess.run(cmd, shell=True)",                          # py-shell-true
            "    requests.get(u, verify=False)",                            # tls-off (py form)
            "    print(\"DEBUG\")",                                         # py-print-debug
            "    try:",
            "        work()",
            "    except:",                                                  # bare-except-pass
            "        pass",
        ],
        "schema.sql": [
            "DROP TABLE users;",                                            # drop-in-migration
            "DELETE FROM sessions;",                                        # no-where
            "CREATE TABLE t (uid int REFERENCES users(id));",               # nullable-fk
            "SELECT * FROM audit;",                                         # select-star
        ],
        "ui.css": [
            "button { outline: none; }",                                    # outline-none
            ".panel { min-width: 1200px; }",                                # px-width-large
            ".tiny { font-size: 10px; }",                                   # fixed-px-font
        ],
    }
    want = [(p, c) for p, spec in PERSONAS.items() for c, *_ in spec["checks"]]
    with tempfile.TemporaryDirectory() as td:
        sh("git init -q .", td)
        sh('git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base', td)
        for name, body in planted.items():
            open(os.path.join(td, name), "w", encoding="utf-8").write("\n".join(body) + "\n")
        lines = added_lines(td, "HEAD")
        found = {(f["persona"], f["check"]) for f in run_local(lines)}
        print("planted change produced {} finding(s) over {} line(s)".format(
            len(run_local(lines)), len(lines)))
        for persona, check in want:
            ok = (persona, check) in found
            print("  {}  {:<12} {}".format("ok  " if ok else "MISS", persona, check))
            rc |= 0 if ok else 1

        # A clean change must produce nothing. A reviewer that always finds
        # something is a reviewer nobody reads, and every false positive here is a
        # line somebody has to defend in review for no reason.
        #
        # The lines below are not hypothetical. Every one of them was flagged by an
        # earlier version of this file when it was pointed at real code: `xit\(`
        # matched the tail of `SystemExit(`, so 50 ordinary Python entry points were
        # reported as disabled tests. A pattern is only as good as the innocent text
        # it has been shown to leave alone.
        for name in planted:
            os.remove(os.path.join(td, name))
        innocent = {
            "clean.ts": [
                "export function add(a: number, b: number): number {",
                "  return a + b;",
                "}",
                "export const Img = () => <img src=\"/x.png\" alt=\"a diagram\" />;",
                "await save(row);",
                "  return save(row).then(done);",
                "    .then(next)",
            ],
            "entry.py": [
                "import sys",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "    sys.exit(main())",
            ],
            "ok.sql": [
                "UPDATE users SET seen = 1 WHERE id = 4;",
                "CREATE TABLE t (uid int NOT NULL REFERENCES users(id));",
            ],
            "ok.css": [
                ".btn:focus-visible { outline: 2px solid var(--ring); }",
                ".card { max-width: 100%; font-size: 1rem; }",
            ],
        }
        for name, body in innocent.items():
            open(os.path.join(td, name), "w", encoding="utf-8").write("\n".join(body) + "\n")
        clean = run_local(added_lines(td, "HEAD"))
        ok = not clean
        print("\n  {}  ordinary code produces no findings".format("ok  " if ok else "MISS"))
        for f in clean:
            print("        false positive: {} {} {}:{}  {}".format(
                f["persona"], f["check"], f["file"], f["line"], f["snippet"]))
        rc |= 0 if ok else 1

        # A base that resolves to HEAD yields an empty diff, which reads as "nothing
        # to review" and quietly makes the review domain unpassable on a clean tree.
        # On the branch being gated that is the common case, not an edge case.
        sh("git add -A && git -c user.email=t@t -c user.name=t commit -q -m clean", td)
        head = sh("git rev-parse HEAD", td)[1].strip()
        base = default_base(td)
        base_sha = sh("git rev-parse " + base, td)[1].strip()
        ok = base_sha != head
        print("  {}  default base on a committed branch is not HEAD itself ({})".format(
            "ok  " if ok else "MISS", base))
        rc |= 0 if ok else 1

        n = len(added_lines(td, base))
        ok = n > 0
        print("  {}  a clean committed tree still has {} line(s) to review".format(
            "ok  " if ok else "MISS", n))
        rc |= 0 if ok else 1

    print("\nVERDICT: {}".format(
        "every planted defect is caught and a clean change passes clean" if rc == 0
        else "panel selftest has failures above"))
    return rc


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="panel.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--project", default=".")
    r.add_argument("--base")
    r.add_argument("--out")
    r.add_argument("--fail-on", choices=("high", "medium", "low"), default="high")
    r.add_argument("--allow-external", action="store_true",
                   help="also send the change to a free OpenRouter model; refuses if the "
                        "change contains credential-shaped content")
    r.add_argument("-v", "--verbose", action="store_true")
    r.set_defaults(fn=cmd_run)
    t = sub.add_parser("selftest")
    t.set_defaults(fn=cmd_selftest)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
