#!/usr/bin/env python3
"""Cross-terminal A2A bus for parallel Claude Code sessions.

Six terminals run at once and none can see the others. Today the operator IS
the message bus: he copy-pastes one session's question into another session's
prompt. This is that bus, made durable and automatic.

Design constraints that came from real failures:
  - Lane is DERIVED from cwd, never declared. A session that must remember to
    announce itself will forget (23 personas sat undeployed for the same
    reason: the step that required someone to remember never ran).
  - Append-only JSONL. No db, no daemon. It DOES take a lock, and the reason is
    a correction: this line used to read "no lock ... concurrent appends of a
    single short line are atomic enough on NTFS at this volume", and that was
    measured false on 2026-07-29. Twenty-four threads each appending one short
    line through `open(path, "a")` left EIGHTEEN lines on disk and a file 246
    bytes shorter than the bytes handed to write. Six rows were destroyed
    outright, not torn: the Windows CRT implements append as a seek-to-end
    followed by a write, and a second writer that seeks in between lands on the
    same offset. `read_all` skipping torn lines hid the survivors of this, which
    is why it went unnoticed. See file_lock().
  - Per-lane read cursor, so a session sees each message exactly once and a
    long-running session does not re-read its whole inbox every prompt.
  - Reading is a hook, not a habit. If it needs the operator to run a command,
    it is not a bus.

DELIVERY RULE, and why it is not "skip your own lane":
  The first version filtered out any message whose from_lane equalled the
  reading lane, on the theory that a session should not be shown its own
  sends. That filter made 8 of the first 9 messages on this bus permanently
  undeliverable: lane B had addressed them to lane B as durable notes for its
  own later sessions, and no lane B session could ever read them. The cursor
  already provides exactly-once, so the filter was guarding a property that
  was not at risk and destroying one that mattered.

  A message addressed to a lane is delivered to that lane. The only cost is
  that a session which sends to its own lane sees that message once on its
  next inbox read, because a per-lane cursor cannot distinguish two sessions
  in the same lane. CLAUDE_SESSION_ID is not exported into the hook
  environment on this machine, so from_session is recorded but always empty
  and must not be used as a filter key.

INTEGRITY, and why a plain JSONL append log was not enough:
  Each row commits to its own content and to the row before it, so an edit, a
  deletion, a reordering or an insertion anywhere in the chained region is
  detectable by `bus.py verify`. Two defects forced this, both reproduced
  against the unchained version before it changed:

    - A third party edited a delivered row's body from "gate is RED, do not
      ship" to "gate is GREEN, ship it" and the bus handed lane C the edited
      text with nothing marking it as altered. A row that does not commit to
      its content cannot be told apart from a row that was never touched.
    - The read cursor was a positional offset into the parsed row list, which
      assumes no earlier row ever moves. state/bus.jsonl is git-tracked and has
      a second writer, so a hand-resolved merge that drops one line shifts every
      lane's cursor. Dropping one earlier row made a genuinely unread message
      undeliverable and printed no error. The cursor is now a row id.

  Scope of the claim, stated because a hash chain invites more: this is tamper
  EVIDENT, not tamper proof, and it authenticates nobody. Every lane here runs
  as the same OS user, so anything that can edit the log can recompute the
  chain over its edit. What it catches is the accident that actually happens, a
  merge resolution or a second writer rewriting a row, not a forger. Truncating
  the newest rows is also not detectable from the log alone, because nothing
  outside the file records where the tip should be.

  bus.py send --to C --kind ask --subject "..." --body "..."
  bus.py inbox                 # unread for THIS lane, advances the cursor
  bus.py inbox --peek          # unread, cursor untouched
  bus.py log --tail 20
  bus.py verify                # walk the chain, exit 1 on any break
  bus.py whoami
  bus.py selftest              # plants known traffic and asserts delivery
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUS = ROOT / "state" / "bus.jsonl"
CURSORS = ROOT / "state" / "bus-cursors"

# cwd prefix -> lane. Longest match wins, so a nested dir cannot be stolen by
# a shorter prefix. Lowercase compare: Windows paths vary in case.
# Letters renumbered 2026-07-30 (B/C/D/E -> A/B/C/D). Scopes are unchanged; only the
# labels moved. tools/lib/lanes.py owns the scheme and the cutover instant, and is the
# only thing that can read a pre-cutover ledger row correctly, because the letters
# collide across the boundary: "B" here now means the resume engine, while "B" in a
# 2026-07-29 row meant the harness. Nothing in this file rewrites history.
LANE_MAP = {
    r"c:\users\shova\claude-setup": "A",
    r"c:\users\shova\downloads\new-recruit": "B",
    # The real checkout is under Downloads. Its absence here is why the learning lane
    # reported itself unaddressable on 2026-07-27 (bus row D->B under the old letters,
    # "LANE_MAP misses downloads\daily-deep-learning"): every message it sent derived
    # the fallback lane, and every message addressed to it landed in a lane nobody
    # read. The two paths below it were aspirational locations that have never existed
    # on this machine; they are kept because a stale prefix costs nothing and removing
    # one that turns out to be real costs a lane.
    r"c:\users\shova\downloads\daily-deep-learning": "C",
    r"c:\users\shova\daily-deep-learning": "C",
    r"c:\users\shova\projects\daily-deep-learning": "C",
    # Added 2026-07-31, after measuring that EVERY real working tree on this
    # machine derived "?" and the ONLY path still resolving to a lane was
    # `downloads\new-recruit`, relocated that morning and now absent. The bus was
    # unaddressable from every live checkout while its map looked populated: the
    # same failure as the daily-deep-learning incident above, at estate scale.
    #
    # Linux spellings are separate keys rather than resolved, because canon_path
    # deliberately does not call Path.resolve() (see its docstring). A symlink is
    # not a duplicate here: `/home/shov/claude-setup` is a symlink to
    # `work/repos/claude-setup` (same inode 2096:92563, verified with
    # `stat -c '%d:%i'`), so both spellings name the SAME authoritative tree and
    # both must derive A. See the selftest note where the old "stale clone"
    # reading of that path is corrected.
    "/home/shov/work/repos/claude-setup": "A",
    "/home/shov/claude-setup": "A",
    "/home/shov/work/repos/new-recruit": "B",
    r"c:\users\shova\new-recruit": "B",
    "/home/shov/work/repos/daily-deep-learning": "C",
}

# An unmapped cwd is UNKNOWN, not a lane. This was "A" until 2026-07-29, which was
# wrong twice over: it silently attributed every unmapped session's messages to a
# real lane that would then be blamed for them, and lane A was retired that same day
# (docs/charters.md), so the default named a lane that no longer exists. Deriving a
# confidently wrong lane is worse than admitting the cwd is not on the map, which is
# the same reasoning session-recall.sh already applies to CLAUDE_LANE.
DEFAULT_LANE = "?"

# Mirrors tools/lib/lanes.py::LANE_NAMES. Duplicated rather than imported to keep this
# oracle importable from any cwd without sys.path surgery; tests/test_lane_renumber.py
# asserts the two stay identical, so the copy cannot drift silently.
LANE_NAMES = {
    "?": "unmapped cwd (not a lane)",
    "A": "claude-setup harness",
    "B": "resume / hiring engine",
    "C": "learning (hasadna)",
    "D": "content and publishing",
}

KINDS = ("fact", "ask", "answer", "claim", "warn", "done")


_WSL_MOUNT = re.compile(r"^/mnt/([a-z])(/|$)")


def canon_path(p: str) -> str:
    """One spelling for a directory, whichever host is naming it.

    `C:\\Users\\x`, `c:/users/x` and WSL's `/mnt/c/Users/x` are the same directory
    and must compare equal, so everything is lowercased into forward-slash
    drive-letter form. A path with no drive (`/home/shov/...`, a real Linux tree)
    is left alone rather than invented into one.

    `Path.resolve()` is deliberately NOT used. It is host-relative: under Linux
    it reads `c:\\users\\x` as an ordinary relative filename and joins it onto the
    cwd, which is how every lane derived UNKNOWN from WSL while the Windows-shaped
    selftest inputs still looked like they were being exercised.
    """
    c = p.strip().replace("\\", "/").lower().rstrip("/")
    m = _WSL_MOUNT.match(c)
    if m:
        c = m.group(1) + ":" + c[len("/mnt/x"):]
    return c or "/"


def lane_for(cwd: str) -> str:
    c = canon_path(cwd)
    best, best_len = DEFAULT_LANE, -1
    for prefix, lane in LANE_MAP.items():
        p = canon_path(prefix)
        if (c == p or c.startswith(p + "/")) and len(p) > best_len:
            best, best_len = lane, len(p)
    return best


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# The fields a row's hash is taken over. `hash` and `sig` are excluded because a
# value cannot commit to itself; `prev` is included because that is what chains
# one row to the one before it.
CHAIN_FIELDS = ("id", "ts", "from_lane", "origin_lane", "from_session", "to",
                "kind", "subject", "body", "refs", "prev")


def canonical(rec: dict) -> bytes:
    """The exact bytes a row's hash is taken over.

    Sorted keys and no whitespace, so a row hashes identically regardless of how
    json.dumps was configured when it was written. Absent keys are omitted
    rather than defaulted to empty, so adding a field to CHAIN_FIELDS later
    cannot silently change the hash of every row that predates the field.

    A row may instead DECLARE its own coverage by carrying `chain_fields`. That
    exists because CHAIN_FIELDS is this bus's vocabulary, and a second ledger
    reusing this function gets a hash over the intersection of its own schema
    with a message-passing one. For a prompt-ticket row carrying id, ts, session,
    repo, branch, text_sha, state and prev, that intersection is three keys: the
    hash would commit to the row's id, its time and its predecessor, and to
    nothing about the ticket. row_altered() would then return False after an edit
    to `state`. A tamper-evidence mechanism that cannot detect tampering is the
    failure class this repo keeps logging, so the alternative is offered here
    rather than left to each caller to get wrong.

    The declaration is itself inside the payload. That is the whole point: if
    coverage could be narrowed without changing the hash, an attacker or a
    careless refactor would drop `state` from the list and every existing row
    would keep verifying. Because `chain_fields` is covered, shrinking it changes
    the digest and reads as tampering, which is what it is.

    Rows with no `chain_fields` key take the original path byte-for-byte, so
    every row already on `bus.jsonl` hashes exactly as it did. The pinned golden
    vector in cmd_selftest holds that.
    """
    declared = rec.get("chain_fields")
    if declared is None:
        fields: tuple[str, ...] = CHAIN_FIELDS
    else:
        fields = (*declared, "chain_fields")
    payload = {k: rec[k] for k in fields if k in rec}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def row_hash(rec: dict) -> str:
    """16 hex of sha256 over canonical(rec), matching tree_fingerprint's width."""
    return hashlib.sha256(canonical(rec)).hexdigest()[:16]


