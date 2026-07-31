"""Execute a verified reclamation plan, recording intent before acting.

WHY THIS EXISTS RATHER THAN A LIST OF SHELL COMMANDS

Three independent inventories of this machine each reported repositories as safe to delete
because they showed zero unpushed commits, and every one of those numbers came from
remote-tracking refs on disk that had not been refreshed in months. After a real fetch, one
repo had 4 unpushed commits, one had 1, and one had 63 commits sharing no ancestor with its
remote. A second verification pass then refuted four more premises: OneDrive had no client
installed at all, `C:\\SQL2025` was still named as an installer source by 24 MSI products, a
"unique" script turned out to be a superseded draft of a newer file, and a directory dismissed
as untracked ballast held hand-made archives with no build script behind them.

So the failure mode here is not fumbling a command. It is acting on a belief that was checked
once, at a time when it happened to be true, and then reused. Every row in a plan therefore
carries the command whose output authorises it, and this tool RE-RUNS the cheap invariants
immediately before touching anything. A row that no longer holds is skipped and reported, not
executed on the strength of yesterday's evidence.

DEFAULTS

Dry-run. `--execute` is required to move or delete anything, and even then `delete` actions
additionally require `--allow-delete`, because a plan reviewed for its archive rows should not
be able to delete on a typo.

THE MANIFEST IS WRITTEN BEFORE THE ACTION, NOT AFTER

An interrupted run must leave evidence of intent rather than a silent gap. The row is appended,
flushed and fsynced first; the action follows. A crash therefore over-reports (a row with no
action) rather than under-reports (an action with no row), which is the correct direction for a
record whose purpose is answering "what happened to that directory".
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARCHIVE = Path("C:/ARCHIVE-2026-07-30")
DEFAULT_MANIFEST = ROOT / "state" / "reclaim-manifest.jsonl"

ACTIONS = ("archive", "delete-artifact", "delete-local-pushed", "vendor-uninstaller", "leave")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(argv: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            argv, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=180,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, repr(exc)


def dir_bytes(path: Path) -> int:
    """Measured, never estimated. A plan's byte count is evidence, not decoration."""
    if path.is_file():
        return path.stat().st_size
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, onerror=lambda e: None):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                pass
    return total


def recheck_git_safety(path: Path) -> tuple[bool, str]:
    """Re-verify a repo is safe to remove locally. Cheap invariants only, no fetch.

    A fetch would be the stronger check and is deliberately NOT done here: it mutates refs
    and would make this tool a writer even in dry-run. The plan is required to have fetched;
    this confirms nothing has changed since, and refuses if there is no upstream to compare
    against at all.
    """
    if not (path / ".git").exists():
        return False, "no .git, so the plan's repo claim does not apply to this path"

    rc, remotes = run(["git", "remote"], cwd=path)
    if rc != 0 or not remotes.strip():
        return False, "NO REMOTE: local commits exist nowhere else"

    rc, dirty = run(["git", "status", "--porcelain"], cwd=path)
    if rc != 0:
        return False, "git status failed: " + dirty[:200]
    non_artifact = [
        ln for ln in dirty.splitlines()
        if ln.strip() and not any(
            m in ln for m in ("node_modules", "/target/", "/dist/", "__pycache__", ".venv")
        )
    ]
    if non_artifact:
        return False, "{} dirty/untracked non-artifact path(s), first: {}".format(
            len(non_artifact), non_artifact[0][:120])

    rc, stashes = run(["git", "stash", "list"], cwd=path)
    if rc == 0 and stashes.strip():
        return False, "{} stash(es) present".format(len(stashes.splitlines()))

    rc, branches = run(
        ["git", "for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads"],
        cwd=path,
    )
    if rc != 0:
        return False, "for-each-ref failed"
    for line in branches.splitlines():
        if not line.strip():
            continue
        br, _, up = line.partition("|")
        if not up:
            return False, "branch {} has NO UPSTREAM".format(br)
        rc, ahead = run(["git", "rev-list", "--count", "{}..{}".format(up, br)], cwd=path)
        if rc != 0:
            return False, "rev-list failed for {}".format(br)
        if ahead.strip() not in ("0", ""):
            return False, "branch {} is {} commit(s) AHEAD of {}".format(br, ahead.strip(), up)

    return True, "all branches ahead 0, clean tree, no stashes"


