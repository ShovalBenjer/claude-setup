#!/usr/bin/env python3
"""Read API keys out of a .env file by reference, never by echo.

Why this exists instead of `os.environ` or python-dotenv:

1. The keys live in `C:/Users/shova/Downloads/new-recruit/.env`, which is a
   different repository from this one and is not on any PATH. Nothing exports
   them into the shell, so a tool that reads only `os.environ` finds nothing.
2. Case is not stable in that file. `openrouter_api_key` is lowercase while
   `HF_TOKEN_KEY` is upper. On 2026-07-25 a case-sensitive grep for
   `OPENROUTER_API_KEY` returned zero matches and was reported as "the key is
   absent", which was false: the key was there in lowercase the whole time. A
   probe's case assumption produced a false absence, so lookup here is
   case-insensitive by construction and cannot repeat that failure.
3. The names are also misspelled in places (`SUPBASE_*` for Supabase), so
   callers get to pass several candidate spellings and take whichever exists.

Hard rule this module enforces: a secret value is returned to the caller
in-process and is never printed, logged, or put in an exception message. The
CLI can only report presence, length, and a short sha256 fingerprint. A
fingerprint identifies a key across machines without disclosing it.

CLI:
  envload.py paths                 which .env files were found
  envload.py names                 key names only, never values
  envload.py find dolt             key names containing a substring
  envload.py has openrouter_api_key [more...]
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

# Search order. First file that defines a name wins, so an explicit
# CLAUDE_ENV_FILE overrides the shared new-recruit file.
_CANDIDATES = [
    os.environ.get("CLAUDE_ENV_FILE", ""),
    str(Path(__file__).resolve().parents[2] / ".env"),
    r"C:\Users\shova\Downloads\new-recruit\.env",
    str(Path.home() / "Downloads" / "new-recruit" / ".env"),
    str(Path.home() / ".env"),
]

_LINE = re.compile(r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$""")


def env_files() -> list[Path]:
    seen: list[Path] = []
    for c in _CANDIDATES:
        if not c:
            continue
        p = Path(c)
        if p.is_file() and p not in seen:
            seen.append(p)
    return seen


def _unquote(raw: str) -> str:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    # Only an unquoted value can carry a trailing comment, and only when the #
    # is whitespace-separated. Splitting on a bare # would truncate any token
    # that legitimately contains one, which fails silently at request time.
    return re.split(r"\s+#", v, maxsplit=1)[0].strip()


def load() -> dict[str, str]:
    """name (as written) -> value. Values are never logged by this module."""
    out: dict[str, str] = {}
    lowered: set[str] = set()
    for path in env_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = _LINE.match(line)
            if not m:
                continue
            name, raw = m.group(1), m.group(2)
            if name.lower() in lowered:
                continue  # earlier file wins
            out[name] = _unquote(raw)
            lowered.add(name.lower())
    return out


def get(*names: str, default: str | None = None) -> str | None:
    """First matching key, case-insensitively, across all candidate names.

    os.environ is checked first so a session can override without editing .env.
    """
    for n in names:
        for k, v in os.environ.items():
            if k.lower() == n.lower() and v:
                return v
    env = load()
    lut = {k.lower(): v for k, v in env.items()}
    for n in names:
        v = lut.get(n.lower())
        if v:
            return v
    return default


def require(*names: str) -> str:
    v = get(*names)
    if not v:
        where = ", ".join(str(p) for p in env_files()) or "no .env file found"
        # The message names the keys we looked for and where we looked. It must
        # never contain a value, so nothing from load() is interpolated here.
        raise SystemExit(
            "missing credential: none of {} is set.\n"
            "looked in: {}".format(" / ".join(names), where)
        )
    return v


def fingerprint(value: str) -> str:
    """Non-reversible identity for a secret: length plus 8 hex of sha256."""
    return "len={} sha256:{}".format(
        len(value), hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    )


def _main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "paths"

    if cmd == "paths":
        files = env_files()
        if not files:
            print("no .env file found. Candidates checked:")
            for c in _CANDIDATES:
                if c:
                    print("  {}".format(c))
            return 1
        for p in files:
            print("{}  ({} keys)".format(p, sum(1 for _ in _keys_of(p))))
        return 0

    if cmd == "names":
        for k in sorted(load(), key=str.lower):
            print(k)
        return 0

    if cmd == "find":
        needle = (argv[2] if len(argv) > 2 else "").lower()
        hits = [k for k in sorted(load(), key=str.lower) if needle in k.lower()]
        for k in hits:
            print(k)
        if not hits:
            print("no key name contains {!r}".format(needle))
            return 1
        return 0

    if cmd == "has":
        wanted = argv[2:]
        if not wanted:
            print("usage: envload.py has NAME [NAME...]", file=sys.stderr)
            return 2
        env = load()
        lut = {k.lower(): (k, v) for k, v in env.items()}
        missing = 0
        for n in wanted:
            hit = lut.get(n.lower())
            if hit:
                name, val = hit
                print("present  {:28s} as {:28s} {}".format(n, name, fingerprint(val)))
            else:
                print("ABSENT   {}".format(n))
                missing += 1
        return 1 if missing else 0

    print(__doc__)
    return 2


def _keys_of(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    for line in text.splitlines():
        m = _LINE.match(line)
        if m and not line.lstrip().startswith("#"):
            yield m.group(1)


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
