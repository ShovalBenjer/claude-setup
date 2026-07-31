"""Bring the claude-memes README up to the case-study bar.

The reference is docs/CASE-STUDY-hiring-engine.md: 125 lines, 10 tables, and
three sections that carry it -- "Measured results", "The design decisions worth
defending", and "What it does not do, and what fails".

Measured against it, the README is NOT thin: 246 lines, 21 tables, 22 code
fences, and "Why it's built this way" is already a real design-decisions section
with an old-vs-new table. Two things are missing and one is wrong.

  MISSING  a measured-results section. Every number in the README today is a
           claim without an instrument.
  MISSING  a named limits section. The limits exist (terminal protocol fallback,
           silent skip with no controlling terminal) but are scattered, so a
           reader who wants to know what breaks has to infer it.
  WRONG    "~3 crates of real surface area". Measured: 9 direct dependencies and
           281 packages in Cargo.lock.

Every number inserted below was produced by a command against the live repo on
2026-07-27, listed here so a later reader can re-run them:

  gh api repos/.../git/trees/HEAD?recursive=1   -> 15 .rs files, 104,523 bytes
  grep -c '#[test]' over each .rs                -> 60 test functions, 14 of 15 files
  Cargo.toml [dependencies]                      -> 9 direct
  grep -c '^[[package]]' Cargo.lock              -> 281 packages
  .github/workflows/ci.yml                       -> fmt, clippy -D warnings, test, release build

Binary size is deliberately absent: the v1.3.1 release build had not finished
when this was written, so there is no measured figure to quote.

    python polish_memes_readme.py            # show the patch
    python polish_memes_readme.py --apply
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "ShovalBenjer/claude-memes-skills"

WRONG = "**One static Rust binary**, ~3 crates of real surface area"
RIGHT = "**One static Rust binary**, 15 source files and 9 direct dependencies"

MEASURED = """
## Measured

Every number here came from a command, listed beside it so you can re-run it.

| | | how it was measured |
|---|---:|---|
| Rust source files | 15 | `git ls-files '*.rs'` |
| Source bytes | 104,523 | tree API, `.rs` blobs summed |
| Test functions | 60 | `grep -c '#\\[test\\]'` across `src/` |
| Source files carrying tests | 14 of 15 | same |
| Direct dependencies | 9 | `[dependencies]` in `Cargo.toml` |
| Packages in the lockfile | 281 | `grep -c '^\\[\\[package\\]\\]' Cargo.lock` |

CI runs four gates on every push, and clippy is set to fail on warnings rather
than report them:

```
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all
cargo build --release
```

What that does **not** tell you: there is no benchmark, so the render latency is
unmeasured, and there is no coverage report, so 60 tests over 14 files is a count
and not a percentage.

---

## What it does not do, and what fails

The honest failure modes, in the order you are likely to hit them.

| Situation | What happens |
|---|---|
| No `GIPHY_API_KEY` set | No GIF. The hook exits cleanly; your session is unaffected |
| Giphy is down, rate-limits you, or the network is gone | No GIF, same clean exit. There is no cache and no offline fallback |
| No controlling terminal (cloud session, CI, some IDE panes) | Rendering is skipped silently by design, because a hook that fails must never take the session with it |
| Terminal without Kitty or iTerm2 graphics | Falls back to Unicode half-blocks. It works and it looks worse. `claude-memes doctor` tells you which you will get before you install |
| Terminal without truecolor | Below the half-block fallback there is nothing left to degrade to |
| You dislike the clip Giphy picked | The query pools in `config/hubs.toml` are editable; the search result is not deterministic |

It is also, deliberately, not useful. It renders a GIF when a hook fires. It does
not analyse your tests, change your workflow, or make anything faster. If that is
not what you want from a plugin, this is the wrong plugin.

---
"""


def gh(*a: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rc, out = gh("api", f"repos/{REPO}/contents/README.md")
    if rc != 0:
        print("  cannot read README")
        return 1
    meta = json.loads(out)
    text = base64.b64decode(meta["content"]).decode("utf-8", "replace")

    fixed = WRONG in text
    print(f"  '~3 crates' claim present : {fixed}")

    anchor = "\n## Terminal support"
    if anchor not in text:
        print("  anchor '## Terminal support' not found; refusing to guess placement")
        return 1

    new = text.replace(WRONG, RIGHT) if fixed else text
    new = new.replace(anchor, MEASURED + anchor, 1)

    print(f"  README {len(text)} -> {len(new)} chars "
          f"({new.count(chr(10)) - text.count(chr(10)):+d} lines)")
    print(f"  sections added: Measured, What it does not do and what fails")

    if not args.apply:
        print("\nPLAN ONLY. Re-run with --apply.")
        return 0

    rc, branch = gh("api", f"repos/{REPO}", "--jq", ".default_branch")
    rc, out = gh(
        "api", "-X", "PUT", f"repos/{REPO}/contents/README.md",
        "-f", "message=README: add measured results and a named limits section\n\n"
              "Corrects '~3 crates of real surface area', which measured 9 direct "
              "dependencies and 281 packages in Cargo.lock. Adds every number with "
              "the command that produced it, and states plainly what is NOT "
              "measured (no benchmark, no coverage). Adds a failure-mode table, "
              "because the limits already existed in the text but were scattered "
              "and a reader had to infer them.",
        "-f", "content=" + base64.b64encode(new.encode("utf-8")).decode("ascii"),
        "-f", f"sha={meta['sha']}", "-f", f"branch={branch}")
    print("  README: " + ("updated" if rc == 0 else "FAILED " + out[:170]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
