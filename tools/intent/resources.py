#!/usr/bin/env python3
"""Resource ledger: what we were handed, and what we concluded about it.

Written because the number was bad. Of 110 external resources the operator handed over
in one week, 14 left a reasoned write-up on disk and 73 left no trace at all, and
nothing anywhere was keyed on a URL or a repository. So "what did we decide about this
repo" was answerable only by grepping prose and hoping, and the only thing carrying a
resource across a session boundary was the compaction summary, which dies with the
session.

TWO ROW KINDS, and the distinction is the whole design.

  `seen` says a resource appeared. Cheap, automatic, and says nothing about whether
  anyone thought about it.
  `note` says we concluded something, and carries a pointer to the artifact holding the
  reasoning. It never carries the reasoning itself.

Collapsing those into one row is the mistake that makes the ledger lie: a bare list of
URLs looks like coverage while recording only exposure. Keeping them apart means the
ratio of noted to seen is computable, and that ratio is the 12.7% this module exists to
move. A ledger that cannot report its own coverage is the same defect as a gate that
cannot fail.

IDENTITY IS CONTENT-ADDRESSED, so the same resource written four different ways is one
row set. `github.com/google-research/zapbench`, its https form, its trailing slash form
and its `.git` form are the same repository, and a ledger that treats them as four
things answers "what did we conclude" with a quarter of the truth.

NO REASONING TEXT LIVES HERE. A note points at a file. That keeps this ledger small
enough to stay honest, and keeps the argument in a document a human can read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "bus") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "bus"))

from bus import file_lock, row_altered, row_hash, row_id  # noqa: E402

LEDGER = REPO_ROOT / "state" / "resource-ledger.jsonl"

# Declared coverage. `chain_fields` is not listed: canonical() covers the declaration on
# top of these, and a self-listing declaration makes that guarantee untestable.
#
# `source` was added on 2026-07-29 for the backfill, and adding it cost no migration.
# Rows written before it declare the shorter list and still verify against their own
# declaration, because each row carries the coverage its hash was taken over. Under a
# module-level constant the same edit would have silently rehashed every existing row
# and read as tampering. This is the property the self-describing design was chosen for,
# and it is the first time it has been exercised.
RES_CHAIN_FIELDS = ("actor", "id", "key", "kind", "note_ref", "prev", "session",
                    "source", "ts", "verdict")

KINDS = ("seen", "note")

# Verdicts a note may carry. Deliberately few and deliberately blunt: a vocabulary with
# twenty shades produces rows nobody can aggregate.
VERDICTS = ("adopt", "reject", "superseded", "reference", "unevaluated")

# Query parameters that identify a campaign rather than a document. Stripping them is
# what makes two links to the same page one resource.
TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_[ce]id$|ref$|ref_src$|si$|s$|igshid$)")


def normalize(raw: str) -> str:
    """Canonical key for one resource. Lossy on purpose, and only where loss is safe.

    A GitHub repository collapses to `github.com/owner/repo`: the branch, the file path
    and the line anchor all describe a location INSIDE one resource, and the question
    being answered is what we concluded about the repository. Any other URL keeps its
    path, because two pages on one domain are genuinely two resources.

    The fragment is dropped everywhere. A `#section` is a position in a document, not a
    different document, and keeping it would split one paper across a dozen ids.
    """
    text = (raw or "").strip()
    if not text:
        return ""

    # A bare owner/repo, the form that appears in prose far more often than a full URL.
    bare = re.fullmatch(r"([A-Za-z0-9][\w.-]*)/([\w.-]+?)(?:\.git)?/?", text)
    if bare and "." not in bare.group(1):
        return f"github.com/{bare.group(1).lower()}/{bare.group(2).lower()}"

    if "://" not in text:
        text = "https://" + text
    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+", "/", parts.path).rstrip("/")

    if host in {"github.com", "gitlab.com"}:
        segments = [s for s in path.split("/") if s]
        if len(segments) >= 2:
            owner, repo = segments[0].lower(), re.sub(r"\.git$", "", segments[1]).lower()
            return f"{host}/{owner}/{repo}"

    query = "&".join(
        sorted(q for q in parts.query.split("&") if q and not TRACKING.match(q.split("=")[0]))
    )
    return urlunsplit(("https", host, path, query, "")).replace("https://", "", 1)


def resource_id(key: str) -> str:
    """`RES-<12 hex>` over the normalized key, so the id is reproducible from the URL.

    No clock and no counter, which means a backfill over material written months ago
    mints the same id a live sighting would, and the two join without a migration.
    """
    return "RES-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_rows(path: Path = LEDGER) -> list[dict[str, Any]]:
    """Every parseable row. A torn line is skipped rather than raised."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def build_row(*, key: str, kind: str, ts: str, session: str, actor: str,
              verdict: str, note_ref: str, prev: str, source: str = "") -> dict[str, Any]:
    """`source` is where the resource was OBSERVED; `note_ref` is where we reasoned.

    Two different questions ("who mentioned this" versus "what did we decide"), so two
    fields. Folding them into one is how a ledger ends up unable to distinguish a link
    someone pasted from a link someone thought about, which is the exact distinction
    this module exists to hold.
    """
    row: dict[str, Any] = {
        "id": resource_id(key),
        "key": key,
        "kind": kind,
        "ts": ts,
        "session": session,
        "actor": actor,
        "verdict": verdict,
        "note_ref": note_ref,
        "source": source,
        "chain_fields": list(RES_CHAIN_FIELDS),
        "prev": prev,
    }
    row["hash"] = row_hash(row)
    return row


