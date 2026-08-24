#!/usr/bin/env python3
"""Backfill the resource ledger from material already on disk.

The driver: `research-papers/` holds 185 files and is referenced from 5 places in the
whole repository, and of 110 resources handed over in one week, 73 left no trace. Those
resources are not missing. They are sitting in documents nobody can query.

This records SIGHTINGS only. Every row it writes is `seen`, never `note`, and that
restriction is the point rather than a limitation. A scanner can prove a link appears in
a file; it cannot prove anyone thought about it. Minting notes from a regex would
manufacture exactly the false coverage the ledger exists to measure, and the resulting
number would be worse than no number because it would look like progress.

So the honest consequence is that running this makes coverage go DOWN, sharply, and the
new figure is the first true one.

Idempotent by (resource, source): re-running adds nothing for a pair already recorded,
so this is safe on a schedule and safe to interrupt.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "tools" / "intent") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "intent"))

import resources  # noqa: E402

DEFAULT_ROOTS = ("research-papers", "docs", "work-docs")

TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".rst", ".html"}

# Trailing punctuation belongs to the sentence, not the URL. Without this, "see
# github.com/x/y." and "see github.com/x/y" are two resources and the ledger is wrong in
# the most boring possible way.
TRAILING = '.,;:!?)]}>"\'`*'

URL = re.compile(r"""(?:https?://|(?<![\w/])github\.com/)[^\s<>()\[\]{}"'`\\]+""")

# Hosts that are never a resource anyone reasoned about.
SKIP_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "example.com", "example.org",
    "schemas.example", "127.0.0.1:8000",
}

# Directories whose contents are machinery or third-party payload rather than material
# the operator handed over. Scanning them buries the real signal under dependency links.
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".mutate-lock",
    "site-packages", ".pytest_cache",
}


def candidate_files(root: Path, max_bytes: int) -> list[Path]:
    out: list[Path] = []
    if root.is_file():
        return [root]
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
        except OSError:
            continue
        out.append(path)
    return out


def extract(text: str) -> set[str]:
    """Every URL-shaped token, cleaned of sentence punctuation and obvious noise."""
    found: set[str] = set()
    for raw in URL.findall(text):
        cleaned = raw.rstrip(TRAILING)
        # A markdown link often ends up as `url)` from `[text](url)`; the strip above
        # handles it, but a bare closing paren inside a path would survive, so drop any
        # token that still looks unbalanced rather than minting a wrong key.
        if cleaned.count("(") != cleaned.count(")"):
            cleaned = cleaned.split("(")[0].rstrip(TRAILING)
        if len(cleaned) < 8:
            continue
        key = resources.normalize(cleaned)
        if not key or "/" not in key and "." not in key:
            continue
        host = key.split("/")[0]
        if host in SKIP_HOSTS or host.startswith("localhost"):
            continue
        found.add(cleaned)
    return found


def scan(roots: list[Path], *, max_bytes: int, dry_run: bool,
         path: Path | None = None) -> dict[str, object]:
    ledger = path or resources.LEDGER

    # Idempotency key. A resource seen in two documents is two sightings, which is
    # information; the same resource seen twice in ONE document is not.
    already = {
        (r.get("id"), r.get("source", ""))
        for r in resources.read_rows(ledger) if r.get("kind") == "seen"
    }

    pairs: list[tuple[str, str]] = []
    files_scanned = 0
    for root in roots:
        if not root.exists():
            print(f"  skip (absent): {root}")
            continue
        for file in candidate_files(root, max_bytes):
            files_scanned += 1
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = file.relative_to(REPO_ROOT).as_posix() if REPO_ROOT in file.parents else str(file)
            for url in extract(text):
                key = resources.normalize(url)
                if (resources.resource_id(key), rel) in already:
                    continue
                pairs.append((url, rel))
                already.add((resources.resource_id(key), rel))

    distinct = {resources.resource_id(resources.normalize(u)) for u, _ in pairs}
    if not dry_run and pairs:
        # One lock, one tip read, one write. See resources.append_many: the per-row path
        # would parse roughly seven million lines to place these.
        resources.append_many(
            [{"url": u, "kind": "seen", "actor": "scan", "source": r} for u, r in pairs],
            path=ledger,
        )

    return {
        "files_scanned": files_scanned,
        "sightings_written": 0 if dry_run else len(pairs),
        "sightings_found": len(pairs),
        "distinct_resources": len(distinct),
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scan_resources")
    parser.add_argument("roots", nargs="*", default=list(DEFAULT_ROOTS),
                        help=f"paths to scan (default: {' '.join(DEFAULT_ROOTS)})")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be recorded, write nothing")
    parser.add_argument("--max-bytes", type=int, default=2_000_000,
                        help="skip files larger than this; a 5 MB lexicon has no URLs worth having")
    args = parser.parse_args(argv)

    roots = [(REPO_ROOT / r if not Path(r).is_absolute() else Path(r)) for r in args.roots]
    result = scan(roots, max_bytes=args.max_bytes, dry_run=args.dry_run)

    for key, value in result.items():
        print(f"  {key}: {value}")
    print()
    cov = resources.coverage()
    print(f"  coverage now: {cov['noted']}/{cov['resources']} resources have a note "
          f"({cov['coverage_pct']}%)")
    if not args.dry_run and cov["coverage_pct"] < 20:
        print("  that number is meant to be low. Only a human writing a note moves it, "
              "and a scanner minting notes would be manufacturing the coverage this "
              "ledger exists to measure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
