"""Add an MIT LICENSE to repositories that have none.

A public repository with no licence grants no rights to anyone. For
`agenteval-bench` that makes it unusable as portfolio evidence by exactly the
audience it exists for, and `protobuf-fuzz-guard` is a security tool people are
invited to clone and run. MIT matches the house convention already used by
sqltok and mcp-guard.

    python add_license.py            # show what would be written
    python add_license.py --apply
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

OWNER = "ShovalBenjer"
HOLDER = "Shoval Benjer"
YEAR = "2026"
TARGETS = ["agenteval-bench", "protobuf-fuzz-guard"]

MIT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""".format(year=YEAR, holder=HOLDER)


def gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    body = base64.b64encode(MIT.encode("utf-8")).decode("ascii")
    rc_all = 0

    for repo in TARGETS:
        rc, out = gh("api", f"repos/{OWNER}/{repo}", "--jq", ".default_branch")
        branch = out if rc == 0 else "?"
        rc, _ = gh("api", f"repos/{OWNER}/{repo}/contents/LICENSE")
        present = rc == 0
        print(f"  {repo:<22} branch={branch:<8} LICENSE {'present' if present else 'ABSENT'}")
        if present:
            print("      already has one, skipping")
            continue
        if not args.apply:
            continue
        rc, out = gh(
            "api", "-X", "PUT", f"repos/{OWNER}/{repo}/contents/LICENSE",
            "-f", "message=Add MIT LICENSE\n\nA public repo with no licence grants "
                  "no rights to anyone, which makes it unusable by the audience it "
                  "exists for. MIT matches sqltok and mcp-guard.",
            "-f", f"content={body}",
            "-f", f"branch={branch}",
        )
        if rc == 0:
            try:
                sha = json.loads(out)["content"]["sha"][:8]
            except Exception:
                sha = "?"
            print(f"      wrote LICENSE ({sha})")
        else:
            rc_all = 1
            print(f"      FAILED: {out[:180]}")

    if args.apply:
        print()
        for repo in TARGETS:
            rc, out = gh("api", f"repos/{OWNER}/{repo}", "--jq",
                         '.license.spdx_id // "NONE"')
            print(f"  {repo:<22} api now reports: {out}")
    else:
        print("\nPLAN ONLY. Re-run with --apply.")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
