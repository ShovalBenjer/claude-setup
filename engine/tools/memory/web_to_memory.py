# -*- coding: utf-8 -*-
"""Memory + web write pipe (Claude OS L2, PRD #14). Turns a research answer into a
DURABLE typed memory card in the auto-memory dir, so web findings stop evaporating
at end of session. Memory becomes write-managed-and-read; the web is a write source.

This is the deterministic writer. The distillation (turning raw search text into the
card body) is done by the caller (Claude, or a local SLM per SLM spec #7) and passed
in; this module owns the file format + provenance + staleness stamp.

Usage:
  web_to_memory.py --name <slug> --desc <one-line> --source <url> [--stamp <ISO>] < body.txt
Writes: <auto-memory>/reference_<slug>.md  and appends a pointer to MEMORY.md
"""
import argparse, sys, pathlib, os

MEM = pathlib.Path(os.environ.get("CLAUDE_MEMORY_DIR",
      pathlib.Path.home() / ".claude" / "projects" / "C--Users-shova" / "memory"))


def write_card(name, desc, source, stamp, body):
    MEM.mkdir(parents=True, exist_ok=True)
    slug = name.strip().lower().replace(" ", "-")
    path = MEM / f"reference_{slug}.md"
    card = f"""---
name: reference_{slug}
description: {desc}
metadata:
  type: reference
---

{body.strip()}

**Source:** {source}
**Captured:** {stamp} (verify freshness before relying; web facts go stale)
"""
    path.write_text(card, encoding="utf-8")
    # append a one-line pointer to the index if not already present
    idx = MEM / "MEMORY.md"
    pointer = f"- [{name}](reference_{slug}.md) — {desc[:80]}"
    if idx.exists():
        txt = idx.read_text(encoding="utf-8", errors="replace")
        if f"reference_{slug}.md" not in txt:
            idx.write_text(txt.rstrip() + "\n" + pointer + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--stamp", default="unknown-date")
    a = ap.parse_args()
    body = sys.stdin.read()
    if not body.strip():
        print("empty body on stdin", file=sys.stderr); sys.exit(1)
    p = write_card(a.name, a.desc, a.source, a.stamp, body)
    print(f"wrote {p}")
