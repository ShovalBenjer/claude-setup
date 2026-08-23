"""Extract plain text from an epub the operator already owns.

Usage: uv run --with ebooklib --with beautifulsoup4 python epub_to_text.py <path.epub>
Writes <path>.txt next to the source epub. Lossless format conversion only:
does not fetch, does not scrape, operates on a local file the caller supplies.
"""
from __future__ import annotations

import sys
from pathlib import Path


def extract(epub_path: Path) -> str:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(epub_path))
    parts: list[str] = []
    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n")
        lines = [ln.strip() for ln in text.splitlines()]
        parts.append("\n".join(ln for ln in lines if ln))
    return "\n\n".join(parts)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: epub_to_text.py <file.epub>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    if not src.exists() or src.suffix.lower() != ".epub":
        print(f"not an epub file: {src}", file=sys.stderr)
        return 2
    try:
        text = extract(src)
    except Exception as exc:  # noqa: BLE001 - report, don't swallow
        print(f"extraction failed for {src.name}: {exc}", file=sys.stderr)
        return 1
    dest = src.with_suffix(".txt")
    dest.write_text(text, encoding="utf-8")
    print(f"wrote {dest} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
