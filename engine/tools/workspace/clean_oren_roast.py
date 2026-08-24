"""Remove the tracked .env from oren-roast-hq at HEAD, then archive the repo.

WHAT THIS DOES AND DOES NOT FIX

The repository tracks a .env at its root carrying 13 populated variables,
including SUPABASE_SERVICE_ROLE_KEY, which bypasses every row-level security
policy on a database holding named real people's data. `.gitignore:18` already
lists `.env`; the file predates that rule, and gitignore does not untrack what is
already tracked.

Deleting it at HEAD removes it from the working tree of every future clone.

It does NOT remove it from history. `gh api commits?path=.env` reports 6 commits
touching the file, so anyone who can read the repository can still recover every
value with `git log -p -- .env`. Purging that needs a history rewrite and a force
push, which this operator's own deny rules forbid and which would break every
existing clone.

**Rotation in the Supabase dashboard is the only thing that makes the key safe.**
This script reduces exposure surface. It does not close the exposure, and saying
otherwise would be the exact false-completion claim the ship gate exists to stop.

No secret value is ever read or printed here. The delete call needs only the blob
sha, which the contents API returns without decoding the file.

    python clean_oren_roast.py            # show the plan
    python clean_oren_roast.py --apply
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "ShovalBenjer/oren-roast-hq"


def gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rc, out = gh("api", f"repos/{REPO}", "--jq",
                 '{v:.visibility,a:.archived,b:.default_branch}|tostring')
    print(f"  repo state: {out}")
    state = json.loads(out) if rc == 0 else {}
    branch = state.get("b", "main")

    rc, out = gh("api", f"repos/{REPO}/contents/.env", "--jq", '{sha:.sha,size:.size}|tostring')
    if rc != 0:
        print("  .env is NOT tracked at HEAD; nothing to delete")
        blob = None
    else:
        blob = json.loads(out)
        print(f"  .env at HEAD: {blob['size']} bytes, sha {blob['sha'][:10]}")

    rc, out = gh("api", f"repos/{REPO}/commits?path=.env&per_page=100", "--jq", "length")
    print(f"  commits touching .env in history: {out}")

    if not args.apply:
        print("\nPLAN: delete .env at HEAD, then archive.")
        print("      History is NOT touched. Rotation remains required.")
        print("\nPLAN ONLY. Re-run with --apply.")
        return 0

    if state.get("a"):
        gh("api", "-X", "PATCH", f"repos/{REPO}", "-F", "archived=false")
        print("  unarchived first (archived repos are read-only)")

    if blob:
        rc, out = gh(
            "api", "-X", "DELETE", f"repos/{REPO}/contents/.env",
            "-f", "message=Remove tracked .env\n\n"
                  ".gitignore already listed .env; the file predates that rule and "
                  "gitignore does not untrack what is already tracked. This removes "
                  "it from HEAD only. It remains in history across 6 commits, so "
                  "SUPABASE_SERVICE_ROLE_KEY and the other 12 values must still be "
                  "rotated. Deleting the file is not rotation.",
            "-f", f"sha={blob['sha']}", "-f", f"branch={branch}")
        print("  delete .env: " + ("done" if rc == 0 else "FAILED " + out[:160]))
        if rc != 0:
            return 1

    rc, out = gh("api", f"repos/{REPO}/contents/.env", "--jq", ".sha")
    print("  .env at HEAD now: " + ("STILL PRESENT" if rc == 0 else "gone"))

    rc, out = gh("api", "-X", "PATCH", f"repos/{REPO}", "-F", "archived=true", "--jq", ".archived")
    print(f"  archived: {out}")

    rc, out = gh("api", f"repos/{REPO}", "--jq",
                 '"  final: \(.visibility) archived=\(.archived)"')
    print(out)
    print("\n  STILL REQUIRED: rotate all 13 values in the Supabase dashboard and "
          "any other provider they belong to. The repository is private and "
          "archived, which limits who can read the history. It does not "
          "invalidate a single credential.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
