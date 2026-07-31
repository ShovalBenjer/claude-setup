"""Ship claude-memes: align the version, then cut the first release.

State before this ran, all verified via gh api on 2026-07-27:

  private, MIT, Rust, 29 files, no secret-shaped paths anywhere in the tree
  Giphy key is user-supplied via GIPHY_API_KEY, documented, never committed
  three workflows (CI, Claude Code Review, Release), CI green
  .claude-plugin/plugin.json present, so it is already a distributable plugin
  NO releases and NO tags, despite a Release workflow that triggers on `v*`

  Cargo.toml   version = "1.3.1"
  plugin.json  "version": "1.1.0"     <- drifted

The drift matters: Claude Code reads plugin.json, so installing the release would
report 1.1.0 while running the 1.3.1 binary. Cargo.toml is treated as the truth
because it is what actually builds. The same defect was found in
mattpocock/skills during the 2026-07-27 repo audit, which is how it was looked
for here at all.

    python ship_claude_memes.py            # show the plan
    python ship_claude_memes.py --apply
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

REPO = "ShovalBenjer/claude-memes-skills"


def gh(*a: str) -> tuple[int, str]:
    p = subprocess.run(["gh", *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or p.stderr or "").strip()


def get(path: str) -> tuple[str, str]:
    rc, out = gh("api", f"repos/{REPO}/contents/{path}")
    d = json.loads(out)
    return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cargo, _ = get("Cargo.toml")
    manifest, msha = get(".claude-plugin/plugin.json")
    cver = re.search(r'^version\s*=\s*"([^"]+)"', cargo, re.M).group(1)
    mver = json.loads(manifest)["version"]

    print(f"  Cargo.toml  : {cver}   (source of truth, this is what builds)")
    print(f"  plugin.json : {mver}   {'AGREES' if cver == mver else 'DRIFTED'}")

    rc, branch = gh("api", f"repos/{REPO}", "--jq", ".default_branch")
    rc, head = gh("api", f"repos/{REPO}/commits/{branch}", "--jq", ".sha")
    tag = f"v{cver}"
    print(f"  branch      : {branch} @ {head[:8]}")
    print(f"  tag to cut  : {tag}")

    rc, out = gh("api", f"repos/{REPO}/git/ref/tags/{tag}")
    if rc == 0:
        print(f"  {tag} already exists; nothing to cut")
        return 0

    if not args.apply:
        print("\nPLAN: align plugin.json to Cargo.toml, then create the tag, which "
              "triggers the Release workflow (on: push: tags: v*).")
        print("PLAN ONLY. Re-run with --apply.")
        return 0

    rc_all = 0
    if cver != mver:
        new = manifest.replace(f'"version": "{mver}"', f'"version": "{cver}"')
        rc, out = gh("api", "-X", "PUT",
                     f"repos/{REPO}/contents/.claude-plugin/plugin.json",
                     "-f", f"message=Align plugin.json version to Cargo.toml ({cver})\n\n"
                           f"The manifest read {mver} while the crate built {cver}. "
                           "Claude Code reads plugin.json, so installing a release "
                           "would have reported the wrong version for the binary "
                           "it was actually running.",
                     "-f", "content=" + base64.b64encode(new.encode()).decode(),
                     "-f", f"sha={msha}", "-f", f"branch={branch}")
        print("  plugin.json: " + ("aligned" if rc == 0 else "FAILED " + out[:140]))
        rc_all |= rc
        if rc == 0:
            rc, head = gh("api", f"repos/{REPO}/commits/{branch}", "--jq", ".sha")

    rc, out = gh("api", "-X", "POST", f"repos/{REPO}/git/refs",
                 "-f", f"ref=refs/tags/{tag}", "-f", f"sha={head}")
    print(f"  tag {tag}: " + ("created" if rc == 0 else "FAILED " + out[:160]))
    rc_all |= rc
    if rc == 0:
        print("  -> Release workflow should now be building the cross-platform matrix")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
