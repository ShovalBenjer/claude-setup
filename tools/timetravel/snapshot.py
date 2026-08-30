#!/usr/bin/env python3
"""Point-in-time reconstruction for the ledgers git never sees.

WHY THIS EXISTS, AND WHAT IT DELIBERATELY DOES NOT DO

`git show <rev>:state/x.jsonl` already reconstructs any TRACKED ledger at any
commit. That is three of Dolt's five features for free, and rebuilding it here
would be pure duplication. This tool is scoped to the complement: bytes that
were never committed, so no revision of anything contains them.

Two disjoint populations land in that complement.

  PERMANENT. Files matched by .gitignore. `state/handback-log.jsonl` (735 rows
  of per-turn stop-hook telemetry, which rules/model-selection.md names as the
  evidence source for the fable falsifier), `state/api-usage.jsonl` (120 rows),
  `state/hook-fires.log` (613), `state/bus-cursors/*.txt`, `state/sessions/`,
  and the cached model catalogues. These are ignored for good reasons that this
  tool does not relitigate: they are machine-local telemetry, and committing
  them would make the gate's own tree fingerprint self-invalidating. The cost
  was already paid once and written down: .gitignore's bus-cursors comment
  records that "a cursor's prior value is then unrecoverable, which is how lane
  B's pre-reset value was already lost on 2026-07-25." That is a measured loss,
  not a hypothetical.

  TRANSIENT. Tracked files whose CURRENT working-tree content differs from
  HEAD. A value that is written, read by the gate, overwritten, and only then
  committed leaves no trace of the intermediate state. This is what happened to
  the `review` waiver in quality-contract.json on 2026-07-30: it read "waived
  until 2026-08-12" early in the session and "until 2026-08-02" later, with a
  different reason, and `git log -p -- quality-contract.json` returns two
  commits, neither of which contains either waiver. Git is not failing here; it
  is answering correctly that it was never told.

Snapshots are content-addressed, so a run over unchanged ledgers writes no new
bytes, only a manifest row proving they were unchanged at that moment. Nothing
is ever mutated: blobs are write-once and the manifest is append-only.

WHAT IS TRACKED AND WHAT IS NOT

Same split state/snapshots/ already uses, for the same reason. `objects/` is
gitignored, because ignored ledgers can carry material that has no business in
a git history and history is exactly where a later delete does not remove it.
`manifest.jsonl` IS tracked: path, size and sha256 prove WHEN a ledger changed
without carrying what it said, so `log` and `changed` survive a fresh clone
while `at --content` needs this machine.

DO NOT WIRE THIS TO A STOP HOOK. Appending to a tracked manifest as a side
effect of ending a turn is precisely the loop that got state/handback-log.jsonl
ignored: the hook fires while reporting a green gate and thereby dirties the
tree the gate just fingerprinted. Run it from a session-start hook, a scheduler,
or by hand.

  python tools/timetravel/snapshot.py snap                capture the current bytes
  python tools/timetravel/snapshot.py at 2026-07-30T12:00 what each ledger said then
  python tools/timetravel/snapshot.py at <when> --path state/api-usage.jsonl --content
  python tools/timetravel/snapshot.py log state/api-usage.jsonl   every distinct version
  python tools/timetravel/snapshot.py changed <from> <to>         what moved in a window
  python tools/timetravel/snapshot.py verify                      blobs match their names
  python tools/timetravel/snapshot.py selftest                    plant a defect per guarantee
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

SCHEMA = 1
STORE = "state/timetravel"
OBJECTS = "objects"
MANIFEST = "manifest.jsonl"
STORE_GITIGNORE = """\
# Snapshot CONTENT stays local, matching state/snapshots/.gitignore and for the
# same reason: these blobs are copies of ledgers that were gitignored in the
# first place, several of them machine-local telemetry, and a git history is
# where a later delete does not remove anything.
#
# manifest.jsonl is tracked ON PURPOSE. path + size + sha256 prove WHEN a ledger
# changed without carrying WHAT it said, so `log` and `changed` answer from a
# fresh clone; only `at --content` needs this machine's objects/.
objects/
"""

# A file this size is a cache, not a ledger, and copying a new copy of it on
# every change would make the store larger than the repository. Recorded with
# its hash and captured=false, so "it changed at 14:00" still answers even
# though "here is what it said" does not.
MAX_BLOB = 4 * 1024 * 1024

# Locks are zero-byte sidecars, __pycache__ is build output, and the two snapshot
# stores must not photograph each other.
SKIP_SUFFIX = (".lock", ".pyc")
SKIP_DIR = ("__pycache__", "state/snapshots", STORE)

# TRACKED files worth watching while they are dirty. Deliberately NOT the whole
# `git diff HEAD` set: on a branch mid-work that is the entire working tree, and
# a tool that copies the working tree is a backup, not a ledger history. The list
# is the files an ORACLE READS AND A SESSION OVERWRITES, which is the class the
# 2026-07-30 waiver incident belongs to. Everything under state/ is included
# whatever its git status, because a ledger that is tracked today can be ignored
# tomorrow and the history should not have a hole at the switch.
TRACKED_WATCH = ("quality-contract.json", "state/")


# ---------------------------------------------------------------- pure helpers

def now_utc() -> str:
    """Millisecond resolution, not seconds.

    Measured 2026-07-30 on the first real run of this tool: two `snap` calls in
    the same shell pipeline both stamped 20:57:38Z, which makes resolve_at's
    ordering arbitrary between them and makes `log` unable to say which content
    came first. Seconds are not enough resolution for a tool whose entire job is
    ordering. Lexical sort still equals chronological sort at this format.
    """
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def next_ts(rows: list[dict], candidate: str) -> str:
    """Never append a row whose ts is not strictly after the previous row's.

    Clock skew, a manual clock change, or two writers in the same millisecond
    would otherwise produce a manifest that cannot be ordered. Rather than
    reject the snapshot, nudge it one millisecond past the last row: the bytes
    are real and worth keeping, only the label is adjusted, and an ordering the
    file cannot express is worse than a timestamp that is 1 ms optimistic.
    """
    if not rows:
        return candidate
    last = max((r.get("ts", "") for r in rows), default="")
    if candidate > last:
        return candidate
    try:
        dt = datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return candidate
    dt += datetime.timedelta(milliseconds=1)
    return dt.isoformat(timespec="milliseconds") + "Z"


def parse_when(text: str) -> str:
    """Normalise an operator-typed instant to the manifest's own ts format.

    Accepts a bare date, a date and time to the minute, seconds, and a trailing
    Z. A bare date means the START of that day, so `at 2026-07-30` answers "what
    did it say when the 30th began", never "at some unstated hour of the 30th".
    """
    s = text.strip().replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1]
    # The tool's own stamps carry milliseconds, so its output must be valid
    # input. Measured 2026-07-30: the first end-to-end run copied a ts out of
    # `log` into `at` and got a ValueError, which makes the two verbs unusable
    # together and is exactly the workflow the tool exists for.
    for fmt, fill in (("%Y-%m-%dT%H:%M:%S.%f", ""),
                      ("%Y-%m-%dT%H:%M:%S", ""),
                      ("%Y-%m-%dT%H:%M", ":00"),
                      ("%Y-%m-%dT%H", ":00:00"),
                      ("%Y-%m-%d", "T00:00:00")):
        try:
            datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
        return s + fill + "Z"
    raise ValueError("cannot read {!r} as an instant; try 2026-07-30T12:00".format(text))


def is_skipped(relpath: str) -> bool:
    p = relpath.replace("\\", "/").lstrip("./")
    if p.endswith(SKIP_SUFFIX):
        return True
    for d in SKIP_DIR:
        if p == d or p.startswith(d + "/") or ("/" + d + "/") in ("/" + p):
            return True
    return False


def blob_relpath(digest: str) -> str:
    """Fan out on the first two hex characters so no directory holds 10k files."""
    return "{}/{}/{}".format(OBJECTS, digest[:2], digest)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_at(rows: list[dict], when: str) -> dict | None:
    """The last snapshot taken at or before `when`.

    Strictly at-or-before, never the nearest. A later snapshot is evidence about
    a later moment, and returning it would answer a question nobody asked with
    bytes that did not exist yet.
    """
    best = None
    for r in rows:
        ts = r.get("ts", "")
        if ts and ts <= when and (best is None or ts > best["ts"]):
            best = r
    return best


def version_log(rows: list[dict], path: str) -> list[dict]:
    """Collapse the manifest to the DISTINCT versions of one path.

    A run over an unchanged file is not a version, it is a confirmation, so it
    extends the previous version's `last_seen` instead of adding a row. Without
    this an hourly snapshotter reports 24 versions a day of a file nobody
    touched, and the log stops meaning anything.
    """
    out: list[dict] = []
    for r in sorted(rows, key=lambda x: x.get("ts", "")):
        ent = (r.get("entries") or {}).get(path)
        if ent is None:
            if out and out[-1].get("digest") is not None:
                out.append({"ts": r.get("ts", ""), "digest": None, "size": 0,
                            "captured": False, "last_seen": r.get("ts", ""),
                            "absent": True})
            continue
        digest = ent.get("sha256")
        if out and out[-1].get("digest") == digest:
            out[-1]["last_seen"] = r.get("ts", "")
            continue
        out.append({"ts": r.get("ts", ""), "digest": digest,
                    "size": ent.get("size", 0),
                    "captured": bool(ent.get("captured")),
                    "last_seen": r.get("ts", ""), "absent": False})
    return out


def changed_between(rows: list[dict], lo: str, hi: str) -> dict[str, tuple]:
    """Paths whose content differs between the snapshots bracketing [lo, hi].

    The lower endpoint is the snapshot in effect AT `lo`, not the first one
    after it, otherwise a change made between `lo` and the next run is invisible
    in the window that contains it.
    """
    a = resolve_at(rows, lo)
    b = resolve_at(rows, hi)
    if b is None:
        return {}
    ae = (a or {}).get("entries") or {}
    be = b.get("entries") or {}
    out = {}
    for p in sorted(set(ae) | set(be)):
        x = (ae.get(p) or {}).get("sha256")
        y = (be.get(p) or {}).get("sha256")
        if x != y:
            out[p] = (x, y)
    return out


# ------------------------------------------------------------------ store i/o

def store_dir(project: str) -> str:
    return os.path.join(project, STORE)


def read_manifest(project: str) -> list[dict]:
    p = os.path.join(store_dir(project), MANIFEST)
    rows: list[dict] = []
    if not os.path.exists(p):
        return rows
    with open(p, "r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print("warn: manifest line {} is not JSON, skipped".format(n),
                      file=sys.stderr)
    return rows


def ensure_store(project: str) -> str:
    d = store_dir(project)
    os.makedirs(os.path.join(d, OBJECTS), exist_ok=True)
    gi = os.path.join(d, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(STORE_GITIGNORE)
    return d


def git_lines(project: str, *args: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", project] + list(args),
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print("warn: git failed ({}); target discovery is incomplete".format(exc),
              file=sys.stderr)
        return []
    if out.returncode != 0:
        print("warn: git exited {}: {}".format(out.returncode, out.stderr.strip()[:200]),
              file=sys.stderr)
        return []
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def in_tracked_watch(relpath: str) -> bool:
    p = relpath.replace("\\", "/")
    return any(p == w or p.startswith(w) for w in TRACKED_WATCH if w.endswith("/")) or \
        p in TRACKED_WATCH


def discover_targets(project: str, all_dirty: bool = False) -> list[str]:
    """Everything under state/ that git will not answer for, derived not listed.

    Derived from git rather than from a hand-kept path list on purpose: a new
    gitignored ledger is covered the day it appears, so a file cannot be born
    exempt. Three populations:

      - ignored files under state/            (permanent: no revision has them)
      - untracked files under state/          (not yet in any revision)
      - tracked files in TRACKED_WATCH that differ from HEAD
        (the intra-session overwrite class, e.g. quality-contract.json)

    `--all-dirty` widens the third population to the whole working tree. Off by
    default because on a branch mid-work that is every file, and copying the
    working tree is a backup rather than a ledger history.
    """
    found: set[str] = set()

    for ln in git_lines(project, "status", "--porcelain", "--ignored", "--", "state"):
        if not ln.startswith(("!!", "??")):
            continue
        found.add(ln[3:].strip().strip('"'))

    # Tracked files that differ from HEAD. These are only unrecoverable while
    # uncommitted, but that is exactly the window in which the gate reads them.
    for p in git_lines(project, "diff", "--name-only", "HEAD"):
        p = p.strip().strip('"')
        if all_dirty or in_tracked_watch(p):
            found.add(p)

    expanded: list[str] = []
    for p in sorted(found):
        full = os.path.join(project, p.replace("/", os.sep))
        if os.path.isdir(full):
            for root, dirs, files in os.walk(full):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), project)
                    expanded.append(rel.replace(os.sep, "/"))
        elif os.path.isfile(full):
            expanded.append(p.rstrip("/"))
    return sorted({p for p in expanded if not is_skipped(p)})


# ------------------------------------------------------------------- commands

def cmd_snap(args) -> int:
    project = args.project
    d = ensure_store(project)
    targets = discover_targets(project, all_dirty=args.all_dirty)
    if not targets:
        print("no uncommitted or ignored files under state/; nothing git cannot answer")
        return 0

    entries: dict[str, dict] = {}
    new_blobs = 0
    reused = 0
    for rel in targets:
        full = os.path.join(project, rel.replace("/", os.sep))
        try:
            data = open(full, "rb").read()
        except OSError as exc:
            entries[rel] = {"sha256": "", "size": 0, "captured": False,
                            "reason": "unreadable: {}".format(exc.__class__.__name__)}
            continue
        digest = sha256_bytes(data)
        rec = {"sha256": digest, "size": len(data), "captured": True, "reason": ""}
        if len(data) > MAX_BLOB:
            rec.update(captured=False, reason="over {} byte cap".format(MAX_BLOB))
        else:
            bp = os.path.join(d, blob_relpath(digest).replace("/", os.sep))
            if os.path.exists(bp):
                reused += 1
            else:
                os.makedirs(os.path.dirname(bp), exist_ok=True)
                # Write-once. A temp file plus replace would still overwrite; a
                # blob is named by its own content, so an existing one is
                # already correct and re-writing it can only corrupt it.
                tmp = bp + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, bp)
                new_blobs += 1
        entries[rel] = rec

    rows = read_manifest(project)
    prev = rows[-1] if rows else None
    same = prev is not None and {k: v.get("sha256") for k, v in entries.items()} == {
        k: v.get("sha256") for k, v in (prev.get("entries") or {}).items()}
    if same and args.only_if_changed:
        print("unchanged since {}; no manifest row written (--only-if-changed)".format(
            prev.get("ts")))
        return 0

    row = {"schema": SCHEMA, "ts": next_ts(rows, now_utc()), "paths": len(entries),
           "unchanged": bool(same), "entries": entries}
    with open(os.path.join(d, MANIFEST), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    print("snapshot {}  {} paths  {} new blobs  {} reused  {}".format(
        row["ts"], len(entries), new_blobs, reused,
        "unchanged since last run" if same else "content moved"))
    return 0


def cmd_at(args) -> int:
    rows = read_manifest(args.project)
    when = parse_when(args.when)
    snap = resolve_at(rows, when)
    if snap is None:
        print("no snapshot at or before {}. The earliest is {}".format(
            when, rows[0]["ts"] if rows else "(store is empty)"))
        return 1
    entries = snap.get("entries") or {}
    print("as of {}, from the snapshot taken {}".format(when, snap["ts"]))
    sel = [args.path] if args.path else sorted(entries)
    rc = 0
    for p in sel:
        ent = entries.get(p)
        if ent is None:
            print("  {}: not in that snapshot".format(p))
            rc = 1
            continue
        print("  {}  {} bytes  {}{}".format(
            p, ent.get("size"), (ent.get("sha256") or "")[:12],
            "" if ent.get("captured") else "  [not captured: {}]".format(ent.get("reason"))))
        if args.content:
            if not ent.get("captured"):
                print("    content unavailable: {}".format(ent.get("reason")))
                rc = 1
                continue
            bp = os.path.join(store_dir(args.project),
                              blob_relpath(ent["sha256"]).replace("/", os.sep))
            if not os.path.exists(bp):
                print("    blob missing (objects/ is gitignored; this is not the "
                      "machine that took the snapshot)")
                rc = 1
                continue
            sys.stdout.write(open(bp, "r", encoding="utf-8", errors="replace").read())
    return rc


def cmd_log(args) -> int:
    rows = read_manifest(args.project)
    vs = version_log(rows, args.path)
    if not vs:
        print("{} appears in no snapshot".format(args.path))
        return 1
    print("{}: {} distinct versions across {} snapshots".format(
        args.path, len(vs), len(rows)))
    for v in vs:
        if v.get("absent"):
            print("  {}  DELETED".format(v["ts"]))
            continue
        print("  {} .. {}  {:>8} bytes  {}{}".format(
            v["ts"], v["last_seen"], v["size"], v["digest"][:12],
            "" if v["captured"] else "  [hash only]"))
    return 0


def cmd_changed(args) -> int:
    rows = read_manifest(args.project)
    lo, hi = parse_when(args.since), parse_when(args.until)
    diffs = changed_between(rows, lo, hi)
    if not diffs:
        print("nothing changed between {} and {}".format(lo, hi))
        return 0
    print("{} paths changed between {} and {}".format(len(diffs), lo, hi))
    for p, (a, b) in diffs.items():
        print("  {}  {} -> {}".format(
            p, (a or "(absent)")[:12], (b or "(absent)")[:12]))
    return 0


def cmd_verify(args) -> int:
    """Every referenced blob is present and hashes to its own name."""
    d = store_dir(args.project)
    rows = read_manifest(args.project)
    want: dict[str, int] = {}
    for r in rows:
        for ent in (r.get("entries") or {}).values():
            if ent.get("captured") and ent.get("sha256"):
                want[ent["sha256"]] = ent.get("size", 0)
    missing, corrupt = [], []
    for digest, size in sorted(want.items()):
        bp = os.path.join(d, blob_relpath(digest).replace("/", os.sep))
        if not os.path.exists(bp):
            missing.append(digest)
            continue
        if sha256_bytes(open(bp, "rb").read()) != digest:
            corrupt.append(digest)
    for digest in corrupt:
        print("CORRUPT {} does not hash to its own name".format(digest))
    for digest in missing:
        print("MISSING {}".format(digest))
    print("VERDICT: {} snapshots, {} distinct blobs, {} missing, {} corrupt".format(
        len(rows), len(want), len(missing), len(corrupt)))
    return 1 if corrupt or missing else 0


def cmd_selftest(args) -> int:
    """Plant one defect per guarantee this module makes, and prove each is caught.

    Every assertion is over a pure function. Nothing here touches git, the
    network, or the real store, so this verb is safe to run anywhere.
    """
    rc = 0

    def ok(cond: bool, what: str, detail: str = "") -> None:
        nonlocal rc
        print(("[ok]   " if cond else "[FAIL] ") + what
              + (f"  <- {detail}" if not cond and detail else ""))
        if not cond:
            rc = 1

    # parse_when(): a bare date must mean the start of the day. If it silently
    # meant "end", `at 2026-07-30` would answer with bytes written later that
    # day and every reconstruction would be off by up to 24 hours.
    ok(parse_when("2026-07-30") == "2026-07-30T00:00:00Z",
       "a bare date resolves to the START of that day", parse_when("2026-07-30"))
    ok(parse_when("2026-07-30T12:00") == "2026-07-30T12:00:00Z",
       "a minute-precision instant gains seconds, not a guess",
       parse_when("2026-07-30T12:00"))
    ok(parse_when("2026-07-30T12:00:00Z") == parse_when("2026-07-30 12:00:00"),
       "a trailing Z and a space separator are the same instant")
    bad = False
    try:
        parse_when("last tuesday")
    except ValueError:
        bad = True
    ok(bad, "an unparseable instant raises instead of defaulting to now")

    # resolve_at(): strictly at-or-before. A nearest-neighbour implementation
    # passes a naive test and is wrong, so this pins the direction explicitly.
    rows = [{"ts": "2026-07-30T10:00:00Z", "entries": {"a": {"sha256": "aa", "size": 1,
                                                             "captured": True}}},
            {"ts": "2026-07-30T14:00:00Z", "entries": {"a": {"sha256": "bb", "size": 2,
                                                             "captured": True}}}]
    got = resolve_at(rows, "2026-07-30T13:59:00Z")
    ok(got is not None and got["ts"] == "2026-07-30T10:00:00Z",
       "a moment one minute before a snapshot resolves to the EARLIER one",
       got["ts"] if got else "None")
    ok(resolve_at(rows, "2026-07-30T14:00:00Z")["ts"] == "2026-07-30T14:00:00Z",
       "a moment exactly at a snapshot resolves to that snapshot")
    ok(resolve_at(rows, "2026-07-30T09:00:00Z") is None,
       "a moment before every snapshot resolves to nothing, not to the first one")

    # version_log(): repeated identical runs are confirmations, not versions.
    many = rows[:1] + [{"ts": "2026-07-30T11:00:00Z",
                        "entries": {"a": {"sha256": "aa", "size": 1, "captured": True}}},
                       {"ts": "2026-07-30T12:00:00Z",
                        "entries": {"a": {"sha256": "aa", "size": 1, "captured": True}}},
                       rows[1]]
    vs = version_log(many, "a")
    ok(len(vs) == 2, "four snapshots over two contents collapse to two versions",
       str(len(vs)))
    ok(vs[0]["last_seen"] == "2026-07-30T12:00:00Z",
       "an unchanged run extends last_seen rather than adding a version",
       vs[0]["last_seen"])
    ok(vs[0]["ts"] == "2026-07-30T10:00:00Z",
       "a version is dated by when it FIRST appeared, not when it was last seen")

    gone = many + [{"ts": "2026-07-30T15:00:00Z", "entries": {}}]
    vg = version_log(gone, "a")
    ok(vg[-1].get("absent") is True,
       "a path that vanishes from a snapshot is logged as DELETED, not as unchanged")

    # changed_between(): the lower endpoint is the snapshot in effect AT `lo`.
    # Taking the first snapshot AFTER `lo` hides any change inside the window.
    ch = changed_between(rows, "2026-07-30T10:30:00Z", "2026-07-30T14:30:00Z")
    ok(ch.get("a") == ("aa", "bb"),
       "a change between two runs is visible from a window that starts mid-gap",
       str(ch))
    ok(changed_between(rows, "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z") == {},
       "a zero-width window reports no change")
    ch2 = changed_between([rows[0], {"ts": "2026-07-30T14:00:00Z", "entries": {}}],
                          "2026-07-30T10:30:00Z", "2026-07-30T15:00:00Z")
    ok(ch2.get("a") == ("aa", None),
       "a path present at the start and absent at the end reports as changed",
       str(ch2))

    # blob_relpath(): fan-out must not collide two digests into one file, and the
    # prefix directory must actually differ from the full name.
    d1, d2 = "ab" + "1" * 62, "ab" + "2" * 62
    ok(blob_relpath(d1) != blob_relpath(d2),
       "two digests sharing a prefix get different blob paths")
    ok(blob_relpath(d1) == "{}/ab/{}".format(OBJECTS, d1),
       "a blob path fans out on the first two hex characters", blob_relpath(d1))

    # is_skipped(): the store must not photograph itself, or every run doubles.
    ok(is_skipped(STORE + "/manifest.jsonl"), "the timetravel store skips itself")
    ok(is_skipped("state/snapshots/x/files/y"), "the snap.py store is skipped")
    ok(is_skipped("state/bus.jsonl.lock"), "a zero-byte chain lock is skipped")
    ok(not is_skipped("state/handback-log.jsonl"),
       "a real ignored ledger is NOT skipped")
    ok(not is_skipped("quality-contract.json"),
       "an uncommitted tracked file is NOT skipped")

    # now_utc()/next_ts(): ordering is this tool's only product, so two rows must
    # never be able to share a timestamp. The seconds-resolution version of
    # now_utc() failed exactly this on its first real run.
    ok(now_utc().endswith("Z") and "." in now_utc(),
       "a stamp carries sub-second resolution", now_utc())
    stamp = now_utc()
    ok(parse_when(stamp) == stamp,
       "a stamp this tool PRINTS is a stamp it can READ back", stamp)
    ok(parse_when("2026-07-30T20:58:36.172Z") == "2026-07-30T20:58:36.172Z",
       "copying a ts out of `log` into `at` does not raise")
    hist = [{"ts": "2026-07-30T20:57:38.000Z"}]
    ok(next_ts(hist, "2026-07-30T20:57:38.000Z") == "2026-07-30T20:57:38.001Z",
       "a colliding stamp is nudged past the previous row, not accepted",
       next_ts(hist, "2026-07-30T20:57:38.000Z"))
    ok(next_ts(hist, "2026-07-30T20:00:00.000Z") > hist[0]["ts"],
       "a BACKWARDS clock cannot write a row that sorts before the last one",
       next_ts(hist, "2026-07-30T20:00:00.000Z"))
    ok(next_ts(hist, "2026-07-30T21:00:00.000Z") == "2026-07-30T21:00:00.000Z",
       "a normal forward stamp is left alone")
    ok(next_ts([], "2026-07-30T21:00:00.000Z") == "2026-07-30T21:00:00.000Z",
       "the first row in an empty store keeps its own stamp")

    # in_tracked_watch(): the narrowing that keeps this a ledger tool instead of a
    # working-tree backup. A prefix match that forgot to anchor would let any
    # dirty file in, which is the exact defect measured on the first run here
    # (171 paths, 7.4 MB, most of them docs).
    ok(in_tracked_watch("quality-contract.json"),
       "the file whose waiver was lost is watched while dirty")
    ok(in_tracked_watch("state/bus.jsonl"),
       "a tracked ledger under state/ is watched even though git has it")
    ok(not in_tracked_watch("docs/CODEBASE-MAP.md"),
       "an unrelated dirty doc is NOT watched")
    ok(not in_tracked_watch("quality-contract.json.bak"),
       "a path that merely starts with a watched file name is NOT watched")

    # sha256_bytes(): content addressing is the whole dedupe claim.
    ok(sha256_bytes(b"x") == sha256_bytes(b"x") != sha256_bytes(b"y"),
       "identical bytes address identically and different bytes do not")

    # cmd_verify(): added 2026-07-31 after tools/audit/mutations/timetravel.py
    # found that deleting the entire corruption comparison left this selftest
    # green. Every check above is over a pure function; verify is the only place
    # the store's integrity claim is enforced, and it was asserted on by nothing.
    # A blob is trusted BECAUSE its name is its hash, so a verify that stops
    # comparing makes `at --content` print altered bytes under a digest that no
    # longer describes them, while still reporting 0 corrupt.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = ensure_store(td)
        payload = b"ledger line one\n"
        digest = sha256_bytes(payload)
        bp = os.path.join(d, blob_relpath(digest).replace("/", os.sep))
        os.makedirs(os.path.dirname(bp), exist_ok=True)
        with open(bp, "wb") as fh:
            fh.write(payload)
        with open(os.path.join(d, MANIFEST), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"schema": SCHEMA, "ts": now_utc(), "paths": 1,
                                 "unchanged": False,
                                 "entries": {"state/x.jsonl": {
                                     "sha256": digest, "size": len(payload),
                                     "captured": True, "reason": ""}}}) + "\n")
        args_v = argparse.Namespace(project=td)
        ok(cmd_verify(args_v) == 0, "an intact store verifies")
        with open(bp, "wb") as fh:
            fh.write(b"ledger line one, edited\n")
        ok(cmd_verify(args_v) == 1,
           "a blob edited after the fact no longer hashes to its own name and is "
           "reported CORRUPT")
        os.remove(bp)
        ok(cmd_verify(args_v) == 1,
           "a referenced blob that is gone is reported MISSING, not skipped")

    print("\nVERDICT: {}".format(
        "every planted defect is caught" if rc == 0
        else "timetravel selftest has failures above"))
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", default=".")
    sub = ap.add_subparsers(dest="command", required=True)

    s = sub.add_parser("snap", help="capture the current bytes")
    s.add_argument("--only-if-changed", action="store_true",
                   help="write no manifest row when nothing moved")
    s.add_argument("--all-dirty", action="store_true",
                   help="widen to every tracked file differing from HEAD, not just "
                        "TRACKED_WATCH; on a mid-work branch this is the whole tree")
    s.set_defaults(fn=cmd_snap)

    s = sub.add_parser("at", help="what a ledger said at a moment")
    s.add_argument("when")
    s.add_argument("--path")
    s.add_argument("--content", action="store_true")
    s.set_defaults(fn=cmd_at)

    s = sub.add_parser("log", help="every distinct version of one path")
    s.add_argument("path")
    s.set_defaults(fn=cmd_log)

    s = sub.add_parser("changed", help="what moved in a window")
    s.add_argument("since")
    s.add_argument("until")
    s.set_defaults(fn=cmd_changed)

    sub.add_parser("verify", help="blobs match their names").set_defaults(fn=cmd_verify)
    sub.add_parser("selftest", help="plant a defect per guarantee").set_defaults(
        fn=cmd_selftest)

    args = ap.parse_args(argv)
    args.project = os.path.abspath(args.project)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
