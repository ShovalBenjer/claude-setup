#!/usr/bin/env python3
"""Point-in-time snapshots of the live ~/.claude tree, with a restore path.

WHY THIS EXISTS. tools/deploy writes into ~/.claude, and sync-live-settings.py
writes settings.json in place. The only undo that existed was:

    bak = LIVE + ".bak-pre-bus-sync"
    shutil.copy2(LIVE, bak)

One file, one level deep, FIXED NAME. A second --apply overwrites the only
pristine copy with the already-modified one, so that undo destroys itself the
second time it is used. Every other live-only file under ~/.claude had no undo at
all. This is that undo, for the whole tree, with a new id per take so a second
take can never eat the first.

WHY NOT JUST COMMIT THE LIVE TREE. It holds .credentials.json, a setup token, an
OAuth screenshot, and backups/. Copying the tree into a git-tracked directory puts
those in history, where deleting the file later does not remove them. So the
capture is split along the line where its two halves genuinely differ:

  content  -> state/snapshots/<id>/files/          local only, gitignored
  manifest -> state/snapshots/<id>/manifest.json   git-tracked: paths and hashes

The manifest is the tabular half. It is what proves the shape of the tree at a
moment without carrying the tree, and drift detection needs only the manifest, so
`diff` still works from a fresh clone that has no content at all.

FAIL CLOSED, TWICE. Inclusion is an ALLOWLIST, so a new secret file appearing in
~/.claude is skipped by default instead of captured by default. On top of that,
any file whose bytes match a secret pattern is recorded HASH ONLY: its sha256 goes
in the manifest so drift stays detectable, and its content is never written into
the snapshot. A hash-only entry is not restorable, and restore says so rather than
reporting success over a file it never held.

WHAT THIS DELIBERATELY DOES NOT DO. restore never deletes a live file that
appeared after the snapshot. It names them and leaves them. Deleting under
~/.claude on the strength of a manifest is the kind of convenience that loses work
once and is never trusted again.

  snap.py take --label pre-deploy
  snap.py list
  snap.py verify <id>            # snapshot content still matches its own manifest
  snap.py diff <id>              # live tree now, against that snapshot
  snap.py restore <id>           # dry run, prints what would be written
  snap.py restore <id> --apply   # writes LIVE, after taking a pre-restore snapshot
  snap.py selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
LIVE = Path.home() / ".claude"
SNAPDIR = ROOT / "state" / "snapshots"
SCHEMA = 1

# Top-level files worth capturing. Anything not named here is skipped, which is
# the point: the default for an unrecognised file is OUT.
INCLUDE_FILES = frozenset({
    "CLAUDE.md",
    "settings.json",
    "settings.local.json",
    "mcp.json",
    ".mcp.json",
})

# Directories walked in full. Same rule: a directory not named here is not walked,
# and `take` reports the ones it left alone so coverage is never overstated.
INCLUDE_TREES = frozenset({
    "agents", "skills", "commands", "rules", "hooks", "bin", "output-styles",
})

# The deny checks below win over the include list, and they are load-bearing
# rather than decorative because candidates() offers every top-level file to
# classify(), including the credential files, and lets classify refuse them.
DENY_NAMES = frozenset({
    ".credentials.json", ".setup-token-tmp", ".env", ".comfy-key", ".key",
})
DENY_PARTS = frozenset({
    "backups", ".token-flow", "projects", "todos", "file-history",
    "shell-snapshots", "statsig", "automation-chrome-profile", "__pycache__",
    "node_modules", ".git", "ide", "plugins",
})
DENY_SUFFIXES = frozenset({
    ".key", ".pem", ".pfx", ".p12", ".crt", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".log", ".jsonl", ".db", ".sqlite", ".sqlite3", ".zip", ".gz",
    ".tar", ".pyc", ".exe", ".dll",
})

# Patterns are matched against raw bytes so a binary that slipped past the suffix
# deny list is still scanned. A match makes the entry hash-only; it is never a
# reason to abort the take, because refusing to snapshot anything at all is worse
# than snapshotting most of it and naming the exceptions.
SECRET_PATTERNS: tuple[tuple[str, bytes], ...] = (
    ("private-key-header", rb"-----BEGIN [A-Z ]{0,32}PRIVATE KEY-----"),
    ("anthropic-key", rb"sk-ant-[A-Za-z0-9_\-]{16,}"),
    ("openai-key", rb"sk-[A-Za-z0-9]{32,}"),
    ("github-token", rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("github-pat", rb"github_pat_[A-Za-z0-9_]{20,}"),
    ("aws-access-key-id", rb"AKIA[0-9A-Z]{16}"),
    ("slack-token", rb"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("google-api-key", rb"AIza[0-9A-Za-z_\-]{35}"),
    ("oauth-token-field", rb'"(?:access|refresh)_token"\s*:\s*"[^"]{8,}"'),
    ("client-secret-field", rb'"client_secret"\s*:\s*"[^"]{8,}"'),
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def secret_reason(p: Path) -> str:
    """Name the secret pattern this file matches, or "" when it matches none.

    Returns the pattern NAME, never the matched text: the reason string is written
    into a git-tracked manifest, so it must describe the finding without carrying
    any of it.
    """
    try:
        blob = p.read_bytes()
    except OSError:
        return ""
    for name, pat in SECRET_PATTERNS:
        if re.search(pat, blob):
            return "matched secret pattern " + name
    return ""


def classify(rel: str) -> str:
    """Return "" when this relative path should be captured, else why not."""
    parts = PurePosixPath(rel).parts
    hit = next((p for p in parts if p in DENY_PARTS), "")
    if hit:
        return "denied directory: " + hit
    if parts[-1] in DENY_NAMES:
        return "denied name: " + parts[-1]
    suf = PurePosixPath(rel).suffix.lower()
    if suf in DENY_SUFFIXES:
        return "denied suffix: " + suf
    if rel in INCLUDE_FILES:
        return ""
    if parts[0] in INCLUDE_TREES:
        return ""
    return "not on the include list"


def candidates() -> tuple[list[tuple[str, Path]], list[str]]:
    """Every path offered to classify(), plus the directories left unwalked.

    Top-level files are ALL offered, including the credential files, so the deny
    checks in classify() are exercised by real input rather than sitting there
    untested. Directories are walked only when allowlisted, which is what keeps
    this off projects/ and history and out of a hundred thousand transcript files.
    """
    files: list[tuple[str, Path]] = []
    not_walked: list[str] = []
    if not LIVE.is_dir():
        return files, not_walked
    for child in sorted(LIVE.iterdir()):
        if child.is_file():
            files.append((child.name, child))
        elif child.is_dir():
            if child.name in INCLUDE_TREES:
                for p in sorted(child.rglob("*")):
                    if p.is_file():
                        files.append((p.relative_to(LIVE).as_posix(), p))
            else:
                not_walked.append(child.name)
    return files, not_walked


def entry_for(rel: str, abs_path: Path) -> dict:
    try:
        size = abs_path.stat().st_size
        digest = sha256_file(abs_path)
    except OSError as e:
        return {"path": rel, "size": -1, "sha256": "", "captured": False,
                "reason": "unreadable: " + e.__class__.__name__}
    reason = secret_reason(abs_path)
    return {"path": rel, "size": size, "sha256": digest,
            "captured": not reason, "reason": reason}


def new_id(label: str) -> str:
    """A fresh id per take, never a fixed name.

    The defect this replaces used one fixed filename, so the second run
    overwrote the only pristine copy with the already-modified file. Two takes in
    the same second must therefore still land in two directories.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = stamp + ("-" + re.sub(r"[^A-Za-z0-9._-]+", "-", label) if label else "")
    sid, n = base, 1
    while (SNAPDIR / sid).exists():
        n += 1
        sid = "{}-{}".format(base, n)
    return sid


