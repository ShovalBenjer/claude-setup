#!/usr/bin/env python3
"""Deployed personas actually parse as agent definitions, not just exist as files.

C-004 counts .md files in ~/.claude/agents and passes at 23. Counting files proves
deployment happened; it does not prove Claude Code can load any of them. A persona
with malformed front matter, a missing name, or a description the router cannot
read is a file on disk and nothing more, and it fails silently: an agent that never
gets selected looks identical to an agent that was never written.

Requires of each file: a YAML front-matter block delimited by --- at the very top,
carrying at least `name` and `description`. Also flags a name that disagrees with
its filename, because the router selects by name while a human edits by path, and
the two drifting apart is how a persona becomes unreachable.

Front matter is parsed with a deliberately small hand-rolled reader rather than
importing yaml: the harness must run on a bare stdlib Python.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

AGENTS = Path(os.path.expanduser("~")) / ".claude" / "agents"
REQUIRED_KEYS = ("name", "description")


def front_matter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            continue  # nested value under the previous key; not a top-level key
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip().strip("'\"")
    return None  # opened front matter but never closed it


def main() -> int:
    if not AGENTS.is_dir():
        print(f"no agents directory at {AGENTS}: nothing is deployed")
        return 1

    files = sorted(AGENTS.glob("*.md"))
    if not files:
        print(f"{AGENTS} exists but holds no .md personas; treat as UNKNOWN not pass")
        return 1

    problems: list[str] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            problems.append(f"{f.name}: unreadable ({e})")
            continue

        fm = front_matter(text)
        if fm is None:
            problems.append(f"{f.name}: no closed --- front-matter block at the top")
            continue

        missing = [k for k in REQUIRED_KEYS if not fm.get(k)]
        if missing:
            problems.append(f"{f.name}: front matter missing {missing}")
            continue

        if fm["name"] != f.stem:
            problems.append(
                f"{f.name}: front-matter name '{fm['name']}' != filename stem "
                f"'{f.stem}' (router selects by name, humans edit by path)")

    if problems:
        print(f"{len(problems)} of {len(files)} deployed personas will not load cleanly:")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"all {len(files)} deployed personas parse with name + description")
    return 0


if __name__ == "__main__":
    sys.exit(main())
