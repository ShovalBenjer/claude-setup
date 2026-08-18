"""Copy new book files from Downloads into docs/books. Never moves, never
downloads, never fetches from the network. Operates only on files already
present on the local disk that the operator placed there.

Usage: uv run python ingest.py [--downloads DIR] [--dest DIR] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

BOOK_EXTS = {".epub", ".pdf", ".txt"}
SKIP_SUFFIXES = (":Zone.Identifier",)


def default_downloads() -> Path:
    for candidate in Path("/mnt/c/Users").glob("*/Downloads"):
        if candidate.is_dir():
            return candidate
    return Path.home() / "Downloads"


def already_present(name: str, size: int, dest_dir: Path) -> bool:
    target = dest_dir / name
    if target.exists() and target.stat().st_size == size:
        return True
    # also check by stem, in case of a prior rename
    for existing in dest_dir.glob(f"{Path(name).stem}*"):
        if existing.is_file() and existing.stat().st_size == size:
            return True
    return False


def run(downloads: Path, dest: Path, dry_run: bool) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    copied, skipped, failed = [], [], []

    for src in sorted(downloads.iterdir()):
        if not src.is_file():
            continue
        if any(str(src).endswith(s) for s in SKIP_SUFFIXES):
            continue
        if src.suffix.lower() not in BOOK_EXTS:
            continue
        size = src.stat().st_size
        if already_present(src.name, size, dest):
            skipped.append(src.name)
            continue
        target = dest / src.name
        if dry_run:
            print(f"would copy: {src.name} ({size} bytes)")
            copied.append(src.name)
            continue
        try:
            shutil.copy2(src, target)
        except OSError as exc:
            failed.append((src.name, str(exc)))
            continue
        copied.append(src.name)
        if src.suffix.lower() == ".epub":
            script = Path(__file__).with_name("epub_to_text.py")
            result = subprocess.run(
                ["uv", "run", "--with", "ebooklib", "--with", "beautifulsoup4",
                 "python", str(script), str(target)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                failed.append((src.name, f"epub extraction: {result.stderr.strip()}"))

    print(f"\ncopied {len(copied)}, skipped {len(skipped)} (already present), "
          f"failed {len(failed)}")
    for name, err in failed:
        print(f"  FAILED {name}: {err}", file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", type=Path, default=None)
    ap.add_argument("--dest", type=Path,
                     default=Path.home() / "work/repos/claude-setup/docs/books")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    downloads = args.downloads or default_downloads()
    if not downloads.is_dir():
        print(f"downloads dir not found: {downloads}", file=sys.stderr)
        return 2
    return run(downloads, args.dest, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