def manifest_path(sid: str) -> Path:
    return SNAPDIR / sid / "manifest.json"


def load_manifest(sid: str) -> dict:
    p = manifest_path(sid)
    if not p.is_file():
        raise FileNotFoundError("no snapshot {!r} (looked for {})".format(sid, p))
    return json.loads(p.read_text(encoding="utf-8"))


def do_take(label: str = "", quiet: bool = False) -> str:
    files, not_walked = candidates()
    sid = new_id(label)
    dest_root = SNAPDIR / sid / "files"
    dest_root.mkdir(parents=True, exist_ok=False)

    entries, skipped, holdback = [], [], []
    for rel, abs_path in files:
        why = classify(rel)
        if why:
            skipped.append((rel, why))
            continue
        e = entry_for(rel, abs_path)
        entries.append(e)
        if e["captured"]:
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_path, dest)
        else:
            holdback.append((rel, e["reason"]))

    man = {
        "schema": SCHEMA,
        "id": sid,
        "label": label,
        "taken_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "live_root": LIVE.as_posix(),
        "not_walked": not_walked,
        "skipped_count": len(skipped),
        "entries": entries,
    }
    manifest_path(sid).write_text(
        json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not quiet:
        kept = sum(1 for e in entries if e["captured"])
        print("snapshot {}".format(sid))
        print("  captured {} file(s) under {}".format(kept, (SNAPDIR / sid / "files")))
        print("  manifest {}".format(manifest_path(sid)))
        for rel, why in holdback:
            print("  HASH ONLY  {}  ({}) - content deliberately not copied"
                  .format(rel, why))
        print("  skipped {} path(s) not on the include list or denied"
              .format(len(skipped)))
        if not_walked:
            print("  did NOT walk {} top-level dir(s): {}"
                  .format(len(not_walked), ", ".join(not_walked)))
    return sid


def cmd_take(a: argparse.Namespace) -> int:
    do_take(a.label or "")
    return 0


def cmd_list(_a: argparse.Namespace) -> int:
    if not SNAPDIR.is_dir():
        print("no snapshots yet ({} does not exist)".format(SNAPDIR))
        return 0
    rows = sorted(p.parent.name for p in SNAPDIR.glob("*/manifest.json"))
    if not rows:
        print("no snapshots yet under {}".format(SNAPDIR))
        return 0
    for sid in rows:
        try:
            man = load_manifest(sid)
        except (OSError, json.JSONDecodeError) as e:
            print("{}  UNREADABLE MANIFEST ({})".format(sid, e.__class__.__name__))
            continue
        kept = sum(1 for e in man.get("entries", []) if e.get("captured"))
        hashed = sum(1 for e in man.get("entries", []) if not e.get("captured"))
        print("{}  {} captured, {} hash-only, taken {}{}".format(
            sid, kept, hashed, man.get("taken_utc", "?"),
            "  label={}".format(man["label"]) if man.get("label") else ""))
    print("{} snapshot(s)".format(len(rows)))
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    """Is this snapshot still intact, and is it still allowed to hold what it holds.

    Integrity is the obvious half: a captured file that changed or vanished, and a
    hash-only entry whose content somehow got written into the snapshot after all.
    That last one is a leak, so it is a failure here rather than a curiosity.

    Policy is the half that a manifest-only check misses, and it asks the question
    from the other direction, against the bytes on disk rather than against what the
    take recorded at the time:

      ORPHAN     content in the snapshot that its own manifest never mentions, so
                 nothing about it was ever classified or hashed.
      NOWDENIED  an entry the CURRENT deny lists would refuse. Deny lists grow as
                 the live tree grows, and an old snapshot does not retroactively
                 become compliant, so a snapshot taken under the looser policy has
                 to surface rather than sit there passing.
      SECRET     a captured file whose bytes match a secret pattern on re-scan. The
                 take already asked this, which is exactly why asking again is worth
                 something: it catches a take whose filter was wrong, or a pattern
                 added since. The pattern NAME is printed, never the match.
    """
    man = load_manifest(a.id)
    root = SNAPDIR / a.id / "files"
    bad = []
    for e in man.get("entries", []):
        p = root / e["path"]
        if e.get("captured"):
            if not p.is_file():
                bad.append("MISSING   " + e["path"])
            elif sha256_file(p) != e["sha256"]:
                bad.append("CHANGED   " + e["path"])
        elif p.exists():
            bad.append("LEAKED    {} (hash-only entry has content in the snapshot)"
                       .format(e["path"]))
        why = classify(e["path"])
        if why:
            bad.append("NOWDENIED {} ({} under the current deny lists)"
                       .format(e["path"], why))

    known = {e["path"] for e in man.get("entries", [])}
    on_disk = sorted(p.relative_to(root).as_posix()
                     for p in root.rglob("*") if p.is_file()) if root.is_dir() else []
    for rel in on_disk:
        if rel not in known:
            bad.append("ORPHAN    {} (in the snapshot, absent from its manifest)"
                       .format(rel))
        reason = secret_reason(root / rel)
        if reason:
            bad.append("SECRET    {} ({})".format(rel, reason))

    kept = sum(1 for e in man.get("entries", []) if e.get("captured"))
    for line in bad:
        print("  " + line)
    print("snapshot {}: {} captured entr(ies), {} file(s) on disk, {} problem(s)"
          .format(a.id, kept, len(on_disk), len(bad)))
    return 1 if bad else 0


def compare_to_live(man: dict) -> dict:
    """Classify every path as unchanged, changed, gone, hash-only, or added."""
    by_path = {e["path"]: e for e in man.get("entries", [])}
    out: dict[str, list[str]] = {"unchanged": [], "changed": [], "gone": [],
                                 "hash_only": [], "added": []}
    for rel, e in sorted(by_path.items()):
        live = LIVE / rel
        if not live.is_file():
            out["gone"].append(rel)
            continue
        same = sha256_file(live) == e["sha256"]
        if not e.get("captured"):
            # Still comparable: the hash was recorded even though the bytes were
            # not, which is the whole reason for recording it.
            out["hash_only" if same else "changed"].append(rel)
        else:
            out["unchanged" if same else "changed"].append(rel)
    for rel, _abs in candidates()[0]:
        if not classify(rel) and rel not in by_path:
            out["added"].append(rel)
    return out


def cmd_diff(a: argparse.Namespace) -> int:
    man = load_manifest(a.id)
    d = compare_to_live(man)
    for bucket in ("changed", "gone", "added"):
        for rel in d[bucket]:
            print("  {:<9} {}".format(bucket.upper(), rel))
    drift = len(d["changed"]) + len(d["gone"]) + len(d["added"])
    print("live vs {}: {} unchanged, {} changed, {} gone, {} added, {} hash-only "
          "and unchanged".format(a.id, len(d["unchanged"]), len(d["changed"]),
                                 len(d["gone"]), len(d["added"]),
                                 len(d["hash_only"])))
    if a.fail_on_drift and drift:
        return 1
    return 0


def cmd_restore(a: argparse.Namespace) -> int:
    man = load_manifest(a.id)
    root = SNAPDIR / a.id / "files"
    d = compare_to_live(man)
    by_path = {e["path"]: e for e in man.get("entries", [])}

    writes = [r for r in d["changed"] + d["gone"] if by_path[r].get("captured")]
    unrestorable = [r for r in d["changed"] + d["gone"]
                    if not by_path[r].get("captured")]

    for rel in writes:
        print("  WRITE     {}".format(rel))
    for rel in unrestorable:
        print("  CANNOT    {}  (hash-only in this snapshot, content was never "
              "captured)".format(rel))
    for rel in d["added"]:
        print("  LEFT      {}  (appeared after the snapshot; restore never "
              "deletes)".format(rel))

    if not a.apply:
        print("dry run: {} file(s) would be written, {} cannot be restored, "
              "{} left in place. Re-run with --apply.".format(
                  len(writes), len(unrestorable), len(d["added"])))
        return 0

    pre = do_take(label="pre-restore-" + a.id, quiet=True)
    print("  took {} first, so this restore is itself revertable".format(pre))
    for rel in writes:
        dst = LIVE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    print("restored {} file(s) from {}; {} could not be restored; {} left in "
          "place".format(len(writes), a.id, len(unrestorable), len(d["added"])))
    return 1 if unrestorable else 0


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Plant a fake live tree and assert what the snapshot does and does not hold.

    Every case is a property this replaces or protects: the fixed-name overwrite
    that destroyed its own backup, the credential file that must never be copied,
    the drift that must be detectable from the manifest alone, and the negative
    cases without which a clean verify would carry no information.
    """
    import io
    import tempfile
    import traceback
    from contextlib import redirect_stdout

    global LIVE, SNAPDIR
    real_live, real_snapdir = LIVE, SNAPDIR
    tmp = Path(tempfile.mkdtemp(prefix="snap-selftest-"))

    failures: list[str] = []
    take_crashes: list[str] = []

    def check(name: str, ok: bool, detail: object = "") -> None:
        """Print one verdict, stringifying detail because it is usually a list.

        This was `"  <- " + detail` with detail typed str, and almost every call
        site below passes sorted(got). The failure branch never ran while the suite
        was green, so under mutation six broken behaviours died on that TypeError
        instead of on a named check: the harness saw a nonzero exit with no [FAIL]
        line and could only report "CRASHED, no check named it". A selftest's
        failure path is the part that has to work.
        """
        print("  [{}] {}{}".format("ok" if ok else "FAIL", name,
                                   "" if ok else "  <- " + str(detail)))
        if not ok:
            failures.append(name)

    def take(label: str) -> str:
        """Take a snapshot, turning a crash into a recorded verdict.

        do_take creates its directory with exist_ok=False on purpose, so a
        regression in new_id's collision loop raises right here. Left unwrapped,
        that exception would abort every check below it and still exit nonzero,
        which tools/audit/mutate.py reads as "caught" with no check naming the
        reason. bus.py shipped exactly that defect twice, and one wrapped call
        site was not enough there: every call site needs this.
        """
        try:
            return do_take(label=label, quiet=True)
        except BaseException:  # noqa: BLE001 - a crash is a verdict in a selftest
            take_crashes.append(traceback.format_exc())
            return ""

    # Built rather than written as a literal so this file does not itself contain
    # a string that a secret scanner would flag.
    fake_secret = b"ghp_" + b"A" * 32

    def fresh_tree() -> None:
        """A live tree with one of every case the classifier has to separate."""
        global LIVE, SNAPDIR
        LIVE = tmp / "live"
        SNAPDIR = tmp / "snaps"
        for p in (LIVE, SNAPDIR):
            shutil.rmtree(p, ignore_errors=True)
        (LIVE / "skills" / "demo").mkdir(parents=True)
        (LIVE / "backups").mkdir(parents=True)
        (LIVE / "projects" / "deep").mkdir(parents=True)
        (LIVE / "hooks").mkdir(parents=True)
        # Denied directory names NESTED inside an allowlisted tree. Without these
        # the DENY_PARTS check is decorative: backups/ and projects/ at the top
        # level are already excluded by not being on the include list, so nothing
        # would ever reach that branch and a regression in it would go unnoticed.
        (LIVE / "skills" / "demo" / "__pycache__").mkdir(parents=True)
        (LIVE / "hooks" / "backups").mkdir(parents=True)
        (LIVE / "bin").mkdir(parents=True)
        # A denied NAME and a denied SUFFIX, both nested inside an allowlisted tree,
        # for the same reason as the directory case above: at the top level each is
        # already excluded for being off the include list, so a top-level fixture
        # leaves both branches of classify() unreachable and their checks decorative.
        # bin/.credentials.json is the one that matters in the real tree.
        (LIVE / "bin" / ".credentials.json").write_text('{"y": 2}', encoding="utf-8")
        (LIVE / "hooks" / ".env").write_text("PLAIN=1\n", encoding="utf-8")
        (LIVE / "hooks" / "oauth.png").write_bytes(b"\x89PNG\r\n")
        (LIVE / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
        (LIVE / "CLAUDE.md").write_text("# contract\n", encoding="utf-8")
        (LIVE / "skills" / "demo" / "SKILL.md").write_text("body\n", encoding="utf-8")
        (LIVE / "skills" / "demo" / "__pycache__" / "junk.txt").write_text(
            "build litter\n", encoding="utf-8")
        (LIVE / "hooks" / "backups" / "old.md").write_text("stale\n", encoding="utf-8")
        (LIVE / "hooks" / "leaky.sh").write_bytes(b"#!/bin/sh\ntoken=" + fake_secret)
        (LIVE / ".credentials.json").write_text('{"x": 1}', encoding="utf-8")
        (LIVE / "backups" / "old.json").write_text("{}", encoding="utf-8")
        (LIVE / "projects" / "deep" / "history.jsonl").write_text("{}\n",
                                                                  encoding="utf-8")
        (LIVE / "oauth.png").write_bytes(b"\x89PNG\r\n")
        (LIVE / "random-notes.txt").write_text("unlisted\n", encoding="utf-8")

    def captured_paths(sid: str) -> set[str]:
        root = SNAPDIR / sid / "files"
        return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}

    def man_of(sid: str) -> dict:
        """The manifest, or {} when there is not one.

        Same reasoning as take() and run(): a missing manifest has to fail a named
        check, not raise past every check below it.
        """
        try:
            return load_manifest(sid)
        except (OSError, ValueError):
            return {}

    def snap_text(sid: str, rel: str) -> str:
        """One captured file as text, or "" when it was never captured."""
        try:
            return (SNAPDIR / sid / "files" / rel).read_text(encoding="utf-8")
        except OSError:
            return ""

    def overwrite_in_snap(sid: str, rel: str, text: str) -> None:
        """Tamper with a snapshot, creating the parent if the take never made it."""
        p = SNAPDIR / sid / "files" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def ns(**kw) -> argparse.Namespace:
        return argparse.Namespace(**kw)

    def run(fn, **kw) -> tuple[int, str]:
        """Call a command, turning a crash into a verdict instead of a dead run.

        bus.py learned this the hard way: an escaping exception aborts every check
        below it while still exiting nonzero, which a mutation harness reads as
        "caught" with nothing naming the reason. A crash here becomes a returned
        traceback tail, so the checks after it still run.
        """
        try:
            with redirect_stdout(io.StringIO()) as buf:
                rc = fn(ns(**kw))
            return rc, buf.getvalue()
        except BaseException:  # noqa: BLE001 - a crash is a verdict in a selftest
            return 99, traceback.format_exc()

    try:
        # --- what a take captures, and what it refuses to -------------------
        fresh_tree()
        sid = take("case one")
        got = captured_paths(sid)

        check("an allowlisted top-level file is captured",
              "settings.json" in got and "CLAUDE.md" in got, sorted(got))
        check("a file inside an allowlisted tree is captured",
              "skills/demo/SKILL.md" in got, sorted(got))
        check("a denied name is never captured",
              ".credentials.json" not in got
              and "bin/.credentials.json" not in got
              and "hooks/.env" not in got, sorted(got))
        check("a denied directory is never walked",
              not any(p.startswith(("backups/", "projects/")) for p in got),
              sorted(got))
        check("a denied directory nested inside an allowlisted tree is excluded",
              "skills/demo/__pycache__/junk.txt" not in got
              and "hooks/backups/old.md" not in got, sorted(got))
        check("a denied suffix is never captured",
              "oauth.png" not in got and "hooks/oauth.png" not in got, sorted(got))
        check("a top-level file that is not on the include list is skipped",
              "random-notes.txt" not in got, sorted(got))
        check("the take reports the directories it chose not to walk",
              set(man_of(sid).get("not_walked") or []) >= {"backups", "projects"},
              man_of(sid).get("not_walked"))

        # --- the secret in an otherwise capturable file ---------------------
        man = man_of(sid)
        leaky = next((e for e in man.get("entries") or []
                      if e["path"] == "hooks/leaky.sh"), None)
        check("a file matching a secret pattern is recorded hash-only",
              leaky is not None and not leaky["captured"] and bool(leaky["sha256"]),
              str(leaky))
        check("the hash-only reason names the pattern, not the secret",
              leaky is not None and "github-token" in leaky["reason"]
              and fake_secret.decode() not in leaky["reason"], str(leaky))
        blobs = b"".join(p.read_bytes()
                         for p in (SNAPDIR / sid).rglob("*") if p.is_file())
        check("the secret's bytes appear nowhere under the snapshot directory",
              fake_secret not in blobs, "found the planted secret in the snapshot")
        check("a clean file is NOT flagged as secret-bearing",
              not secret_reason(LIVE / "CLAUDE.md"),
              "the flagger fires on everything, so a flag carries no information")

        # --- the defect this whole tool replaces ---------------------------
        second = take("case one")
        check("a second take with the same label gets its own id",
              bool(second) and second != sid and not take_crashes
              and (SNAPDIR / sid / "manifest.json").is_file(),
              "second={!r} crashes={} first_manifest_exists={}".format(
                  second, len(take_crashes),
                  (SNAPDIR / sid / "manifest.json").is_file()))
        check("the first snapshot's content survives the second take",
              snap_text(sid, "settings.json") == '{"hooks": {}}',
              "a fixed-name backup would have been overwritten here")

        # do_take's exist_ok=False is a second guard sitting behind new_id, and
        # new_id normally makes it unreachable, which is exactly how an unreachable
        # guard rots. Stub the id generator so the guard itself is under test: two
        # processes can compute the same id within one second, and the loser has to
        # refuse rather than write into the winner's directory.
        real_new_id = globals()["new_id"]
        globals()["new_id"] = lambda _label="": "fixed-id-collision-probe"
        try:
            probe = take("collide")
            refused = False
            try:
                do_take(label="collide", quiet=True)
            except FileExistsError:
                refused = True
        finally:
            globals()["new_id"] = real_new_id
        check("a take refuses to write into a snapshot directory that already exists",
              bool(probe) and refused,
              "probe={!r} refused={}".format(probe, refused))

        # --- verify, and the negative cases that make a pass mean something --
        rc, _ = run(cmd_verify, id=sid)
        check("verify passes on a snapshot nobody has touched", rc == 0, "rc=" + str(rc))
        tampered = take("tamper")
        overwrite_in_snap(tampered, "settings.json", '{"hooks": {"evil": 1}}')
        rc, out = run(cmd_verify, id=tampered)
        check("verify FAILS when a captured file was edited in the snapshot",
              rc == 1 and "CHANGED" in out, "rc={} out={}".format(rc, out[-200:]))
        (SNAPDIR / tampered / "files" / "settings.json").unlink(missing_ok=True)
        rc, out = run(cmd_verify, id=tampered)
        check("verify FAILS when a captured file vanished from the snapshot",
              rc == 1 and "MISSING" in out, "rc={} out={}".format(rc, out[-200:]))
        leak = take("leak")
        (SNAPDIR / leak / "files" / "hooks").mkdir(parents=True, exist_ok=True)
        (SNAPDIR / leak / "files" / "hooks" / "leaky.sh").write_bytes(fake_secret)
        rc, out = run(cmd_verify, id=leak)
        check("verify FAILS when a hash-only entry's content leaked into the snapshot",
              rc == 1 and "LEAKED" in out, "rc={} out={}".format(rc, out[-200:]))

        # --- the policy half of verify, asked against the bytes on disk ------
        orphan = take("orphan")
        (SNAPDIR / orphan / "files" / "smuggled.md").write_text("no entry\n",
                                                                encoding="utf-8")
        rc, out = run(cmd_verify, id=orphan)
        check("verify FAILS on snapshot content its own manifest never mentions",
              rc == 1 and "ORPHAN" in out, "rc={} out={}".format(rc, out[-200:]))
        planted = take("secret-later")
        overwrite_in_snap(planted, "CLAUDE.md",
                          "# contract\ntoken=" + fake_secret.decode() + "\n")
        rc, out = run(cmd_verify, id=planted)
        check("verify FAILS when a captured file's bytes match a secret on re-scan",
              rc == 1 and "SECRET" in out, "rc={} out={}".format(rc, out[-200:]))
        # A snapshot taken while the deny lists were looser. Written by hand because
        # a take under the current lists cannot produce one, which is the point: the
        # only way this state arises is policy moving after the fact.
        drifted = take("policy-drift")
        denied_body = "PLAIN=1\n"
        overwrite_in_snap(drifted, "hooks/.env", denied_body)
        mp = manifest_path(drifted)
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["entries"].append({
            "path": "hooks/.env", "size": len(denied_body), "captured": True,
            "sha256": sha256_file(SNAPDIR / drifted / "files" / "hooks" / ".env"),
            "reason": ""})
        mp.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        rc, out = run(cmd_verify, id=drifted)
        check("verify FAILS on an entry the current deny lists would now refuse",
              rc == 1 and "NOWDENIED" in out, "rc={} out={}".format(rc, out[-200:]))

        # --- drift detection, from the manifest alone ----------------------
        fresh_tree()
        base = take("drift")
        rc, out = run(cmd_diff, id=base, fail_on_drift=True)
        check("diff reports no drift immediately after a take",
              rc == 0 and "0 changed, 0 gone, 0 added" in out,
              "rc={} out={}".format(rc, out[-260:]))
        (LIVE / "CLAUDE.md").write_text("# contract, edited\n", encoding="utf-8")
        rc, out = run(cmd_diff, id=base, fail_on_drift=True)
        check("diff detects a live file that changed", rc == 1 and "CHANGED" in out,
              "rc={} out={}".format(rc, out[-260:]))
        (LIVE / "skills" / "demo" / "SKILL.md").unlink()
        rc, out = run(cmd_diff, id=base, fail_on_drift=True)
        check("diff detects a live file that disappeared", rc == 1 and "GONE" in out,
              "rc={} out={}".format(rc, out[-260:]))
        (LIVE / "rules").mkdir(exist_ok=True)
        (LIVE / "rules" / "new.md").write_text("new\n", encoding="utf-8")
        rc, out = run(cmd_diff, id=base, fail_on_drift=True)
        check("diff detects a live file that appeared after the snapshot",
              rc == 1 and "ADDED" in out, "rc={} out={}".format(rc, out[-260:]))
        rc, _ = run(cmd_diff, id=base, fail_on_drift=False)
        check("diff without --fail-on-drift reports drift and still exits 0",
              rc == 0, "rc=" + str(rc))
        (LIVE / "hooks" / "leaky.sh").write_bytes(b"#!/bin/sh\ntoken=" + fake_secret
                                                  + b"B")
        rc, out = run(cmd_diff, id=base, fail_on_drift=True)
        check("a hash-only file that changes is still detected as drift",
              rc == 1 and "hooks/leaky.sh" in out, "rc={} out={}".format(rc, out[-260:]))

        # --- restore -------------------------------------------------------
        fresh_tree()
        rid = take("restore")
        (LIVE / "CLAUDE.md").write_text("# clobbered\n", encoding="utf-8")
        rc, out = run(cmd_restore, id=rid, apply=False)
        check("a dry-run restore writes nothing",
              rc == 0 and (LIVE / "CLAUDE.md").read_text(
                  encoding="utf-8") == "# clobbered\n" and "WRITE" in out,
              "rc={} out={}".format(rc, out[-260:]))
        before = sorted(p.parent.name for p in SNAPDIR.glob("*/manifest.json"))
        rc, out = run(cmd_restore, id=rid, apply=True)
        check("--apply puts the snapshot's content back",
              (LIVE / "CLAUDE.md").read_text(encoding="utf-8") == "# contract\n",
              "rc={} out={}".format(rc, out[-260:]))
        after = sorted(p.parent.name for p in SNAPDIR.glob("*/manifest.json"))
        check("--apply takes a pre-restore snapshot first, so a restore is revertable",
              len(after) == len(before) + 1
              and any("pre-restore" in s for s in set(after) - set(before)),
              "before={} after={}".format(before, after))
        (LIVE / "extra.md").write_text("appeared later\n", encoding="utf-8")
        (LIVE / "rules").mkdir(exist_ok=True)
        (LIVE / "rules" / "late.md").write_text("appeared later\n", encoding="utf-8")
        rc, out = run(cmd_restore, id=rid, apply=True)
        check("restore never deletes a file that appeared after the snapshot",
              (LIVE / "rules" / "late.md").is_file() and "LEFT" in out,
              "rc={} out={}".format(rc, out[-300:]))
        (LIVE / "hooks" / "leaky.sh").write_bytes(b"#!/bin/sh\nchanged")
        rc, out = run(cmd_restore, id=rid, apply=True)
        check("restore refuses to claim success over a hash-only entry",
              rc == 1 and "CANNOT" in out, "rc={} out={}".format(rc, out[-300:]))
        check("a hash-only entry is not resurrected from thin air",
              (LIVE / "hooks" / "leaky.sh").read_bytes() == b"#!/bin/sh\nchanged",
              "restore invented content it never had")

        # --- the manifest is the git-tracked half, so it must stay readable --
        man = man_of(rid)
        check("the manifest is JSON with a schema version and a live root",
              man.get("schema") == SCHEMA and bool(man.get("live_root"))
              and isinstance(man.get("entries"), list), sorted(man))
        rc, out = run(cmd_list)
        check("list names every snapshot it can see",
              rc == 0 and out.count("captured") >= len(after),
              "rc={} out={}".format(rc, out[-300:]))
        rc, out = run(cmd_verify, id="no-such-snapshot")
        check("an unknown snapshot id is an error, not a quiet pass",
              rc != 0, "rc={} out={}".format(rc, out[-200:]))
        check("no take raised anywhere in this run", not take_crashes,
              take_crashes[-1].strip().splitlines()[-1] if take_crashes else "")
    finally:
        LIVE, SNAPDIR = real_live, real_snapdir
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("FAILED {}: {}".format(len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="snap.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("take")
    t.add_argument("--label", help="short tag folded into the snapshot id")
    t.set_defaults(func=cmd_take)

    ls = sub.add_parser("list")
    ls.set_defaults(func=cmd_list)

    v = sub.add_parser("verify")
    v.add_argument("id")
    v.set_defaults(func=cmd_verify)

    d = sub.add_parser("diff")
    d.add_argument("id")
    d.add_argument("--fail-on-drift", dest="fail_on_drift", action="store_true",
                   help="exit 1 when the live tree has moved (for a verifier)")
    d.set_defaults(func=cmd_diff)

    r = sub.add_parser("restore")
    r.add_argument("id")
    r.add_argument("--apply", action="store_true", help="write LIVE (dry run without)")
    r.set_defaults(func=cmd_restore)

    s = sub.add_parser("selftest")
    s.set_defaults(func=cmd_selftest)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
