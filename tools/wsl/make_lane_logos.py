#!/usr/bin/env python3
"""Generate one window-logo PNG per charter lane, for kitty's window_logo_path.

WHY THIS EXISTS. kitty draws window_logo_path as a watermark behind the text of a
window. The lane a session belongs to is currently visible only in the recall banner at
startup, which scrolls away in seconds, and docs/charters.md records that doing another
lane's work is the most frequently logged entry in state/lessons.jsonl. A watermark that
cannot scroll off is the cheapest permanent answer to "which lane is this window".

WHY NO PILLOW. PIL is not installed in this distro and neither is ImageMagick, measured
2026-08-01. The repo convention is stdlib-only tools, so the PNG is written by hand:
zlib for the IDAT stream, struct for the chunk framing, binascii.crc32 for the checksums.
That is roughly forty lines and removes a dependency argument entirely.

The letters are a hand-set 5x7 bitmap. A real font would need freetype, which is the
dependency this file exists to avoid, and four glyphs do not justify it.

Colours are Kanagawa Dragon, the palette already in ~/.config/kitty/kitty.conf, so the
logos are grounded in an anchor that exists rather than invented here.

    python3 tools/wsl/make_lane_logos.py            # write to ~/.config/kitty/logos
    python3 tools/wsl/make_lane_logos.py --check    # verify without writing
"""

from __future__ import annotations

import argparse
import binascii
import os
import struct
import sys
import zlib

SIZE = 256
SCALE = 28          # glyph cell size in px; 5x7 cells -> 140x196, centred in 256
ALPHA = 96          # watermark, not a sticker: ~38% at full strength before kitty scales

# Kanagawa Dragon accents, one per lane. Same hexes as the colorN block in kitty.conf.
LANES = {
    "A": ("harness", 0x8B, 0xA4, 0xB0),      # dragonBlue
    "B": ("resume", 0xC4, 0x74, 0x6E),       # dragonRed
    "C": ("learning", 0x8A, 0x9A, 0x7B),     # dragonGreen
    "D": ("content", 0xC4, 0xB2, 0x8A),      # dragonYellow
}

# 5 wide, 7 tall, one string per row, '#' is ink.
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
}


def render(letter: str, rgb: tuple[int, int, int]) -> bytes:
    """RGBA pixel buffer, transparent everywhere except the glyph."""
    r, g, b = rgb
    rows = GLYPHS[letter]
    gw, gh = len(rows[0]) * SCALE, len(rows) * SCALE
    ox, oy = (SIZE - gw) // 2, (SIZE - gh) // 2

    # One flat bytearray beats a list of lists here: 256*256*4 is 262 kB and the
    # per-pixel Python loop is the only cost that matters at this size.
    buf = bytearray(SIZE * SIZE * 4)
    for cy, row in enumerate(rows):
        for cx, ch in enumerate(row):
            if ch != "#":
                continue
            for y in range(oy + cy * SCALE, oy + (cy + 1) * SCALE):
                base = (y * SIZE + ox + cx * SCALE) * 4
                for i in range(SCALE):
                    p = base + i * 4
                    buf[p], buf[p + 1], buf[p + 2], buf[p + 3] = r, g, b, ALPHA
    return bytes(buf)


def png(pixels: bytes, width: int = SIZE, height: int = SIZE) -> bytes:
    """Minimal RGBA PNG. Filter type 0 on every scanline, one IDAT."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
        )

    stride = width * 4
    raw = b"".join(
        b"\x00" + pixels[y * stride:(y + 1) * stride] for y in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=os.path.expanduser("~/.config/kitty/logos"),
        help="directory to write lane-<letter>.png into",
    )
    ap.add_argument("--check", action="store_true", help="verify, write nothing")
    args = ap.parse_args()

    failures = 0
    for letter, (desc, r, g, b) in LANES.items():
        blob = png(render(letter, (r, g, b)))
        path = os.path.join(args.out, f"lane-{letter.lower()}.png")

        # The oracle is the file signature and the IHDR geometry, not "the write did not
        # raise". A zero-byte or truncated PNG is exactly what a silent failure produces.
        ok = blob[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(
            ">II", blob[16:24]
        ) == (SIZE, SIZE)
        if not ok:
            print(f"  BAD  lane {letter}: PNG header/geometry check failed")
            failures += 1
            continue

        if args.check:
            state = "would write" if not os.path.exists(path) else "would overwrite"
            print(f"  {state:14} {path}  ({len(blob)} bytes, {desc})")
            continue

        os.makedirs(args.out, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(blob)
        on_disk = os.path.getsize(path)
        if on_disk != len(blob):
            print(f"  BAD  lane {letter}: wrote {len(blob)} but disk has {on_disk}")
            failures += 1
        else:
            print(f"  wrote {path}  ({on_disk} bytes, lane {letter} {desc})")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