def append(*, url: str, kind: str = "seen", session: str = "", actor: str = "claude",
           verdict: str = "", note_ref: str = "", ts: str = "", source: str = "",
           path: Path = LEDGER) -> dict[str, Any]:
    """Append one row, reading the chain tip inside the same lock as the write.

    Reading the tip outside the lock forks the chain under two concurrent writers: both
    see the same tip, both write `prev` pointing at it, and verify then reports a break
    with no way to tell which row is the intruder.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    if kind == "note":
        if not note_ref:
            raise ValueError("a note must name the artifact holding the reasoning")
        if verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}, got {verdict!r}")

    key = normalize(url)
    if not key:
        raise ValueError("empty resource key")

    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        rows = read_rows(path)
        row = build_row(key=key, kind=kind, ts=ts or utc_now(), session=session,
                        actor=actor, verdict=verdict, note_ref=note_ref, source=source,
                        prev=row_id(rows[-1]) if rows else "")
        payload = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        try:
            if path.exists() and path.stat().st_size:
                with path.open("rb") as fh:
                    fh.seek(-1, 2)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with path.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with path.open("ab") as fh:
            fh.write(payload)
    return row


def append_many(items: list[dict[str, Any]], *, path: Path = LEDGER) -> list[dict[str, Any]]:
    """Append a batch under ONE lock, chaining the rows to each other in order.

    `append` re-reads the whole ledger inside the lock to find the chain tip, which is
    fine per prompt and quadratic per backfill: the first scan wanted 3855 rows, so the
    one-at-a-time path would have parsed roughly seven million lines to write them. The
    tip only has to be read once for a batch, and every row after the first chains to
    the row this same call just built.

    Validation happens BEFORE the lock so a malformed item fails the whole batch with
    nothing written, rather than leaving a partial run that a retry would then duplicate.
    """
    prepared: list[dict[str, Any]] = []
    for item in items:
        kind = item.get("kind", "seen")
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
        if kind == "note":
            if not item.get("note_ref"):
                raise ValueError("a note must name the artifact holding the reasoning")
            if item.get("verdict") not in VERDICTS:
                raise ValueError(f"verdict must be one of {VERDICTS}")
        key = normalize(item.get("url", ""))
        if not key:
            raise ValueError(f"empty resource key from {item.get('url')!r}")
        prepared.append({**item, "_key": key, "kind": kind})

    if not prepared:
        return []

    written: list[dict[str, Any]] = []
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        rows = read_rows(path)
        prev = row_id(rows[-1]) if rows else ""
        chunks: list[bytes] = []
        for item in prepared:
            row = build_row(
                key=item["_key"], kind=item["kind"], ts=item.get("ts") or utc_now(),
                session=item.get("session", ""), actor=item.get("actor", "claude"),
                verdict=item.get("verdict", ""), note_ref=item.get("note_ref", ""),
                source=item.get("source", ""), prev=prev,
            )
            prev = row_id(row)
            written.append(row)
            chunks.append((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                          .encode("utf-8"))
        try:
            if path.exists() and path.stat().st_size:
                with path.open("rb") as fh:
                    fh.seek(-1, 2)
                    torn = fh.read(1) != b"\n"
                if torn:
                    with path.open("ab") as fh:
                        fh.write(b"\n")
        except OSError:
            pass
        with path.open("ab") as fh:
            fh.write(b"".join(chunks))
    return written


def lookup(url: str, path: Path = LEDGER) -> list[dict[str, Any]]:
    """Every row for one resource, however the caller happened to spell it."""
    target = resource_id(normalize(url))
    return [r for r in read_rows(path) if r.get("id") == target]


def coverage(path: Path = LEDGER) -> dict[str, Any]:
    """The ratio this module exists to move: how many seen resources were ever noted.

    Reported rather than hidden, because a ledger that can only list what it holds
    describes exposure and calls it coverage.
    """
    rows = read_rows(path)
    seen = {r["id"] for r in rows if r.get("kind") == "seen"}
    noted = {r["id"] for r in rows if r.get("kind") == "note"}
    return {
        "resources": len(seen | noted),
        "seen": len(seen),
        "noted": len(noted),
        "unnoted": sorted(seen - noted),
        "coverage_pct": round(100.0 * len(noted) / len(seen | noted), 1) if (seen | noted) else 0.0,
    }


def verify(path: Path = LEDGER) -> list[tuple[int, str]]:
    """Every break in the chain as (index, reason). Empty means intact."""
    breaks: list[tuple[int, str]] = []
    prev_id: str | None = None
    for i, row in enumerate(read_rows(path)):
        if row_altered(row):
            breaks.append((i, f"row {row.get('id', '?')} no longer matches its hash"))
        elif prev_id is not None and row.get("prev", "") != prev_id:
            breaks.append((i, f"row {row.get('id', '?')} names prev "
                              f"{row.get('prev', '') or '(empty)'}, previous is {prev_id}"))
        prev_id = row_id(row)
    return breaks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="resources")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_see = sub.add_parser("see", help="record that a resource appeared")
    p_see.add_argument("url")
    p_see.add_argument("--session", default="")

    p_note = sub.add_parser("note", help="record a conclusion, pointing at an artifact")
    p_note.add_argument("url")
    p_note.add_argument("--verdict", required=True, choices=VERDICTS)
    p_note.add_argument("--ref", required=True, help="path to the artifact holding the reasoning")
    p_note.add_argument("--session", default="")

    p_look = sub.add_parser("lookup", help="every row for one resource")
    p_look.add_argument("url")

    sub.add_parser("coverage", help="how many seen resources were ever reasoned about")
    sub.add_parser("verify", help="walk the chain, exit 1 on any break")

    args = parser.parse_args(argv)

    if args.cmd == "see":
        print(json.dumps(append(url=args.url, kind="seen", session=args.session)))
    elif args.cmd == "note":
        print(json.dumps(append(url=args.url, kind="note", verdict=args.verdict,
                                note_ref=args.ref, session=args.session)))
    elif args.cmd == "lookup":
        rows = lookup(args.url)
        if not rows:
            print(f"no rows for {normalize(args.url)} ({resource_id(normalize(args.url))})")
            return 1
        for r in rows:
            mark = " !! ALTERED" if row_altered(r) else ""
            extra = f"  {r['verdict']} -> {r['note_ref']}" if r["kind"] == "note" else ""
            print(f"{r['ts']}  {r['kind']:5}  {r['key']}{extra}{mark}")
    elif args.cmd == "coverage":
        print(json.dumps(coverage(), indent=1))
    elif args.cmd == "verify":
        breaks = verify()
        if breaks:
            for i, reason in breaks:
                print(f"  break at row {i}: {reason}")
            return 1
        print(f"chain intact across {len(read_rows())} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