def recheck_row(row: dict) -> tuple[bool, str]:
    """Re-verify a row's own preconditions. Returns (safe, why)."""
    path = Path(row["path"])
    if not path.exists():
        return False, "path does not exist (already handled?)"

    action = row.get("action")
    if action not in ACTIONS:
        return False, "unknown action {!r}".format(action)
    if action in ("leave", "vendor-uninstaller"):
        return False, "action {} is never executed by this tool".format(action)

    if action == "delete-local-pushed":
        return recheck_git_safety(path)

    # For archive and delete-artifact, the plan's own guard string is re-run if given. This is
    # how a row states a condition that is specific to it, for example "Drive is not running".
    guard = row.get("recheck_command")
    if guard:
        rc, out = run(["bash", "-lc", guard])
        expect = row.get("recheck_expect")
        if expect is not None and expect not in out:
            return False, "guard {!r} did not contain {!r}; got {!r}".format(
                guard, expect, out[:200])
        if expect is None and rc != 0:
            return False, "guard {!r} exited {}".format(guard, rc)

    return True, "preconditions hold"


def append_manifest(manifest: Path, row: dict) -> None:
    """Append, flush, fsync. Before the action, never after. See the module docstring."""
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def do_archive(path: Path, archive_root: Path) -> Path:
    """Move, preserving enough of the original path to be unambiguous on restore."""
    drive = path.drive.replace(":", "").upper() or "REL"
    rel = Path(*path.parts[1:]) if path.drive else path
    dest = archive_root / drive / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path, help="JSON list of rows")
    ap.add_argument("--execute", action="store_true", help="actually act; default is dry-run")
    ap.add_argument("--allow-delete", action="store_true",
                    help="additionally permit delete-* actions")
    ap.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    rows = json.loads(args.plan.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("plan must be a JSON list")
        return 2

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print("{} | plan={} | rows={} | archive_root={}".format(
        mode, args.plan, len(rows), args.archive_root))
    if args.execute and not args.allow_delete:
        print("note: --allow-delete not given, so delete-* rows will be SKIPPED")
    print()

    totals = {"acted": 0, "skipped": 0, "bytes": 0}
    for row in rows:
        path = Path(row["path"])
        action = row.get("action", "?")
        safe, why = recheck_row(row)

        if not safe:
            print("SKIP  {:<20} {}".format(action, path))
            print("        {}".format(why))
            totals["skipped"] += 1
            continue

        if action.startswith("delete") and not args.allow_delete:
            print("SKIP  {:<20} {}  (needs --allow-delete)".format(action, path))
            totals["skipped"] += 1
            continue

        measured = dir_bytes(path)
        claimed = row.get("bytes")
        drift = ""
        if isinstance(claimed, int) and claimed > 0:
            pct = abs(measured - claimed) / claimed * 100
            if pct > 10:
                drift = "  BYTES DRIFTED {:.0f}% from the plan ({} vs {})".format(
                    pct, measured, claimed)

        print("{}  {:<20} {}  {} bytes{}".format(
            "DO   " if args.execute else "would", action, path, measured, drift))
        print("        why: {}".format(row.get("reason", "")[:150]))
        print("        recheck: {}".format(why))

        if not args.execute:
            totals["bytes"] += measured
            continue

        record = {
            "ts": now(), "action": action, "source": str(path),
            "destination": None, "bytes": measured,
            "reason": row.get("reason", ""), "reversible": row.get("reversible", ""),
            "verified_by": row.get("verified_by", ""),
            "recheck_result": why,
        }

        try:
            if action == "archive":
                dest = args.archive_root / (path.drive.replace(":", "").upper() or "REL")
                record["destination"] = str(dest / Path(*path.parts[1:]))
                append_manifest(args.manifest, record)
                actual = do_archive(path, args.archive_root)
                print("        moved -> {}".format(actual))
            else:
                append_manifest(args.manifest, record)
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
                print("        deleted")
            totals["acted"] += 1
            totals["bytes"] += measured
        except OSError as exc:
            print("        FAILED: {!r}".format(exc))
            append_manifest(args.manifest, {**record, "action": action + "-FAILED",
                                            "error": repr(exc)})
            totals["skipped"] += 1

    print()
    print("acted={} skipped={} bytes={} ({:.2f} GiB)".format(
        totals["acted"], totals["skipped"], totals["bytes"],
        totals["bytes"] / 1024 ** 3))
    if not args.execute:
        print("dry-run only. Nothing was moved or deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
