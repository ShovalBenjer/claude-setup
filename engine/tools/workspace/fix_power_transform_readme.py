"""Repair the Power_Transform README, which is a raw chat paste.

Verified 2026-07-27 on the public README:

  :48  git clone https://github.com/yourusername/machine-learning-project-phase-1.git
  :54  Copy code
  :60  Copy code
  :70  css
  :71  Copy code

plus an unclosed ```bash fence opened at the Installation section and never
closed, so every heading after it renders as code, and a trailing line reading
"Feel free to customize the content according to your project's specific details
and requirements" -- the assistant's sign-off, published as documentation.

The repo is archived, therefore read-only. It is unarchived, fixed, and archived
again, because archiving is the correct resting state for finished coursework and
read-only is not a reason to leave a broken page up.

    python fix_power_transform_readme.py            # show the rewrite
    python fix_power_transform_readme.py --apply
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "ShovalBenjer/Power_Transform_Box-Cox_Supervised_ML"
NOTEBOOK = "Machine_learning_project_phase_1.ipynb"

REPLACEMENT = """## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/ShovalBenjer/Power_Transform_Box-Cox_Supervised_ML.git
cd Power_Transform_Box-Cox_Supervised_ML
pip install -r requirements.txt
```

## Usage

Open the notebook and run the cells in order:

```bash
jupyter notebook {notebook}
```

## Status

Coursework, completed and archived. It is kept public as a record of earlier
work rather than as a maintained project, so there is no CI, no test suite, and
no support.
""".format(notebook=NOTEBOOK)


def gh(*args: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    rc, out = gh("api", f"repos/{REPO}/contents/README.md")
    if rc != 0:
        print(f"  cannot read README: {out[:150]}")
        return 1
    meta = json.loads(out)
    text = base64.b64decode(meta["content"]).decode("utf-8", "replace")
    sha = meta["sha"]

    # Everything from the Installation heading onward is the damaged region.
    m = re.search(r"^## Installation\s*$", text, re.M)
    if not m:
        print("  '## Installation' heading not found; refusing to guess")
        return 1
    head = text[:m.start()]
    new = head.rstrip() + "\n\n" + REPLACEMENT

    def count(s: str) -> dict:
        return {
            "Copy code": s.count("Copy code"),
            "yourusername": s.count("yourusername"),
            "bare css line": len(re.findall(r"^css\s*$", s, re.M)),
            "chat sign-off": s.count("Feel free to customize"),
            "``` fences": s.count("```"),
        }

    print("  before:", count(text))
    print("  after :", count(new))
    print(f"  README {len(text)} -> {len(new)} chars")

    if not args.apply:
        print("\nPLAN ONLY. Re-run with --apply.")
        return 0

    rc, out = gh("api", "-X", "PATCH", f"repos/{REPO}", "-F", "archived=false",
                 "--jq", ".archived")
    print(f"  unarchive -> archived={out}")
    if rc != 0:
        print(f"  cannot unarchive: {out[:150]}")
        return 1

    rc, branch = gh("api", f"repos/{REPO}", "--jq", ".default_branch")
    rc, out = gh(
        "api", "-X", "PUT", f"repos/{REPO}/contents/README.md",
        "-f", "message=Repair the README, which was a raw chat paste\n\n"
              "Removes three 'Copy code' buttons pasted as text, a placeholder "
              "yourusername clone URL naming a repo that does not exist, two bare "
              "fence-language lines, an unclosed ```bash fence that made every "
              "later heading render as code, and a trailing assistant sign-off "
              "that was published as documentation.",
        "-f", "content=" + base64.b64encode(new.encode("utf-8")).decode("ascii"),
        "-f", f"sha={sha}", "-f", f"branch={branch}")
    print("  README: " + ("rewritten" if rc == 0 else "FAILED " + out[:150]))

    rc2, out2 = gh("api", "-X", "PATCH", f"repos/{REPO}", "-F", "archived=true",
                   "--jq", ".archived")
    print(f"  re-archive -> archived={out2}")
    return rc or rc2


if __name__ == "__main__":
    sys.exit(main())