def row_id(rec: dict) -> str:
    """A stable address for any row, chained or not.

    The rows that predate chaining carry no hash. Recomputing one for them costs
    nothing and lets the cursor address every row in the file, so replacing the
    positional cursor needs no migration pass over existing traffic and no
    rewrite of a git-tracked log.

    For a chained row this returns the STORED hash, not a recomputation, so a
    tampered row keeps its address and stays addressable by a cursor that was
    set before the tamper. A cursor that silently stopped resolving would
    reintroduce exactly the message loss the row id was introduced to remove.
    The tamper is not thereby hidden: row_altered() marks it at read time.
    """
    return rec.get("hash") or row_hash(rec)


def row_altered(rec: dict) -> bool:
    """True when a row carries a hash and its content no longer matches it.

    Checked on the READ path, not only by verify. An earlier version of this
    module detected tampering only when someone ran verify, and nothing runs
    verify on every prompt, so an edited row was still handed to the reader as
    ordinary traffic. A check nobody invokes at the moment of use is a check that
    reports rather than protects.

    False for a row with no hash. Those predate chaining and make no claim about
    their own content, so calling them unaltered would be a claim this cannot
    support; verify names them separately as uncovered.
    """
    return "hash" in rec and row_hash(rec) != rec["hash"]


def read_all() -> list[dict]:
    if not BUS.exists():
        return []
    out = []
    for line in BUS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            # A torn concurrent append. Skip the row, never crash the hook that
            # reads this file on every prompt. Silence here is deliberate: a
            # hook that errors blocks the session.
            continue
    return out


