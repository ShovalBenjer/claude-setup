#!/usr/bin/env python3
"""Find the parts of this setup that only look like they exist.

WHY THIS EXISTS

Three hooks in dot-claude/hooks are 45-byte files whose entire content is a
Linux path that does not exist on this machine. `dot-claude/skills/ponytail` is
not a directory, it is a 37-byte file containing a path. `coverage-enforcer`'s
SKILL.md tells the reader its companion hook lives at
~/.codex/hooks/coverage-enforcer.sh, which is also not there. None of that
announces itself: a hook that cannot run fails open, a skill that is a path
just never gets loaded, and a document that names a dead path reads exactly like
a document that names a live one.

That is the same failure the ship gate exists for, one level down. The gate
stops an agent from claiming an app works when nothing measured it. This stops
the setup from claiming a check is wired when the file behind it is a path to
nowhere.

WHAT IT CLASSIFIES, AND WHY THE SEVERITIES DIFFER

  wired-missing   settings.json runs this hook and the file is not there.
  wired-hollow    settings.json runs this hook and the file is a pointer, so
                  the interpreter will read a path as a script. This is the
                  worst case, because the wiring looks complete.
  pointer         a file whose whole content is an absolute path that does not
                  resolve. Not currently wired to anything, so nothing is
                  silently failing, but the skill or hook it stands for is
                  absent and anybody reading the directory listing will believe
                  it is present.
  doc-ref         a document names an absolute path under a config tree that
                  does not exist. Lowest severity because a stale sentence
                  misleads a reader without breaking a run.

WHAT IT DOES NOT DO

It does not reconstruct anything. A pointer file records that content once
existed somewhere else; what that content was is not recoverable from the
pointer, and writing a plausible replacement would be inventing a file and
calling it a repair. The output is a decision list for a human: delete, or
rebuild deliberately.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

HIGH, MED, LOW = "high", "medium", "low"
SEV_ORDER = {HIGH: 3, MED: 2, LOW: 1}

# A file that is nothing but one absolute path. Posix, msys (/c/Users/...), a
# tilde form, or a Windows drive path. No shell metacharacters and no argument
# looking token, because `/usr/bin/env python3 x.py` is a script, not a pointer.
POINTER_LINE = re.compile(r"^(?:/[^\r\n]+|~[/\\][^\r\n]+|[A-Za-z]:[\\/][^\r\n]+)$")
ARGISH = re.compile(r"\s-{1,2}\w|[|<>*?$`]")

# Paths worth reporting when a document names them: the config trees this setup
# actually wires. A generic /usr/bin or /tmp reference is not a wiring claim.
CONFIG_REF = re.compile(
    r"(?<![\w/\\.-])(?:~[/\\]\.(?:claude|codex|agents)[^\s`'\"),;:\]]*"
    r"|/home/[\w.-]+/[^\s`'\"),;:\]]*"
    r"|/c/Users/[\w.-]+/[^\s`'\"),;:\]]*"
    r"|[A-Za-z]:[\\/]Users[\\/][\w.-]+[\\/]\.(?:claude|codex|agents)[^\s`'\"),;:\]]*)")

DOC_EXT = (".md", ".markdown", ".txt")
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".next",
             "state", ".venv", "venv"}
# A file whose subject is dead paths contains dead paths. Reading itself is not
# a finding, it is the same self-reference trap every scanner has.
SELF = re.compile(r"(?i)(^|[/\\])tools[/\\]audit[/\\]")


def win(path: str) -> str:
    """Best-effort local form of a path written for another shell.

    msys writes C:\\Users as /c/Users and the git-bash hooks in settings.json use
    that form, so testing it literally on Windows reports a live hook as missing.
    A /home/... path gets no translation on purpose: it is genuinely absent here,
    and pretending otherwise is what let these files sit for months.

    The reverse direction was missing until 2026-07-31 and it cost twelve false
    HIGH findings. Read from WSL, every hook in `dot-claude/settings.json` reported
    `wired-missing`, because that file is the committed copy of a WINDOWS ~/.claude
    and its `C:\\Users\\shova\\...` paths were tested against the Linux filesystem.
    All twelve exist under /mnt/c; checked by hand before this was changed. A missing
    hook is a believable defect, so twelve of them read as rot rather than as a bug
    in the reader, `pointers scan` exits FAIL on them, and the genuinely dead
    pointers in the same report sit underneath.

    Translation happens only where the drive is actually MOUNTED, which is the whole
    safety property: on bare Linux `C:\\Users\\x` stays unreachable, because a
    translator that rewrites unconditionally is a machine for making absent paths
    look present. See tools/lib/hostpaths.py.
    """
    p = path.strip().strip('"').strip("'")
    if p.startswith("~"):
        p = os.path.expanduser(p)
    m = re.match(r"^/([A-Za-z])/(.*)$", p)
    if m and os.name == "nt":
        return "{}:\\{}".format(m.group(1).upper(), m.group(2).replace("/", "\\"))
    if os.name != "nt":
        return str(_hostpaths().translate(p))
    return p


def _hostpaths():
    """Imported by path rather than by name: tools/ is not a package, and this is
    the same directory-shaped import the rest of this tree uses."""
    global _HOSTPATHS
    if _HOSTPATHS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hostpaths", os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "lib", "hostpaths.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _HOSTPATHS = mod
    return _HOSTPATHS


_HOSTPATHS = None


def exists(path: str) -> bool:
    p = win(path)
    if not p or re.search(r"[*?]", p):
        return False
    try:
        return os.path.exists(p)
    except (OSError, ValueError):
        return False


def read_head(path: str, limit: int = 600) -> str | None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(limit + 1)
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")


def pointer_target(path: str) -> str | None:
    """The path this file consists of, or None if it is a real file.

    Deliberately strict: one line, absolute, no metacharacters, small. A large
    file that happens to start with a path is a script.
    """
    try:
        if os.path.getsize(path) > 400:
            return None
    except OSError:
        return None
    text = read_head(path)
    if text is None:
        return None
    body = text.strip()
    if not body or body.startswith("#!") or "\n" in body:
        return None
    if ARGISH.search(body) or not POINTER_LINE.match(body):
        return None
    if not re.search(r"[/\\]", body):
        return None
    # `/usr/bin/env python3 x.py` is an absolute path followed by arguments, and
    # the dash check above does not see it because it has no flags. A path may
    # legitimately contain spaces (C:\Program Files\Git\bin\bash.exe), so the
    # discriminator is not whitespace itself: it is a whitespace-separated token
    # with no separator in it, which is an argument rather than a path segment.
    tokens = body.split()
    if len(tokens) > 1 and any(not re.search(r"[/\\]", t) for t in tokens[1:]):
        return None
    return body


def walk(root: str) -> list[str]:
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            out.append(os.path.join(base, name))
    return out


def hook_paths(settings: dict) -> list[tuple[str, str]]:
    """Every (event, path) a settings.json would execute.

    The command may be the interpreter (`python`, git-bash) with the script in
    args, so both are candidates and anything that does not look like a path is
    dropped. Missing that distinction would report `python` as a missing hook.
    """
    out: list[tuple[str, str]] = []
    for event, groups in (settings.get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in (group or {}).get("hooks") or []:
                cands = []
                cmd = hook.get("command")
                if isinstance(cmd, str):
                    cands.append(cmd)
                for a in hook.get("args") or []:
                    if isinstance(a, str):
                        cands.append(a)
                for c in cands:
                    if not re.search(r"[/\\]", c):
                        continue          # bare interpreter name, resolved on PATH
                    if c.startswith("-"):
                        continue
                    out.append((event, c))
    return out


def scan(roots: list[str], settings_files: list[str]) -> list[dict]:
    findings: list[dict] = []

    # 1. the wiring. Highest value: a hook the runtime will actually invoke.
    for sf in settings_files:
        if not os.path.exists(sf):
            continue
        try:
            with open(sf, encoding="utf-8", errors="replace") as fh:
                settings = json.load(fh)
        except (OSError, ValueError) as exc:
            findings.append({"kind": "settings-unreadable", "severity": HIGH,
                             "file": sf, "target": "", "note": str(exc)[:160]})
            continue
        for event, path in hook_paths(settings):
            local = win(path)
            if not os.path.exists(local):
                findings.append({
                    "kind": "wired-missing", "severity": HIGH, "file": sf,
                    "target": path,
                    "note": "{} hook: no file at {}".format(event, local)})
                continue
            tgt = pointer_target(local)
            if tgt is not None:
                findings.append({
                    "kind": "wired-hollow", "severity": HIGH, "file": local,
                    "target": tgt,
                    "note": ("{} hook exists but its whole content is a path to {}, "
                             "which {} exist".format(
                                 event, tgt, "does" if exists(tgt) else "does not"))})

    # 2. pointer files anywhere in the trees.
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path in walk(root):
            rel = os.path.relpath(path).replace("\\", "/")
            if SELF.search(rel):
                continue
            tgt = pointer_target(path)
            if tgt is None:
                continue
            if exists(tgt):
                continue          # a live pointer is a redirect, not a hole
            same = os.path.basename(win(tgt)) == os.path.basename(path)
            findings.append({
                "kind": "pointer", "severity": MED, "file": rel, "target": tgt,
                "note": ("whole file is a path to nowhere"
                         + ("; basename matches, so this was a link that got "
                            "flattened" if same else ""))})

    # 3. documents naming config paths that are not there.
    pointer_files = {f["file"] for f in findings if f["kind"] == "pointer"}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for path in walk(root):
            rel = os.path.relpath(path).replace("\\", "/")
            if SELF.search(rel) or rel in pointer_files:
                continue
            if not path.lower().endswith(DOC_EXT):
                continue
            text = read_head(path, 400_000)
            if not text:
                continue
            seen = set()
            for lineno, line in enumerate(text.splitlines(), 1):
                for ref in CONFIG_REF.findall(line):
                    ref = ref.rstrip(".,:;)")
                    if ref in seen or exists(ref):
                        continue
                    seen.add(ref)
                    findings.append({
                        "kind": "doc-ref", "severity": LOW,
                        "file": "{}:{}".format(rel, lineno), "target": ref,
                        "note": "document names a path that is not on this machine"})
    findings.sort(key=lambda f: (-SEV_ORDER[f["severity"]], f["kind"], f["file"]))
    return findings


def normalize(target: str) -> str:
    """Collapse the spellings of one home directory into `~`.

    The same missing script appears as ~/.claude/bin/work-item.sh in one document
    and /home/shovalbe/.claude/bin/work-item.sh in another. Counted separately
    they look like two small problems; counted together they are 40 references to
    one absent file, which is the number that decides whether to write it or
    delete the references.
    """
    t = target.replace("\\", "/")
    t = re.sub(r"^/home/[\w.-]+/", "~/", t)
    t = re.sub(r"(?i)^/c/Users/[\w.-]+/", "~/", t)
    t = re.sub(r"(?i)^[A-Za-z]:/Users/[\w.-]+/", "~/", t)
    return t


def report(findings: list[dict], out_path: str | None) -> None:
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("severity\tkind\tfile\ttarget\tnote\n")
            for f in findings:
                fh.write("\t".join([f["severity"], f["kind"], f["file"],
                                    f["target"], f["note"]]) + "\n")
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    for kind in ("settings-unreadable", "wired-missing", "wired-hollow", "pointer",
                 "doc-ref"):
        if kind in counts:
            print("  {:<18} {}".format(kind, counts[kind]))
    for f in findings:
        if f["severity"] == HIGH:
            print("  [{}] {}  {}".format(f["severity"], f["file"], f["note"]))

    groups: dict[str, int] = {}
    for f in findings:
        if f["kind"] == "doc-ref":
            key = normalize(f["target"])
            groups[key] = groups.get(key, 0) + 1
    top = sorted(groups.items(), key=lambda kv: -kv[1])[:8]
    if top:
        print("\n  most-referenced absent paths ({} distinct):".format(len(groups)))
        for key, n in top:
            print("    {:>3}x  {}".format(n, key))

    if out_path:
        print("\nfull list: {} ({} row(s))".format(out_path, len(findings)))


def cmd_scan(a: argparse.Namespace) -> int:
    root = os.path.abspath(a.project)
    roots = [os.path.join(root, r) for r in (a.tree or
             ["dot-claude", "dot-codex", "dot-agents"])]
    settings = list(a.settings or [])
    if not settings:
        settings = [os.path.join(root, "dot-claude", "settings.json")]
        if a.include_live:
            settings.append(os.path.join(os.path.expanduser("~"), ".claude",
                                         "settings.json"))
    findings = scan(roots, settings)
    print("scanned {} tree(s) and {} settings file(s)".format(
        len([r for r in roots if os.path.isdir(r)]),
        len([s for s in settings if os.path.exists(s)])))

    # A POINTER INTO THE LIVE HOME IS UNANSWERABLE WHERE THERE IS NO LIVE HOME.
    # Added 2026-08-05, the same day the `rules` domain was fixed for the identical
    # reason and one hour before this domain repeated it. On a GitHub runner this
    # scan reported 304 distinct absent paths, headed by `~/.claude/bin/work-item.sh`
    # at 40 references and `~/.claude/rules/gastown-company-registry.md` at 6, every
    # one of which resolves on the operator's machine. That is L-2026-07-31-g:
    # a host-shaped question that is correct on the host it was written on and
    # answers something else entirely on the other.
    #
    # The split is by ANSWERABILITY, not by severity. A pointer at a path inside the
    # repository is checkable anywhere and stays blocking. A pointer into ~ is
    # demoted to a reported observation when ~/.claude is absent, and the demotion is
    # printed, because a domain that quietly stops checking half of its subject is
    # worse than one that fails.
    # Keyed on settings.json rather than on the DIRECTORY existing. First attempt
    # tested `isdir(~/.claude)` and CI still failed, because something on the
    # runner creates that directory: an empty or near-empty ~/.claude satisfied the
    # guard while containing none of the files the pointers reference, which is the
    # worst of both readings. A DEPLOYED live tree has a settings.json; a runner
    # that merely has the folder does not.
    live_home = os.path.isfile(os.path.join(os.path.expanduser("~"), ".claude",
                                            "settings.json"))
    if not live_home:
        home_prefix = os.path.expanduser("~") + os.sep
        # Deferral goes through normalize(), not the raw string. A pointer written
        # as /home/shov/.claude/... names the same unanswerable live home as one
        # written ~/.claude/..., and on a runner it starts with neither "~/" nor
        # the runner's own home prefix, so the raw test let it through to FAIL.
        # That was the residual red on PR #37 after the first two hardenings
        # (bus msg 1785935801-ef3acc, run 31008726876).
        deferred = [f for f in findings
                    if str(f.get("target", "")).startswith(("~/", home_prefix))
                    or normalize(str(f.get("target", ""))).startswith("~/")]
        if deferred:
            print("\n  SKIP {} finding(s) pointing into the live home: no ~/.claude on this "
                  "host, so their absence is a fact about the runner and not about the "
                  "repository. Repo-internal pointers below still block."
                  .format(len(deferred)))
            findings = [f for f in findings if f not in deferred]

    # Print what remains AFTER the deferral, because the verdict is computed over
    # exactly this list. Before this call existed, CI printed "scanned 3 trees"
    # and "VERDICT: FAIL" with nothing in between: a red nobody could act on.
    report(findings, a.out)

    worst = max([SEV_ORDER[f["severity"]] for f in findings], default=0)
    threshold = SEV_ORDER[a.fail_on]
    verdict = "PASS" if worst < threshold else "FAIL"
    print("\nVERDICT: {} (fail-on={})".format(verdict, a.fail_on))
    return 0 if verdict == "PASS" else 1


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Plant one of each kind, plus the things that must not be reported."""
    rc = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal rc
        print("  {}  {}".format("ok  " if ok else "MISS", label))
        if detail and not ok:
            print("        " + detail[:400])
        if not ok:
            rc = 1

    with tempfile.TemporaryDirectory() as td:
        tree = os.path.join(td, "dot-claude")
        os.makedirs(os.path.join(tree, "hooks"))
        live = os.path.join(td, "real-target.sh")
        open(live, "w").write("#!/bin/sh\necho alive\n")

        p = lambda *x: os.path.join(tree, *x)
        # must be reported
        open(p("hooks", "hollow.sh"), "w").write("/home/nobody/hooks/hollow.sh\n")
        open(p("hooks", "orphan.sh"), "w").write("/home/nobody/hooks/orphan.sh\n")
        open(p("doc.md"), "w").write(
            "Run the companion hook at ~/.codex/hooks/definitely-not-here.sh first.\n")
        # must NOT be reported
        open(p("hooks", "real.sh"), "w").write("#!/bin/sh\necho hi\n")
        open(p("hooks", "oneline.sh"), "w").write("/usr/bin/env python3 x.py\n")
        open(p("redirect.sh"), "w").write(live + "\n")
        open(p("ok.md"), "w").write("The live one is at {}\n".format(live))

        settings = os.path.join(td, "settings.json")
        json.dump({"hooks": {
            "Stop": [{"hooks": [
                {"type": "command", "command": "python",
                 "args": [p("hooks", "hollow.sh")]},
                {"type": "command", "command": "python",
                 "args": [p("hooks", "real.sh")]},
                {"type": "command", "command": "python",
                 "args": [p("hooks", "gone.py")]}]}],
            "Notification": [{"hooks": [
                {"type": "command", "command": "powershell.exe",
                 "args": ["-NoProfile", "-File", p("hooks", "real.sh")]}]}]}},
            open(settings, "w"))

        found = scan([tree], [settings])
        by_kind: dict[str, list[dict]] = {}
        for f in found:
            by_kind.setdefault(f["kind"], []).append(f)
        tgts = {f["target"] for f in found}

        check("a wired hook that is a path is wired-hollow",
              any("hollow.sh" in f["target"] for f in by_kind.get("wired-hollow", [])),
              json.dumps(found, indent=1))
        check("a wired hook with no file is wired-missing",
              any("gone.py" in f["target"] for f in by_kind.get("wired-missing", [])),
              json.dumps(by_kind.get("wired-missing", []), indent=1))
        check("an unwired pointer file is reported at medium",
              any("orphan.sh" in f["target"] and f["severity"] == MED
                  for f in by_kind.get("pointer", [])),
              json.dumps(by_kind.get("pointer", []), indent=1))
        check("a flattened link is named as one",
              any("basename matches" in f["note"] for f in by_kind.get("pointer", [])),
              json.dumps(by_kind.get("pointer", []), indent=1))
        check("a doc naming a dead config path is reported at low",
              any("definitely-not-here" in f["target"] and f["severity"] == LOW
                  for f in by_kind.get("doc-ref", [])),
              json.dumps(by_kind.get("doc-ref", []), indent=1))

        # the false positives that would make this tool unreadable
        check("a real script is not a pointer",
              not any("real.sh" in t for t in tgts if t), sorted(tgts))
        check("a one-line command with arguments is not a pointer",
              not any(f["file"].endswith("oneline.sh")
                      for f in by_kind.get("pointer", [])),
              json.dumps(by_kind.get("pointer", []), indent=1))
        check("a pointer whose target exists is a redirect, not a hole",
              not any(f["file"].endswith("redirect.sh")
                      for f in by_kind.get("pointer", [])),
              json.dumps(by_kind.get("pointer", []), indent=1))
        check("a doc naming a live path is not reported",
              not any(f["file"].startswith("ok.md")
                      for f in by_kind.get("doc-ref", [])),
              json.dumps(by_kind.get("doc-ref", []), indent=1))
        check("a hook exists so it is not reported twice",
              len([f for f in found if f["file"].endswith("real.sh")]) == 0,
              json.dumps(found, indent=1))

        # severity gating has to be a real gate, not a label
        args = argparse.Namespace(project=td, tree=[tree], settings=[settings],
                                  include_live=False, out=None, fail_on=HIGH)
        check("high findings fail the scan", cmd_scan(args) == 1)
        no_wiring = os.path.join(td, "empty-settings.json")
        json.dump({"hooks": {}}, open(no_wiring, "w"))
        args = argparse.Namespace(project=td, tree=[tree], settings=[no_wiring],
                                  include_live=False, out=None, fail_on=HIGH)
        check("pointers alone do not fail a high-only scan", cmd_scan(args) == 0)
        args.fail_on = MED
        check("pointers alone do fail a medium scan", cmd_scan(args) == 1)

    print("\nVERDICT: {}".format(
        "hollow wiring is detected and real files are left alone" if rc == 0
        else "selftest has failures above"))
    return rc


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="classify pointers, wiring and stale doc paths")
    s.add_argument("--project", default=".")
    s.add_argument("--tree", action="append", help="directory to scan; repeatable")
    s.add_argument("--settings", action="append", help="settings.json to check")
    s.add_argument("--include-live", action="store_true",
                   help="also check ~/.claude/settings.json wiring")
    s.add_argument("--out", default=None, help="write the full TSV here")
    s.add_argument("--fail-on", choices=[HIGH, MED, LOW], default=HIGH)
    s.set_defaults(func=cmd_scan)

    t = sub.add_parser("selftest", help="prove the classifier on planted files")
    t.set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