@contextmanager
def file_lock(target: Path):
    """An exclusive advisory lock for one append to `target`.

    Held on a sidecar `<name>.lock` rather than on the data file, because
    `msvcrt.locking` locks a byte range starting at the current file position and
    the data handle's position belongs to the append. Two things that must move
    independently should not share a handle.

    Blocking, and deliberately patient: `LK_LOCK` gives up after ten retries at
    one second, and a message is worth more waiting than that, so the retry is
    wrapped in a loop. Uncontended cost is one open and one close.

    Public because the prompt-ticket ledger in tools/intent needs exactly this
    guarantee over a different file, and a second hand-rolled copy of a lock is
    how two files end up with two different bugs.
    """
    lock_path = target.with_name(target.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if sys.platform == "win32":
            import msvcrt
            while True:
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    continue
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if sys.platform == "win32":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def append_row(rec: dict) -> None:
    """Append one message under an exclusive lock, healing a torn predecessor first.

    A crashed write leaves a partial line with no trailing newline. The next
    append would concatenate onto it, so the combined line fails to parse and
    ONE crashed write silently eats TWO messages: the fragment and its
    successor. Writing a newline first confines the damage to the fragment.
    Found by bus.py selftest; the docstring had claimed torn lines were already
    handled, and they were only half handled.

    The lock is the second correction to the same paragraph. Torn-line healing
    addresses a write that CRASHED; it does nothing for two writes that merely
    overlapped, and on Windows those destroy whole rows rather than tearing them.
    The heal-then-write sequence also has to be inside the lock, or one writer
    can append its newline between another's check and its write.

    Binary mode, so the byte on disk is the byte counted. Text mode rewrites
    `\\n` as `\\r\\n` here, which is what made the torn-line check read a `\\n`
    that was really the tail of a `\\r\\n`.
    """
    BUS.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
    with file_lock(BUS):
        try:
            if BUS.exists() and BUS.stat().st_size:
                with BUS.open("rb") as fh:
                    fh.seek(-1, os.SEEK_END)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with BUS.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with BUS.open("ab") as fh:
            fh.write(payload)


def cursor_path(lane: str) -> Path:
    return CURSORS / f"{lane}.txt"


def get_cursor(lane: str) -> str:
    """The id of the last row this lane consumed, or "" if it never has.

    A value of all digits is the old positional cursor. It is returned as written
    and unread() honours it once, so a lane mid-flight when this changed does not
    replay its whole history.
    """
    p = cursor_path(lane)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()


def set_cursor(lane: str, rows: list[dict]) -> None:
    """Point this lane at the last row in the FILE, not the last one delivered.

    Matches the previous semantics, which stored len(rows): a lane is caught up
    to everything written so far, including the rows addressed elsewhere that it
    was never shown.
    """
    CURSORS.mkdir(parents=True, exist_ok=True)
    cursor_path(lane).write_text(row_id(rows[-1]) if rows else "", encoding="utf-8")


def unread(rows: list[dict], lane: str) -> list[dict]:
    """The rows after this lane's cursor.

    When the cursor names a row that is no longer in the file, replay from the
    start instead of skipping. That failure direction is chosen, not incidental:
    over-delivery is visible to the operator and recoverable by reading, while
    silent loss is neither, and silent loss is the defect this replaced. Searches
    from the end so the newest match wins if a row id ever repeats.
    """
    cur = get_cursor(lane)
    if not cur:
        return list(rows)
    if cur.isdigit():                       # legacy positional cursor, honoured once
        return rows[int(cur):]
    for i in range(len(rows) - 1, -1, -1):
        if row_id(rows[i]) == cur:
            return rows[i + 1:]
    return list(rows)


def cmd_send(a: argparse.Namespace) -> int:
    lane = a.from_lane or lane_for(os.getcwd())
    rows = read_all()
    rec = {
        "id": f"{int(time.time())}-{uuid.uuid4().hex[:6]}",
        "ts": now_iso(),
        "from_lane": lane,
        # Derived from cwd even when --from-lane overrides the sender. This
        # module's first design rule is that a lane is derived and never
        # declared, and --from-lane exists to break precisely that rule, so
        # recording both makes a mismatch a visible fact in the row rather than
        # an unknowable one. Nothing here authenticates the claim; it only stops
        # the override from being silent.
        "origin_lane": lane_for(os.getcwd()),
        "from_session": os.environ.get("CLAUDE_SESSION_ID", "")[:8],
        "to": a.to.upper() if a.to.lower() != "all" else "ALL",
        "kind": a.kind,
        "subject": a.subject,
        "body": a.body,
        "refs": [r for r in (a.ref or []) if r],
        "prev": row_id(rows[-1]) if rows else "",
    }
    rec["hash"] = row_hash(rec)
    append_row(rec)
    note = "" if rec["origin_lane"] == lane else f" (declared; cwd is lane {rec['origin_lane']})"
    print(f"sent {rec['id']} {lane}{note} -> {rec['to']} [{rec['kind']}] {rec['subject']}")
    return 0


def cmd_inbox(a: argparse.Namespace) -> int:
    """Deliver unread messages for this lane.

    Registered directly as a SessionStart and UserPromptSubmit hook, so it must
    never exit nonzero: a UserPromptSubmit hook that fails blocks the operator's
    prompt, and an A2A bus that can wedge a session is worse than no bus. Every
    failure path returns 0 with no output. The selftest still catches real
    breakage because it asserts on delivered CONTENT, not on the exit code.
    """
    try:
        return _inbox(a)
    except Exception:  # noqa: BLE001
        return 0


def _inbox(a: argparse.Namespace) -> int:
    lane = a.lane or lane_for(os.getcwd())
    rows = read_all()
    # Addressed to this lane, or broadcast. Deliberately NOT filtered on
    # from_lane: see the DELIVERY RULE in the module docstring.
    fresh = [r for r in unread(rows, lane) if r.get("to") in (lane, "ALL")]
    if not a.peek:
        set_cursor(lane, rows)
    if not fresh:
        return 0
    print(f"=== A2A INBOX: lane {lane} ({LANE_NAMES.get(lane, '?')}), {len(fresh)} unread ===")
    for r in fresh:
        # A declared sender that disagrees with the sender's cwd is shown at the
        # point of reading. Recording the mismatch and never surfacing it would
        # be a field nobody looks at.
        origin = r.get("origin_lane")
        claim = ""
        if origin and origin != r.get("from_lane"):
            claim = f" [declared; sender cwd was lane {origin}]"
        print(f"[{r.get('kind','?')}] from lane {r.get('from_lane','?')}{claim} {r.get('ts','')}")
        print(f"  {r.get('subject','')}")
        # An altered row is still delivered, because withholding it would lose a
        # message and the whole cursor design here prefers over-delivery to
        # silent loss. It is delivered MARKED: the text below is what the file
        # says now, not provably what the sender wrote.
        if row_altered(r):
            print("  !! ALTERED: this row does not match its own hash. The text")
            print("  !! below is what the log says now, not what was sent. Do not")
            print("  !! act on it. Run: python tools/bus/bus.py verify")
        body = (r.get("body") or "").strip()
        for ln in body.splitlines():
            print(f"  {ln}")
        for ref in r.get("refs") or []:
            print(f"  ref: {ref}")
        print(f"  reply: bus.py send --to {r.get('from_lane')} --kind answer --subject \"re: {r.get('subject','')}\" --body \"...\"")
        print()
    return 0


def cmd_log(a: argparse.Namespace) -> int:
    rows = read_all()
    for r in rows[-a.tail:]:
        # Marked here as well as in the inbox. `log` is the other surface a
        # person reads the bus through, and an integrity mark that appears on
        # only one of two read paths tells you nothing about which path you used.
        mark = " !! ALTERED" if row_altered(r) else ""
        print(f"{r.get('ts','')} {r.get('from_lane','?')}->{r.get('to','?')} [{r.get('kind','?')}] {r.get('subject','')}{mark}")
    return 0


def cmd_whoami(_a: argparse.Namespace) -> int:
    lane = lane_for(os.getcwd())
    rows = read_all()
    cur = get_cursor(lane)
    pending = len([r for r in unread(rows, lane) if r.get("to") in (lane, "ALL")])
    print(f"cwd:    {os.getcwd()}")
    print(f"lane:   {lane} ({LANE_NAMES.get(lane, '?')})")
    print(f"bus:    {BUS} ({len(rows)} messages)")
    print(f"cursor: {cur or '(never read)'}{'  [legacy positional]' if cur.isdigit() else ''}")
    print(f"unread: {pending} for this lane")
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    """Walk the chain and name the first thing that does not add up.

    Exits 1 on a break, because a check that finds defects and exits 0 reports
    rather than enforces. Rows that predate chaining are counted and named but
    are not breaks: they are pre-existing traffic, not evidence of tampering,
    and failing on them would make the clean state unreachable. --strict fails
    on them too, for a caller that wants the whole log chained.
    """
    rows = read_all()
    unchained = [i for i, r in enumerate(rows) if "hash" not in r]
    breaks = []
    prev_id = None
    for i, r in enumerate(rows):
        if "hash" in r:
            # Same predicate the read path uses, so verify and the inbox can
            # never disagree about whether a given row was altered.
            if row_altered(r):
                breaks.append((i, r, "content does not match its own hash: the row "
                                     f"says {r['hash']}, its content hashes to "
                                     f"{row_hash(r)}"))
            elif prev_id is not None and r.get("prev", "") != prev_id:
                breaks.append((i, r, "prev does not name the row before it: the row "
                                     f"says {r.get('prev', '') or '(empty)'}, the previous "
                                     f"row is {prev_id}. A row was removed, reordered, "
                                     "or inserted here."))
        prev_id = row_id(r)

    print(str(BUS))
    print("  {} row(s): {} chained, {} predate chaining".format(
        len(rows), len(rows) - len(unchained), len(unchained)))
    if unchained:
        print("  unchained at index: " + ", ".join(str(i) for i in unchained))
        print("  those rows carry no hash, so nothing can be said about whether")
        print("  they were altered. Only rows sent after chaining are covered.")
    print("  not covered either way: truncation of the newest rows, because")
    print("  nothing outside this file records where the tip should be.")

    if not breaks:
        print("  chain intact across every chained row")
        if unchained and a.strict:
            print()
            print("FAIL under --strict: {} row(s) are unchained".format(len(unchained)))
            return 1
        return 0

    print()
    print("  {} BREAK(S):".format(len(breaks)))
    for i, r, why in breaks:
        print("    row {} [{}] {}->{} {!r}".format(
            i, r.get("kind", "?"), r.get("from_lane", "?"), r.get("to", "?"),
            r.get("subject", "")))
        print("      " + why)
    return 1


def cmd_selftest(_a: argparse.Namespace) -> int:
    """Plant known traffic on a throwaway bus and assert what comes back.

    Every case here is a property this bus had already broken in production or
    could break silently: the self-lane message that was undeliverable, the
    cursor that must make delivery exactly-once, the torn line that must not
    crash a hook running on every prompt.
    """
    import io
    import shutil
    import tempfile
    import traceback
    from contextlib import redirect_stdout

    global BUS, CURSORS
    real_bus, real_cursors = BUS, CURSORS
    tmp = Path(tempfile.mkdtemp(prefix="bus-selftest-"))
    BUS, CURSORS = tmp / "bus.jsonl", tmp / "cursors"
    # Every throwaway bus this run created, so a case that plants tampering
    # cannot leak its damage into the next case and every dir gets removed.
    made: list[Path] = [tmp]

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print("  [{}] {}{}".format("ok" if ok else "FAIL", name,
                                   "" if ok else "  <- " + detail))
        if not ok:
            failures.append(name)

    def send(**kw) -> tuple[str, dict]:
        """Run cmd_send against the throwaway bus, turning a crash into a verdict.

        An escaping exception used to take this whole selftest down: the checks
        below the failing send never ran, and the process still exited nonzero.
        Under tools/audit/mutate.py that reads as "caught" with no check naming
        it, which is indistinguishable from being caught for the intended reason
        and hides however many later checks were never reached. Dropping the
        origin_lane line from cmd_send is exactly that case: the row is appended,
        then the summary line raises KeyError reading the field back.

        Returns the traceback text (empty when the send was clean) and the last
        row on the bus, or an empty dict when the crash happened before append.
        """
        crash = ""
        try:
            with redirect_stdout(io.StringIO()):
                cmd_send(argparse.Namespace(ref=None, **kw))
        except BaseException:            # noqa: BLE001 - a crash is a verdict here
            crash = traceback.format_exc()
        rows = read_all()
        return crash, (rows[-1] if rows else {})

    def fresh_bus() -> None:
        """Point the module at a brand new empty bus."""
        global BUS, CURSORS
        d = Path(tempfile.mkdtemp(prefix="bus-selftest-"))
        made.append(d)
        BUS, CURSORS = d / "bus.jsonl", d / "cursors"

    def plant(from_lane: str, to: str, subject: str, body: str = "b") -> None:
        """Write one row shaped exactly as cmd_send writes it, chain included.

        Goes through append_row, the same path cmd_send uses, so the torn-line
        case below tests production behaviour rather than the test's own writer,
        and the integrity cases run against rows shaped like real traffic.
        """
        rows = read_all()
        rec = {
            "id": subject, "ts": now_iso(), "from_lane": from_lane,
            "origin_lane": from_lane, "from_session": "", "to": to,
            "kind": "fact", "subject": subject, "body": body, "refs": [],
            "prev": row_id(rows[-1]) if rows else "",
        }
        rec["hash"] = row_hash(rec)
        append_row(rec)

    def plant_unchained(from_lane: str, to: str, subject: str) -> None:
        """A row in the pre-chaining shape, to prove old traffic still reads."""
        append_row({
            "id": subject, "ts": now_iso(), "from_lane": from_lane,
            "from_session": "", "to": to, "kind": "fact",
            "subject": subject, "body": "b", "refs": [],
        })

    def drop(marker: str) -> None:
        """Remove one row from the file, as a hand-resolved merge conflict does.

        Raises if it did not remove exactly one line. A marker that matches
        nothing would leave the file intact and every assertion downstream would
        pass while testing nothing, which is the failure mode of any test that
        edits its fixture by string match.
        """
        lines = [l for l in BUS.read_text(encoding="utf-8").splitlines() if l.strip()]
        keep = [l for l in lines if marker not in l]
        if len(lines) - len(keep) != 1:
            raise AssertionError(
                "drop({!r}) removed {} lines, expected exactly 1. The fixture was "
                "not modified as intended.".format(marker, len(lines) - len(keep)))
        BUS.write_text("\n".join(keep) + "\n", encoding="utf-8")

    def tamper(find: str, repl: str) -> None:
        """Edit the log in place as a third party would, and prove the edit landed."""
        text = BUS.read_text(encoding="utf-8")
        if text.count(find) != 1:
            raise AssertionError(
                "tamper({!r}) matched {} times, expected 1".format(find, text.count(find)))
        BUS.write_text(text.replace(find, repl), encoding="utf-8")

    def verify(strict: bool = False) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_verify(argparse.Namespace(strict=strict))
        return rc, buf.getvalue()

    def inbox(lane: str, peek: bool = False) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_inbox(argparse.Namespace(lane=lane, peek=peek))
        return buf.getvalue()

    try:
        print("bus.py selftest")

        # The regression that motivated this selftest. Lane B addressed 8 real
        # messages to lane B; the old from_lane filter dropped every one.
        plant("B", "B", "self-lane-note")
        out = inbox("B", peek=True)
        check("self-lane message is delivered to its own lane",
              "self-lane-note" in out,
              "a lane cannot leave durable notes for its own later sessions")

        # Addressing must still be honoured.
        plant("B", "C", "for-c-only")
        check("message addressed to C is not delivered to D",
              "for-c-only" not in inbox("D", peek=True))
        check("message addressed to C is delivered to C",
              "for-c-only" in inbox("C", peek=True))

        # Broadcast.
        plant("A", "ALL", "broadcast-msg")
        check("ALL is delivered to an unrelated lane",
              "broadcast-msg" in inbox("D", peek=True))

        # --peek must not consume.
        before = get_cursor("C")
        inbox("C", peek=True)
        check("--peek leaves the cursor untouched", get_cursor("C") == before,
              "cursor moved {} -> {}".format(before, get_cursor("C")))

        # Exactly-once: a real read consumes, a second read returns nothing.
        first = inbox("C")
        second = inbox("C")
        check("a real read delivers", "for-c-only" in first)
        check("the same message is not delivered twice", second.strip() == "",
              "second read returned: " + second[:80])

        # A torn concurrent append must not crash the reader, because this runs
        # as a hook on every prompt and a crashing hook blocks the session.
        with BUS.open("a", encoding="utf-8") as fh:
            fh.write('{"to": "D", "subj')  # no newline, truncated mid-object
        plant("A", "D", "after-torn-line")
        try:
            out = inbox("D", peek=True)
            check("a torn line is skipped, not fatal", "after-torn-line" in out,
                  "reader stopped at the torn line")
        except Exception as exc:  # noqa: BLE001
            check("a torn line is skipped, not fatal", False, repr(exc))

        # Lane derivation is by longest prefix, so a nested path is not stolen.
        # Letters are the post-2026-07-30 scheme (harness A, resume B, learning C,
        # content D). These three assertions are what would have caught the renumber
        # being applied to the map and not to the derivation contract, or vice versa.
        check("cwd inside claude-setup derives lane A",
              lane_for(r"c:\users\shova\claude-setup\tools\bus") == "A")
        check("cwd inside new-recruit derives lane B",
              lane_for(r"c:\users\shova\downloads\new-recruit") == "B")
        # Changed 2026-07-29 from "falls back to lane A". The old contract attributed
        # every unmapped session to a real lane, so lane A carried messages it never
        # sent, and after lane A was retired the fallback named a lane that no longer
        # exists. UNKNOWN is the honest answer and the loud one.
        check("an unmapped cwd derives UNKNOWN, not a real lane",
              lane_for(r"c:\windows\temp") == "?")
        # The regression the learning lane reported on 2026-07-27: its real checkout
        # lives under Downloads and was absent from the map, so it was unaddressable
        # and its own messages derived the fallback lane. It was lane D then and is
        # lane C now; the bug it guards against is the map missing a real checkout,
        # which the renumber does nothing to fix.
        check("the real daily-deep-learning checkout derives lane C",
              lane_for(r"c:\users\shova\downloads\daily-deep-learning") == "C")

        # Added 2026-07-31, the first session run from WSL. Every one of the three
        # checks above passed on Windows while lane_for returned "?" for EVERY
        # input on this host, including the Windows-shaped literals they pass,
        # because `Path(r"c:\...").resolve()` under Linux is not a drive letter but
        # a relative name joined onto the cwd. The result was the exact defect the
        # daily-deep-learning check exists to catch -- a live checkout deriving no
        # lane, so its messages are unaddressable -- reached through a different
        # door: not a missing prefix, a cwd spelling the map cannot see.
        check("the WSL spelling of the harness checkout derives lane A",
              lane_for("/mnt/c/Users/shova/claude-setup") == "A")
        check("a WSL path nested inside a lane still derives that lane",
              lane_for("/mnt/c/Users/shova/claude-setup/tools/bus") == "A")
        check("the WSL spelling of new-recruit derives lane B",
              lane_for("/mnt/c/Users/shova/Downloads/new-recruit") == "B")
        # CORRECTED 2026-07-31. This block previously asserted that
        # /home/shov/claude-setup derives "?", on the reading that it was "a
        # second checkout, two commits behind the one under /mnt/c" whose
        # authority was an open operator question. That reading was wrong on the
        # facts: it is not a checkout at all. `ls -ld` shows a symlink to
        # `work/repos/claude-setup`, and `stat -c '%d:%i'` gives the same inode
        # (2096:92563) for tools/gate/gate.py through either spelling. One tree,
        # two names. Refusing it a lane made the harness lane unaddressable from
        # the path the operator's own launchers use.
        #
        # This is a strengthening, not a relaxation: the guard it replaces was
        # protecting against attributing a STALE clone's messages to lane A, and
        # that hazard is real but lives elsewhere. It now has its own row below,
        # aimed at the copy that genuinely is behind: the Windows claude-setup
        # sits on `chore/delete-dolt` at 24e01de, an ancestor of main.
        check("the symlinked harness path under /home derives lane A",
              lane_for("/home/shov/claude-setup") == "A")
        check("the WSL work-tree spelling of the harness derives lane A",
              lane_for("/home/shov/work/repos/claude-setup") == "A")
        check("the relocated new-recruit derives lane B on both hosts",
              lane_for("/home/shov/work/repos/new-recruit") == "B"
              and lane_for("/mnt/c/Users/shova/new-recruit") == "B")
        check("the WSL work-tree spelling of the learning repo derives lane C",
              lane_for("/home/shov/work/repos/daily-deep-learning") == "C")
        # The real stale-copy hazard, kept explicit rather than implied. An
        # unmapped sibling of a mapped tree must not inherit its lane by prefix.
        check("a sibling directory of a mapped tree does not inherit its lane",
              lane_for("/home/shov/work/repos/new-recruit-backup") == "?")
        check("an unmapped WSL path derives UNKNOWN",
              lane_for("/mnt/c/Windows/Temp") == "?")

        # A corrupt cursor must not wedge the bus. It names no row in the file,
        # so the lane replays rather than raising or reading as caught-up.
        fresh_bus()
        plant("A", "D", "z1")
        CURSORS.mkdir(parents=True, exist_ok=True)
        cursor_path("D").write_text("not-a-row-id", encoding="utf-8")
        try:
            check("a corrupt cursor replays rather than raising",
                  "z1" in inbox("D", peek=True))
        except Exception as exc:  # noqa: BLE001
            check("a corrupt cursor replays rather than raising", False, repr(exc))

        # --- integrity ------------------------------------------------------
        # Reproduced against the unchained version before this existed: a third
        # party edited a delivered row's body and the bus handed the reader the
        # edited text with nothing marking it as altered.
        fresh_bus()
        plant("B", "C", "verdict", body="gate is RED, do not ship")
        rc, out = verify()
        check("a clean chain verifies and exits 0",
              rc == 0 and "chain intact" in out,
              "exit {}: {}".format(rc, out[-200:]))

        tamper("gate is RED, do not ship", "gate is GREEN, ship it")
        rc, out = verify()
        check("an edited body is caught and the row is named",
              rc == 1 and "does not match its own hash" in out and "verdict" in out,
              "exit {}: {}".format(rc, out[-300:]))
        got = inbox("C", peek=True)
        check("the tampered row is still addressable, so no message is lost",
              "GREEN" in got,
              "verify detects the edit; the cursor must not stop resolving")
        check("the reader is told the row was altered, at the point of reading",
              "ALTERED" in got,
              "the edited text was delivered as ordinary traffic; nothing runs "
              "verify on every prompt, so detection there is not enough")
        with redirect_stdout(io.StringIO()) as lbuf:
            cmd_log(argparse.Namespace(tail=10))
        check("bus.py log marks an altered row too",
              "ALTERED" in lbuf.getvalue(),
              "log: " + repr(lbuf.getvalue()[:160]))

        # The mark must be earned, not decorative: a clean row must not carry it.
        fresh_bus()
        plant("B", "C", "clean-row", body="gate is RED, do not ship")
        got = inbox("C", peek=True)
        check("an untampered row is NOT marked as altered",
              "clean-row" in got and "ALTERED" not in got,
              "a mark that appears on clean rows carries no information")
        plant_unchained("B", "C", "legacy-row")
        got = inbox("C", peek=True)
        check("a row predating the chain is not claimed to be altered",
              "legacy-row" in got and "ALTERED" not in got,
              "an unchained row makes no claim about its content either way")

        # The canonical form is a wire format, so it needs a fixed oracle rather
        # than only self-consistency. Every case above writes and reads with the
        # same canonical(), so a change to its SHAPE stays invisible to them
        # while silently invalidating every row already on disk. This vector was
        # computed once and is pinned: it deliberately omits origin_lane, so the
        # rule that absent keys are omitted rather than defaulted is what is
        # being held, not just the digest.
        want_bytes = ('{"body":"fixed body","from_lane":"B","from_session":"deadbeef",'
                      '"id":"1753400000-abc123","kind":"claim","prev":"0123456789abcdef",'
                      '"refs":["a.py","b.py"],"subject":"golden","to":"C",'
                      '"ts":"2026-07-25T12:00:00+03:00"}')
        golden = {
            "id": "1753400000-abc123", "ts": "2026-07-25T12:00:00+03:00",
            "from_lane": "B", "from_session": "deadbeef", "to": "C",
            "kind": "claim", "subject": "golden", "body": "fixed body",
            "refs": ["a.py", "b.py"], "prev": "0123456789abcdef",
            "hash": "ignored", "sig": "ignored",
        }
        got_bytes = canonical(golden).decode("utf-8")
        check("the canonical form is byte-for-byte what it was when rows were written",
              got_bytes == want_bytes,
              "shape changed, so every row already on disk stops verifying:\n"
              "      want {}\n      got  {}".format(want_bytes, got_bytes))
        check("the pinned row still hashes to its recorded digest",
              row_hash(golden) == "1def9c6c00638f23",
              "got {}".format(row_hash(golden)))
        check("hash and sig are excluded from what a row commits to",
              '"hash"' not in got_bytes and '"sig"' not in got_bytes,
              "a value cannot commit to itself")

        # A row that declares its own coverage. Same reasoning as the vector
        # above: this is a wire format, so it needs a fixed oracle and not only
        # agreement with itself. The declaration is inside the payload on
        # purpose, and the two checks after the vector are the ones that matter,
        # because a hash that cannot notice its own coverage shrinking is
        # decoration.
        # The declaration deliberately does NOT list itself. A writer states its
        # content fields and canonical() guarantees the declaration is covered on
        # top; a self-listing fixture would pass whether or not canonical adds
        # the key, which is a fixture testing itself. Caught by mutation: the
        # first version of this vector self-listed and the mutation that drops
        # the guarantee survived against it.
        pt_want = ('{"branch":"main","chain_fields":["branch","id","prev","repo",'
                   '"session","state","text_sha","ts"],'
                   '"id":"PT-4f2a9c1e77b0","prev":"0123456789abcdef",'
                   '"repo":"claude-setup","session":"deadbeef","state":"CAPTURED",'
                   '"text_sha":"9f2c1e77","ts":"2026-07-29T12:00:00+03:00"}')
        pt_fields = ["branch", "id", "prev", "repo", "session",
                     "state", "text_sha", "ts"]
        pt = {
            "id": "PT-4f2a9c1e77b0", "ts": "2026-07-29T12:00:00+03:00",
            "session": "deadbeef", "repo": "claude-setup", "branch": "main",
            "text_sha": "9f2c1e77", "state": "CAPTURED",
            "chain_fields": list(pt_fields), "prev": "0123456789abcdef",
            "hash": "ignored", "sig": "ignored",
        }
        pt_bytes = canonical(pt).decode("utf-8")
        check("a self-describing row has the canonical form it was written with",
              pt_bytes == pt_want,
              "want {}\n      got  {}".format(pt_want, pt_bytes))
        check("the self-describing vector still hashes to its recorded digest",
              row_hash(pt) == "31683b641761dc1c", "got {}".format(row_hash(pt)))

        # The defect this path exists to prevent: under CHAIN_FIELDS these rows
        # would hash over id, ts and prev only, so state and text_sha would be
        # uncovered and an edit to either would read as clean.
        edited_state = dict(pt, state="CLOSED_VERIFIED", hash=row_hash(pt))
        check("a declared field outside CHAIN_FIELDS is actually covered",
              row_altered(edited_state),
              "state changed and row_altered called it clean, so the chain "
              "commits to nothing about the ticket")
        edited_sha = dict(pt, text_sha="ffffffff", hash=row_hash(pt))
        check("text_sha is covered too, so the prompt cannot be swapped",
              row_altered(edited_sha))

        # Coverage cannot be narrowed quietly. Drop "state" from the declaration
        # and the digest has to move, because the declaration is in the payload.
        narrowed = dict(pt, chain_fields=[f for f in pt_fields if f != "state"])
        check("shrinking the declared coverage changes the digest",
              row_hash(narrowed) != row_hash(pt),
              "coverage was reduced without moving the hash, so a row can be "
              "un-covered after the fact and keep verifying")
        check("a narrowed row is marked altered rather than accepted",
              row_altered(dict(narrowed, hash=row_hash(pt))))

        # The discriminating case. Both rows carry identical values for every key
        # they actually cover; they differ only in the declaration, because the
        # extra name matches no key in the row. If the digest moves, the
        # declaration is genuinely in the payload. If it does not, the earlier
        # checks were passing only because narrowing happened to drop a real key
        # out of the payload, which is a weaker property wearing the same name.
        decl_wide = dict(pt, chain_fields=[*pt_fields, "field_not_in_this_row"])
        check("the declaration is covered in its own right, not via its effect",
              row_hash(decl_wide) != row_hash(pt),
              "two rows agreeing on every covered value hashed the same despite "
              "declaring different coverage, so chain_fields is not in the payload")

        # Concurrent appends must not destroy rows. This is a COUNT check, not a
        # content check, because the failure it guards against is not corruption:
        # the losing row leaves nothing behind to inspect. read_all() skips torn
        # lines silently, so without counting, a bus that ate six of twenty-four
        # messages looks exactly like a bus that received eighteen.
        import threading
        fresh_bus()
        writers, barrier = 24, threading.Barrier(24)

        def concurrent_append(i: int) -> None:
            barrier.wait()  # maximise overlap; without it the writes serialise
            append_row({"id": "c{}".format(i), "ts": now_iso(), "from_lane": "B",
                        "origin_lane": "B", "from_session": "", "to": "C",
                        "kind": "note", "subject": "concurrent", "body": str(i),
                        "refs": [], "prev": ""})

        threads = [threading.Thread(target=concurrent_append, args=(i,))
                   for i in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        landed = read_all()
        check("concurrent appends do not destroy rows",
              len(landed) == writers,
              "{} of {} rows survived; the rest were overwritten, and nothing on "
              "disk records that they existed".format(len(landed), writers))
        check("every concurrent row is individually readable",
              {r.get("body") for r in landed} == {str(i) for i in range(writers)},
              "a row landed corrupt or duplicated")

        # Opt-in is real: the mechanism only engages when the key is present.
        check("declaring coverage changes a row that previously had none",
              row_hash(dict(golden, chain_fields=["id", "ts"])) != row_hash(golden),
              "the declaration was ignored")
        check("rows without a declaration are untouched by this path",
              row_hash(golden) == "1def9c6c00638f23")

        # A row removed from the middle breaks the next row's prev. That is the
        # property that makes deletion detectable at all. Sent through cmd_send,
        # not through plant: a mutation test showed plant() computes its own prev,
        # so planting here would test the test's writer and pass even if cmd_send
        # stopped writing prev entirely.
        fresh_bus()
        crashes = [c for c in (send(to="D", kind="fact", subject=subj, body="b",
                                    from_lane="A")[0]
                               for subj in ("k1", "k2", "k3")) if c]
        check("cmd_send completes without raising",
              not crashes,
              "{} of 3 sends RAISED: {}".format(
                  len(crashes), crashes[0].strip().splitlines()[-1] if crashes else ""))
        check("cmd_send chains each row to the one before it",
              all(r.get("prev") for r in read_all()[1:]),
              "prev values: {}".format([r.get("prev") for r in read_all()]))
        drop('"subject": "k2"')
        rc, out = verify()
        check("a row deleted from the middle of the chain is caught",
              rc == 1 and "prev does not name the row before it" in out,
              "exit {}: {}".format(rc, out[-300:]))

        # row_id must return the STORED hash for a chained row, not a fresh
        # recomputation. Discriminating case: tamper with the exact row the
        # cursor names. Stored -> the cursor still resolves and only the genuinely
        # unread row is delivered. Recomputed -> the cursor resolves nothing and
        # the lane replays traffic it already consumed.
        fresh_bus()
        plant("A", "D", "s1")
        plant("A", "D", "s2")
        inbox("D")                           # cursor now names s2
        plant("A", "D", "s3")
        tamper('"subject": "s2", "body": "b"', '"subject": "s2", "body": "edited"')
        got = inbox("D")
        check("tampering with the row the cursor names does not force a replay",
              "s3" in got and "s1" not in got,
              "delivered: " + repr(got.strip()[:200]))

        # Pre-chaining traffic must stay readable and must not read as tampering,
        # or the clean state would be unreachable on the real 12-row log.
        fresh_bus()
        plant_unchained("A", "D", "old1")
        plant_unchained("A", "D", "old2")
        plant("A", "D", "new1")
        rc, out = verify()
        check("rows predating the chain are reported, not counted as breaks",
              rc == 0 and "unchained at index: 0, 1" in out,
              "exit {}: {}".format(rc, out[-300:]))
        rc, out = verify(strict=True)
        check("--strict fails on unchained rows",
              rc == 1 and "FAIL under --strict" in out,
              "exit {}: {}".format(rc, out[-200:]))
        check("a chained row after unchained ones still delivers",
              "new1" in inbox("D", peek=True))

        # --- the cursor defect ----------------------------------------------
        # Reproduced before the fix: cursor D was the offset 2 into a list that
        # became 2 long, so rows[2:] was empty and a genuinely unread message was
        # lost with no error at all.
        fresh_bus()
        plant("A", "D", "c1")
        plant("A", "D", "c2")
        got = inbox("D")
        check("both messages are delivered on the first read",
              "c1" in got and "c2" in got)
        plant("A", "D", "c3")                # genuinely unread
        drop('"c1"')                         # hand-resolved merge drops a line
        got = inbox("D")
        check("an unread message survives an earlier row being dropped",
              "c3" in got,
              "delivered instead: " + (repr(got.strip()[:60]) if got.strip()
                                       else "nothing at all"))

        # When the cursor names a row that is gone, replay beats skip:
        # over-delivery is visible and recoverable, silent loss is neither.
        fresh_bus()
        plant("A", "D", "r1")
        inbox("D")                           # cursor now names r1
        plant("A", "D", "r2")
        drop('"r1"')
        check("a cursor naming a vanished row replays instead of skipping",
              "r2" in inbox("D", peek=True))

        # A lane mid-flight when this changed must not replay its whole history.
        fresh_bus()
        plant("A", "D", "p1")
        plant("A", "D", "p2")
        CURSORS.mkdir(parents=True, exist_ok=True)
        cursor_path("D").write_text("1", encoding="utf-8")
        got = inbox("D", peek=True)
        check("a legacy positional cursor is honoured once",
              "p2" in got and "p1" not in got,
              "delivered: " + repr(got.strip()[:120]))

        # --- the declared-lane override -------------------------------------
        # This module's first design rule is that a lane is derived from cwd and
        # never declared, and --from-lane exists to break exactly that rule.
        fresh_bus()
        derived = lane_for(os.getcwd())
        declared = "C" if derived != "C" else "D"
        crash, row = send(to="D", kind="fact", subject="declared-send", body="b",
                          from_lane=declared)
        check("--from-lane records the cwd-derived lane beside the declared one",
              not crash and row.get("from_lane") == declared
              and row.get("origin_lane") == derived,
              "from_lane={} origin_lane={} (cwd derives {}){}".format(
                  row.get("from_lane"), row.get("origin_lane"), derived,
                  "; RAISED " + crash.strip().splitlines()[-1] if crash else ""))
        check("a crashing send does not stop the checks after it",
              True, "reaching this line is the assertion")
        check("the declared/derived mismatch is visible when the row is read",
              "declared; sender cwd was lane" in inbox("D", peek=True),
              "the reader saw no mark that the sender lane was declared")
        check("a row sent by cmd_send verifies",
              verify()[0] == 0, verify()[1][-200:])

        # The lock, asserted STRUCTURALLY against this file's own source.
        #
        # mutate.py --spec bus had exactly two survivors out of 23 for weeks:
        # "append_row stops taking the lock" and "the lock is released before
        # the write instead of after". Everything above races nothing, so
        # nothing above could ever notice.
        #
        # A concurrency check is the wrong instrument and would have been worse
        # than this gap. append_row's docstring says the lock exists because
        # overlapping writes destroy whole rows ON WINDOWS; on Linux an O_APPEND
        # write below PIPE_BUF is atomic, so two racing appends both land intact
        # with the lock deleted. That test passes here, passes in CI, and asserts
        # nothing: L-2026-07-31-g, a host-shaped oracle answering a different
        # question on the other host.
        #
        # So this asserts what CAN be checked on any host: the bytes go to disk
        # inside the `with file_lock(...)` block. It cannot prove the lock
        # excludes anyone. It proves nobody moved the write out from under it,
        # which is precisely what both survivors do. Reading __file__ is what
        # makes it work under mutation, since mutate.py runs a mutated COPY of
        # this file and the parse therefore sees the mutant.
        try:
            import ast as _ast
            _src = Path(__file__).read_text(encoding="utf-8")
            _fn = next((n for n in _ast.walk(_ast.parse(_src))
                        if isinstance(n, _ast.FunctionDef)
                        and n.name == "append_row"), None)
            if _fn is None:
                check("append_row still exists to be checked", False,
                      "no append_row in this module")
            else:
                _locks = []
                for _n in _ast.walk(_fn):
                    if not isinstance(_n, _ast.With):
                        continue
                    for _it in _n.items:
                        _c = _it.context_expr
                        if isinstance(_c, _ast.Call) and (
                                getattr(_c.func, "id", None)
                                or getattr(_c.func, "attr", None)) == "file_lock":
                            _locks.append(_n)
                check("append_row takes the file lock", bool(_locks),
                      "the hash-chained ledger is appended with no exclusion")

                _inside = set()
                for _lk in _locks:
                    for _st in _lk.body:
                        for _n in _ast.walk(_st):
                            _inside.add(id(_n))
                _writes = [n for n in _ast.walk(_fn)
                           if isinstance(n, _ast.Call)
                           and isinstance(n.func, _ast.Attribute)
                           and n.func.attr == "write"]
                _out = [w for w in _writes if id(w) not in _inside]
                check("append_row performs a write at all", bool(_writes),
                      "the function no longer writes; its shape changed")
                check("every append_row write is inside the lock", not _out,
                      "write(s) at line {} run with the lock released".format(
                          sorted(w.lineno for w in _out)))
        except Exception as _e:  # a parse failure is a FAIL, never a silent skip
            check("the structural lock check ran", False, repr(_e))
    finally:
        BUS, CURSORS = real_bus, real_cursors
        for d in made:
            shutil.rmtree(d, ignore_errors=True)

    print()
    if failures:
        print("FAILED {}: {}".format(len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="bus.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send")
    s.add_argument("--to", required=True, help="lane letter or 'all'")
    s.add_argument("--kind", default="fact", choices=KINDS)
    s.add_argument("--subject", required=True)
    s.add_argument("--body", required=True)
    s.add_argument("--ref", action="append", help="file path, URL, or command (repeatable)")
    s.add_argument("--from-lane", dest="from_lane", help="override derived lane")
    s.set_defaults(func=cmd_send)

    i = sub.add_parser("inbox")
    i.add_argument("--lane")
    i.add_argument("--peek", action="store_true")
    i.set_defaults(func=cmd_inbox)

    l = sub.add_parser("log")
    l.add_argument("--tail", type=int, default=20)
    l.set_defaults(func=cmd_log)

    v = sub.add_parser("verify")
    v.add_argument("--strict", action="store_true",
                   help="also fail on rows that predate chaining")
    v.set_defaults(func=cmd_verify)

    w = sub.add_parser("whoami")
    w.set_defaults(func=cmd_whoami)

    t = sub.add_parser("selftest")
    t.set_defaults(func=cmd_selftest)

    a = p.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
